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

test('exports a verifiable manifest and replays its exact route', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.getTrailManifest === 'function' && typeof window.roll === 'function');
  await page.evaluate(() => window.roll());

  const result = await page.evaluate(async () => {
    const exported = await window.getTrailManifest();
    const verified = await window.R4b1tTrail.verify(exported);
    const expected = verified.manifest.routes[0].url;
    await window.importTrailManifest(exported);
    const replayed = await window.replayTrailManifest(0);
    return {
      expected,
      replayed,
      visible: document.getElementById('previewUrl').textContent.trim(),
      trailId: exported.trail_id,
      corpusRevision: exported.manifest.corpus_revision,
    };
  });

  expect(result.replayed).toBe(result.expected);
  expect(result.visible).toBe(result.expected);
  expect(result.trailId).toMatch(/^sha256:[0-9a-f]{64}$/);
  expect(result.corpusRevision).toMatch(/^sha256:[0-9a-f]{64}$/);
});

test('rejects a tampered imported trail', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.getTrailManifest === 'function');
  await page.evaluate(() => window.roll());

  const message = await page.evaluate(async () => {
    const exported = await window.getTrailManifest();
    exported.manifest.routes[0].url = 'https://attacker.invalid/replaced';
    try {
      await window.importTrailManifest(exported);
      return 'accepted';
    } catch (error) {
      return error.message;
    }
  });

  expect(message).toMatch(/Route ID mismatch/);
});

test('forks a replayed trail with verifiable parent lineage', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.getTrailManifest === 'function' && typeof window.roll === 'function');
  await page.evaluate(() => window.roll());

  const result = await page.evaluate(async () => {
    const parent = await window.getTrailManifest();
    await window.importTrailManifest(parent);
    await window.replayTrailManifest(0);
    const child = await window.forkTrailManifest();
    const lineage = await window.R4b1tTrail.verifyLineage(child, parent);
    return {
      parentId: parent.trail_id,
      declaredParentId: child.manifest.parent.trail_id,
      forkAt: lineage.fork_at,
      inheritedRoute: child.manifest.routes[0].url,
      parentRoute: parent.manifest.routes[0].url,
      status: document.getElementById('trailLedgerStatus').textContent,
    };
  });

  expect(result.declaredParentId).toBe(result.parentId);
  expect(result.forkAt).toBe(1);
  expect(result.inheritedRoute).toBe(result.parentRoute);
  expect(result.status).toBe('FORKED / STEP 001');
});
