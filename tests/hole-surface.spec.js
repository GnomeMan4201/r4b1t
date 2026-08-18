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

async function waitReady(page) {
  await page.waitForFunction(() => typeof window.roll === 'function');
  await page.waitForSelector('#r4mShellHost');
  await page.waitForSelector('#r4mHero.r4h-functional');
}

test.beforeEach(async ({ page }) => {
  await blockExternalNetwork(page);
});

test('mobile hero is an operational hole surface, not campaign copy', async ({ page }, testInfo) => {
  if (testInfo.project.name !== 'mobile-chromium') test.skip();

  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitReady(page);

  await expect(page.locator('#r4mHero')).toBeVisible();
  await expect(page.locator('.r4h-hole')).toBeVisible();
  await expect(page.locator('#r4hState')).toHaveText('CORPUS READY');
  await expect(page.locator('.r4m-status span')).toHaveText('HOLE / RANDOM');
  await expect(page.locator('#r4mHero')).not.toContainText('NOT SEARCH');
  await expect(page.locator('#r4mHero')).not.toContainText('NOT A FEED');
  await expect(page.locator('#r4mHero')).not.toContainText('A DOOR');
});

test('mobile roll updates the hole readout and uses functional route wording', async ({ page }, testInfo) => {
  if (testInfo.project.name !== 'mobile-chromium') test.skip();

  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitReady(page);
  await page.locator('#r4mRoll').click();

  await expect(page.locator('#r4mRoute')).toBeVisible();
  await expect(page.locator('#r4hState')).toContainText('ROUTE READY /');
  await expect(page.locator('.r4m-enter')).toHaveText('FOLLOW ROUTE ↗');
});

test('hole surface does not introduce horizontal overflow', async ({ page }, testInfo) => {
  if (testInfo.project.name !== 'mobile-chromium') test.skip();

  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitReady(page);

  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }));
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport + 1);
});
