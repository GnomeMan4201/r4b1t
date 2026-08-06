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

test.beforeEach(async ({ page }) => {
  await blockExternalNetwork(page);
});

test('loads the core application shell without runtime errors', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));

  const response = await page.goto('./', { waitUntil: 'domcontentloaded' });

  expect(response).not.toBeNull();
  expect(response.status()).toBe(200);
  await expect(page).toHaveTitle('r4B1T_h0L3');
  await expect(page.locator('.wordmark')).toBeVisible();
  await expect(page.locator('.btn-go')).toBeVisible();
  await expect(page.locator('.btn-go')).toBeEnabled();
  await expect(page.locator('#trailItems')).toBeAttached();
  await expect(page.locator('.counter')).toBeVisible();
  expect(pageErrors).toEqual([]);
});

test('a roll selects a corpus URL and enables navigation controls', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.locator('.btn-go').click();

  await expect(page.locator('.preview')).toHaveClass(/\bvisible\b/);
  await expect(page.locator('.preview-url')).toHaveText(/^https?:\/\//);
  await expect(page.locator('.mode-toggle')).toHaveClass(/\bactive\b/);
  await expect(page.locator('.btn-visit')).toBeEnabled();
  await expect(page.locator('.btn-skip')).toBeEnabled();
});

test('keyboard help opens and closes without navigation', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });

  await page.keyboard.press('?');
  await expect(page.locator('.help-overlay')).toHaveClass(/\bopen\b/);
  await expect(page.locator('.help-modal')).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(page.locator('.help-overlay')).not.toHaveClass(/\bopen\b/);
});

test('the initial viewport does not overflow horizontally', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });

  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }));
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport + 1);
});
