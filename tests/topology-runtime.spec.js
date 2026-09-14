'use strict';

const { test, expect } = require('@playwright/test');

test('local topology maps verified snapshots and opens revealed stops', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.openTrailTopology === 'function' && typeof window.roll === 'function');
  await page.evaluate(() => window.roll());
  const result = await page.evaluate(async () => {
    const snapshot = await window.getTrailManifest();
    await window.openTrailTopology(snapshot);
    return {
      open: document.getElementById('trailTopologyOverlay').classList.contains('open'),
      cards: document.querySelectorAll('.topology-card').length,
      stops: document.querySelectorAll('.topology-stop[data-url]').length,
      title: document.getElementById('trailTopologyTitle').textContent,
    };
  });
  expect(result.open).toBe(true);
  expect(result.cards).toBe(1);
  expect(result.stops).toBeGreaterThan(0);
  expect(result.title).toBe('TRAIL TOPOLOGY');
});

test('topology remains inside the mobile viewport', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('mobile'), 'mobile-only layout assertion');
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.openTrailTopology === 'function');
  await page.evaluate(async () => window.openTrailTopology());
  const overflow = await page.evaluate(() => document.getElementById('trailTopologyOverlay').scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
});

test('sample topology shows revealed, concealed, inherited, and divergent wear together', async ({ page }) => {
  await page.goto('./', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.openTrailWearSample === 'function');
  const state = await page.evaluate(async () => {
    await window.openTrailWearSample();
    return {
      cards: document.querySelectorAll('.topology-card').length,
      revealed: document.querySelectorAll('.topology-wear .wear-step.revealed').length,
      concealed: document.querySelectorAll('.topology-wear .wear-step.concealed').length,
      inherited: document.querySelectorAll('.topology-wear .wear-step.inherited').length,
      divergent: document.querySelectorAll('.topology-wear .wear-step.divergent').length,
      forks: document.querySelectorAll('.topology-wear .wear-fork-mark').length,
      creases: document.querySelectorAll('.topology-wear .wear-crease').length,
      sampleStatus: document.getElementById('trailTopologyMap').textContent,
    };
  });
  expect(state.cards).toBe(2);
  expect(state.revealed).toBeGreaterThan(1);
  expect(state.concealed).toBeGreaterThan(0);
  expect(state.inherited).toBeGreaterThan(0);
  expect(state.divergent).toBeGreaterThan(0);
  expect(state.forks).toBeGreaterThan(0);
  expect(state.creases).toBeGreaterThan(0);
  expect(state.sampleStatus).toContain('NOT SAVED TO LOCAL ATLAS');
});
