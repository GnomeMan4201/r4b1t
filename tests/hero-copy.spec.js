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

test('mobile keeps the rabbit aperture and uses privacy-first copy', async ({ page }, testInfo) => {
  if (testInfo.project.name !== 'mobile-chromium') test.skip();

  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.roll === 'function');
  await page.waitForSelector('#r4mHero h1');

  await expect(page.locator('#r4mHero')).toBeVisible();
  await expect(page.locator('#r4mHero img[src="rabbit-aperture.svg"]')).toBeVisible();
  await expect(page.locator('.r4m-status span')).toHaveText('APERTURE / RANDOM');
  await expect(page.locator('#r4mHero h1')).toContainText('NO PROFILE.');
  await expect(page.locator('#r4mHero h1')).toContainText('NO TRACKING.');
  await expect(page.locator('#r4mHero h1')).toContainText('NO RANKING.');
  await expect(page.locator('#r4mHero h1')).not.toContainText('NOT SEARCH');
  await expect(page.locator('#r4mHero h1')).not.toContainText('A DOOR');
  await expect(page.locator('.r4m-enter')).toHaveText('ENTER DOOR ↗');
});
