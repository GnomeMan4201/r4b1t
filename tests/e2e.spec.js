'use strict';

const { test, expect } = require('@playwright/test');

async function blockExternalNetwork(page) {
  await page.route('**/*', async (route) => {
    const requestUrl = route.request().url();
    if (requestUrl.startsWith('data:') || requestUrl.startsWith('blob:')) {
      await route.continue();
      return;
    }

    const parsed = new URL(requestUrl);
    if (parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost') {
      await route.continue();
      return;
    }
    await route.abort('blockedbyclient');
  });
}

async function waitForApplicationReady(page) {
  await page.waitForFunction(() => (
    typeof window.roll === 'function'
    && typeof window.toggleHelp === 'function'
  ));
  await page.waitForSelector('#r4mShellHost');
}

async function rollFromVisibleShell(page, testInfo) {
  if (testInfo.project.name === 'mobile-chromium') {
    await page.locator('#r4mRoll').click();
  } else {
    await page.locator('#btnGo').click();
  }
}

test.beforeEach(async ({ page }) => {
  await blockExternalNetwork(page);
});

test('loads the correct application shell without runtime errors', async ({ page }, testInfo) => {
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));

  const response = await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitForApplicationReady(page);

  expect(response).not.toBeNull();
  expect(response.status()).toBe(200);
  await expect(page).toHaveTitle('r4b1t');
  await expect(page.locator('#trailItems')).toBeAttached();
  await expect(page.locator('#counter')).toBeAttached();

  if (testInfo.project.name === 'mobile-chromium') {
    await expect(page.locator('html')).toHaveAttribute('data-r4b1t-interface', 'mobile');
    await expect(page.locator('.r4m-shell')).toBeVisible();
    await expect(page.locator('#r4mRoll')).toBeEnabled();
  } else {
    await expect(page.locator('html')).toHaveAttribute('data-r4b1t-interface', 'desktop');
    await expect(page.locator('.wordmark')).toBeVisible();
    await expect(page.locator('#btnGo')).toBeVisible();
    await expect(page.locator('#btnGo')).toBeEnabled();
  }

  expect(pageErrors).toEqual([]);
});

test('a roll selects a corpus URL through either shell', async ({ page }, testInfo) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitForApplicationReady(page);
  await rollFromVisibleShell(page, testInfo);

  await expect(page.locator('#previewDomain')).not.toHaveText('—');
  await expect(page.locator('#previewUrl')).toHaveText(/^https?:\/\//);

  if (testInfo.project.name === 'mobile-chromium') {
    await expect(page.locator('#r4mRoute')).toBeVisible();
    await expect(page.locator('#r4mDomain')).not.toHaveText('—');
    await expect(page.locator('#r4mUrl')).toHaveText(/^https?:\/\//);
    await expect(page.locator('[data-mobile-action="visit"]')).toBeEnabled();
  } else {
    await expect(page.locator('#preview')).toBeVisible();
    await expect(page.locator('#btnVisitMain')).toBeVisible();
    await expect(page.locator('#btnVisitMain')).toBeEnabled();
  }
});

test('keyboard help opens and closes without navigation', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitForApplicationReady(page);

  await page.keyboard.press('KeyH');
  await expect(page.locator('#helpOverlay')).toHaveClass(/\bopen\b/);
  await expect(page.locator('.help-modal')).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(page.locator('#helpOverlay')).not.toHaveClass(/\bopen\b/);
});

test('the initial viewport does not overflow horizontally', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitForApplicationReady(page);

  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }));

  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport + 1);
});

test('mobile viewport exposes one-thumb controls', async ({ page }, testInfo) => {
  if (testInfo.project.name !== 'mobile-chromium') test.skip();

  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await waitForApplicationReady(page);

  await expect(page.locator('#r4mRoll')).toBeVisible();
  await expect(page.locator('.r4m-nav')).toBeVisible();
  await expect(page.locator('[data-mobile-action="filter"]').first()).toBeVisible();
  await page.locator('#r4mRoll').click();
  await expect(page.locator('#r4mRoute')).toBeVisible();
  await expect(page.locator('[data-mobile-action="visit"]')).toBeVisible();
});
