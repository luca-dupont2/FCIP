import { test, expect } from '@playwright/test';

test.describe('FCIP Dashboard', () => {
  test('loads the app and shows FCIP title in sidebar', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('FCIP')).toBeVisible();
    await expect(page.getByText('FPGA Compile Intelligence')).toBeVisible();
  });

  test('renders all sidebar navigation links', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('link', { name: 'Projects' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Experiments' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Compare' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Predictions' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Recommendations' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible();
  });

  test('navigates to Experiments page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Experiments' }).click();
    await expect(page).toHaveURL(/\/experiments/);
  });

  test('navigates to Settings page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Settings' }).click();
    await expect(page).toHaveURL(/\/settings/);
  });

  test('navigates to Predictions page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Predictions' }).click();
    await expect(page).toHaveURL(/\/predictions/);
  });
});
