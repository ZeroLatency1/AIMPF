import { test, expect } from '@playwright/test';

test('AIMPF home smoke', async ({ page }) => {
  await page.goto('/');

  await expect(
    page.getByRole('link', { name: 'AIMPF', exact: true })
  ).toBeVisible();

  await expect(
    page.getByText(/Predict the consequences of AI-system changes/)
  ).toBeVisible();
});
