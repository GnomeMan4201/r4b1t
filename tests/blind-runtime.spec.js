'use strict';

const { test, expect } = require('@playwright/test');

async function blockExternalNetwork(page) {
  await page.route('**/*', async (route) => {
    const requestUrl = route.request().url();
    if (requestUrl.startsWith('data:') || requestUrl.startsWith('blob:')) return route.continue();
    const parsed = new URL(requestUrl);
    if (parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost') return route.continue();
    return route.abort('blockedbyclient');
  });
}

test.beforeEach(async ({ page }) => {
  await blockExternalNetwork(page);
});

test('blind descent commits without changing or exposing the visible route', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.blindDescend === 'function' && typeof window.getBlindManifest === 'function');

  const result = await page.evaluate(async () => {
    const visibleBefore = document.getElementById('previewUrl').textContent.trim();
    await window.openBlindDescent();
    await window.blindDescend();
    await window.blindDescend();
    const snapshot = await window.getBlindManifest();
    return {
      visibleBefore,
      visibleAfter: document.getElementById('previewUrl').textContent.trim(),
      steps: snapshot.manifest.steps,
      publicJson: JSON.stringify(snapshot),
      status: document.getElementById('blindStatus').textContent,
      depth: document.getElementById('blindDepth').textContent,
    };
  });

  expect(result.visibleAfter).toBe(result.visibleBefore);
  expect(result.steps).toHaveLength(2);
  expect(result.steps.every((step) => step.state === 'concealed')).toBe(true);
  expect(result.steps.every((step) => Object.keys(step).sort().join(',') === 'commitment,index,state')).toBe(true);
  expect(result.publicJson).not.toContain('nonce');
  expect(result.status).toBe('CONCEALED / COMMITMENT PRESENT');
  expect(result.depth).toContain('002');
});

test('reveal discloses the committed route without rerolling it', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.blindDescend === 'function');

  const result = await page.evaluate(async () => {
    await window.openBlindDescent();
    const committed = await window.blindDescend();
    const commitment = committed.manifest.steps[0].commitment;
    const url = await window.blindReveal(0);
    const revealed = await window.getBlindManifest();
    const verification = await window.R4b1tBlind.verify(revealed);
    return {
      url,
      visible: document.getElementById('previewUrl').textContent.trim(),
      commitment,
      revealedCommitment: revealed.manifest.steps[0].commitment,
      verification: verification.statuses[0].status,
      status: document.getElementById('blindStatus').textContent,
    };
  });

  expect(result.visible).toBe(result.url);
  expect(result.revealedCommitment).toBe(result.commitment);
  expect(result.verification).toBe('COMMITMENT VERIFIED');
  expect(result.status).toBe('REVEALED / COMMITMENT VERIFIED');
});

test('blind interface remains within the mobile viewport', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('mobile'), 'mobile-only layout assertion');
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.openBlindDescent === 'function');
  await page.evaluate(() => window.openBlindDescent());
  await expect(page.locator('#blindDescentOverlay')).toHaveClass(/open/);
  const overflow = await page.evaluate(() => document.getElementById('blindDescentOverlay').scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
});

test('wear is persistent and descend, return, and reveal remain visually distinct', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.blindDescend === 'function' && typeof window.R4b1tWear === 'object');
  const result = await page.evaluate(async () => {
    await window.openBlindDescent();
    await window.blindDescend();
    await window.blindDescend();
    await window.blindDescend();
    const afterDescend = {
      motion: document.querySelector('#blindWear .trail-wear').className,
      depth: document.querySelector('#blindWear .trail-wear').dataset.depth,
      creases: document.querySelectorAll('#blindWear .wear-crease').length,
      concealed: document.querySelectorAll('#blindWear .wear-step.concealed').length,
    };
    await window.blindReturn();
    const afterReturn = document.querySelector('#blindWear .trail-wear').className;
    await window.blindReveal(2);
    return {
      afterDescend,
      afterReturn,
      revealWear: document.querySelector('#blindWear .trail-wear').className,
      inkSegment: document.querySelectorAll('#blindWear .wear-step.ink-reveal').length,
      inkCard: document.getElementById('blindCard').classList.contains('ink-reveal-card'),
      revealed: document.querySelectorAll('#blindWear .wear-step.revealed').length,
    };
  });
  expect(result.afterDescend.motion).toContain('motion-descend');
  expect(result.afterDescend.depth).toBe('3');
  expect(result.afterDescend.creases).toBe(3);
  expect(result.afterDescend.concealed).toBe(3);
  expect(result.afterReturn).toContain('motion-return');
  expect(result.revealWear).not.toContain('motion-descend');
  expect(result.revealWear).not.toContain('motion-return');
  expect(result.inkSegment).toBe(1);
  expect(result.inkCard).toBe(true);
  expect(result.revealed).toBe(1);
});
