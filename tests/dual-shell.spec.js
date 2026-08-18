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
}

test.beforeEach(async ({ page }) => {
  await blockExternalNetwork(page);
});

test('desktop keeps the native r4b1t shell', async ({ page }, testInfo) => {
  if (testInfo.project.name === 'mobile-chromium') test.skip();
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitReady(page);
  await expect(page.locator('html')).toHaveAttribute('data-r4b1t-interface', 'desktop');
  await expect(page.locator('.rig')).toBeVisible();
  await expect(page.locator('#r4mShellHost')).toBeHidden();
});

test('mobile selects the dedicated shell and rolls through the shared engine', async ({ page }, testInfo) => {
  if (testInfo.project.name !== 'mobile-chromium') test.skip();
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitReady(page);
  await expect(page.locator('html')).toHaveAttribute('data-r4b1t-interface', 'mobile');
  await expect(page.locator('.r4m-shell')).toBeVisible();
  await expect(page.locator('#r4mRoll')).toBeVisible();
  await page.locator('#r4mRoll').click();
  await expect(page.locator('#r4mRoute')).toBeVisible();
  await expect(page.locator('#r4mDomain')).not.toHaveText('—');
  await expect(page.locator('#r4mUrl')).toHaveText(/^https?:\/\//);
  await expect(page.locator('#previewDomain')).not.toHaveText('—');
});

test('mobile navigation opens filter and inspect sheets without horizontal overflow', async ({ page }, testInfo) => {
  if (testInfo.project.name !== 'mobile-chromium') test.skip();
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitReady(page);

  await page.locator('[data-mobile-action="filter"]').first().click();
  await expect(page.locator('#r4mFilterSheet')).toHaveClass(/\bopen\b/);
  await page.locator('[data-mobile-action="close-sheets"]').first().click();

  await page.locator('[data-mobile-action="inspect"]').click();
  await expect(page.locator('#r4mInspectSheet')).toHaveClass(/\bopen\b/);

  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }));
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport + 1);
});

test('changing viewport width switches shells without reloading', async ({ page }, testInfo) => {
  if (testInfo.project.name === 'mobile-chromium') test.skip();
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitReady(page);
  await expect(page.locator('html')).toHaveAttribute('data-r4b1t-interface', 'desktop');
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('html')).toHaveAttribute('data-r4b1t-interface', 'mobile');
  await page.setViewportSize({ width: 1280, height: 800 });
  await expect(page.locator('html')).toHaveAttribute('data-r4b1t-interface', 'desktop');
});
