import {test,expect} from '@playwright/test'
test('AIMPF home smoke',async({page})=>{await page.goto('/');await expect(page.getByText('AIMPF')).toBeVisible();await expect(page.getByText(/Predict the consequences of AI-system changes/)).toBeVisible()})
