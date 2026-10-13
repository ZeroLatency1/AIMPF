import { test, expect } from '@playwright/test';

const project = {
  id: 1,
  name: 'Customer Support AI',
  description: 'Demo project',
  aimi: 74.2,
  components: 8,
  dependencies: 8,
};

const components = [
  { id: 4, name: 'RAG Pipeline', type: 'RAG_PIPELINE' },
  { id: 3, name: 'LLM', type: 'LLM' },
];

const tests = [
  {
    id: 2,
    test_name: 'retrieval_recall',
    behavior_dimensions_covered: ['retrieval_quality', 'grounding'],
    estimated_cost: 1.2,
    expected_information_gain: 0.55,
  },
];

async function mockApi(page: any) {
  await page.route('**/api/**', async (route: any) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/\/+$/, '');
    const method = route.request().method();

    if (path === '/api/health') {
      return route.fulfill({
        json: { status: 'ok', service: 'AIMPF' },
      });
    }

    if (path === '/api/projects' && method === 'GET') {
      return route.fulfill({ json: [project] });
    }

    if (path === '/api/projects/1/components') {
      return route.fulfill({ json: components });
    }

    if (path === '/api/projects/1/dashboard') {
      return route.fulfill({
        json: {
          project,
          high_risk: 1,
          trend: [
            { label: '2026-09-01', aimi: 72 },
            { label: '2026-09-10', aimi: 74.2 },
          ],
          recent: [
            {
              id: 1,
              change_type: 'KNOWLEDGE_UPDATE',
              overall_impact: 0.77,
              risk: 'HIGH',
            },
          ],
        },
      });
    }

    if (path === '/api/projects/1/metrics') {
      return route.fulfill({
        json: [
          { id: 1, metric_name: 'AIMI', value: 74.2 },
          { id: 2, metric_name: 'CCS', value: 20 },
        ],
      });
    }

    if (path === '/api/projects/1/graph') {
      return route.fulfill({
        json: {
          nodes: components.map((c) => ({
            id: String(c.id),
            label: c.name,
          })),
          edges: [],
        },
      });
    }

    if (path === '/api/projects/1/recommendations') {
      return route.fulfill({
        json: [
          {
            priority: 'HIGH',
            title: 'Improve grounding',
            reason: 'Observed weakness',
            action: 'Run regression evaluation.',
          },
        ],
      });
    }

    if (path === '/api/validation/tests') {
      return route.fulfill({
        status: 200,
        json: tests,
      });
    }

    if (path === '/api/projects/1/validation') {
      return route.fulfill({
        json: { results: [], calibration: [] },
      });
    }

    if (
      path === '/api/projects/1/evaluations' ||
      path === '/api/projects/1/evaluations/summary' ||
      path === '/api/projects/1/experiments'
    ) {
      return route.fulfill({ json: [] });
    }

    return route.fulfill({ json: {} });
  });
}

test('home renders the core workflow', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');

  await expect(
    page.getByRole('link', { name: 'AIMPF', exact: true })
  ).toBeVisible();

  await expect(
    page.getByText(/Adaptive Counterfactual Validation/)
  ).toBeVisible();
});

test('projects workspace renders project cards', async ({ page }) => {
  await mockApi(page);
  await page.goto('/projects');

  await expect(
    page.getByRole('heading', {
      name: 'Customer Support AI',
      exact: true,
    })
  ).toBeVisible();

  await expect(page.getByText('Dashboard')).toBeVisible();
});

test('change workspace is project-aware', async ({ page }) => {
  await mockApi(page);
  await page.goto('/changes');

  await expect(page.getByText('Simulate Change')).toBeVisible();
  await expect(page.getByText('Analyze impact')).toBeVisible();
});

test('validation workspace renders adaptive test selector', async ({ page }) => {
  await mockApi(page);
  await page.goto('/validation');

  await expect(
    page.getByText('Adaptive Counterfactual Validation')
  ).toBeVisible();

  await expect(
    page.getByRole('option', {
      name: 'retrieval_recall',
      exact: true,
    })
  ).toHaveCount(1);
});

test('evaluation workspace renders RAG evaluator', async ({ page }) => {
  await mockApi(page);
  await page.goto('/evaluations');

  await expect(page.getByText('Offline RAG evaluator')).toBeVisible();
  await expect(page.getByText('Evaluate RAG')).toBeVisible();
});

test('experiment workspace renders comparison controls', async ({ page }) => {
  await mockApi(page);
  await page.goto('/experiments');

  await expect(page.getByText('Run baseline comparison')).toBeVisible();
});

