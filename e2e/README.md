# E2E Tests - JazzMate Shop

End-to-end tests for the JazzMate jazz music review and recommendation platform using Playwright.

## Project Structure

```
e2e/
├── fixtures/              # Test data and fixtures
│   └── test-data.ts      # Reusable test data (users, reviews, albums)
├── page-objects/         # Page Object Model classes
│   ├── base.page.ts      # Base page with common functionality
│   ├── home.page.ts      # Home page object
│   └── write-review.page.ts  # Write review page object
├── utils/                # Helper utilities
│   ├── api-helpers.ts    # API interaction helpers
│   └── page-helpers.ts   # Page interaction helpers
├── screenshots/          # Test failure screenshots (gitignored)
├── test-results/         # Test execution artifacts (gitignored)
├── .env.example          # Example environment variables
└── README.md            # This file
```

## Prerequisites

- Node.js 20+
- All services running:
  - Frontend (React + Vite): `http://localhost:3000`
  - Backend (Spring Boot): `http://localhost:8080`
  - AI Service (FastAPI): `http://localhost:8000`

## Installation

```bash
# Install root dependencies (includes Playwright)
npm install

# Install Playwright browsers
npx playwright install
```

## Configuration

1. Copy the example environment file:
```bash
cp e2e/.env.example e2e/.env
```

2. Adjust settings in `e2e/.env` if needed (defaults work for local development)

## Running Tests

### All Tests (Headless)
```bash
npm run test:e2e
```

### With Browser UI
```bash
npm run test:e2e:headed
```

### Interactive UI Mode
```bash
npm run test:e2e:ui
```

### Debug Mode (Step Through)
```bash
npm run test:e2e:debug
```

### Specific Browser
```bash
npm run test:e2e:chromium
npm run test:e2e:firefox
npm run test:e2e:webkit
```

### Mobile Viewports
```bash
npm run test:e2e:mobile
```

### View Test Report
```bash
npm run test:e2e:report
```

## Test Development

### Generating Test Code
Use Playwright's code generator to record interactions:
```bash
npm run test:e2e:codegen
```

### Writing Tests

1. **Use Page Objects** for reusable page interactions
2. **Use Fixtures** for consistent test data
3. **Use Helpers** for common operations

Example test structure:
```typescript
import { test, expect } from '@playwright/test';
import { HomePage } from '../page-objects/home.page';
import { testReviews } from '../fixtures/test-data';

test('user can submit a review', async ({ page }) => {
  const homePage = new HomePage(page);
  await homePage.goto();
  await homePage.goToWriteReview();

  // Test logic here...
});
```

## Architecture Considerations

### Async Recommendation Generation
JazzMate uses asynchronous processing for AI recommendations:
- Review submission returns immediately (~150ms)
- Recommendations generate in background (~6 seconds)
- Tests must use `waitForRecommendations()` helper

### API vs UI Testing
- **Direct API calls**: Use `api-helpers.ts` for setup/cleanup
- **UI interactions**: Use page objects for user workflows
- **Hybrid approach**: API setup + UI validation = faster, more stable tests

## CI/CD Integration

Tests run automatically on GitHub Actions for:
- Push to `main`, `master`, or `develop` branches
- Pull requests to those branches

The CI workflow:
1. Starts PostgreSQL service
2. Builds and starts Backend (Spring Boot)
3. Starts AI Service (FastAPI)
4. Starts Frontend (Vite)
5. Runs Playwright tests
6. Uploads test reports as artifacts

## Troubleshooting

### Tests Timing Out
- Increase timeouts in `playwright.config.ts`
- Check that all services are running and healthy
- Use `--headed` mode to see what's happening

### Flaky Tests
- Add explicit waits: `await page.waitForLoadState('networkidle')`
- Use `waitForRecommendations()` for async operations
- Avoid hard-coded delays; use `waitFor*` methods

### Screenshots Not Captured
- Check `e2e/screenshots/` directory exists
- Verify `screenshot: 'only-on-failure'` in config
- Use `await page.screenshot()` for manual captures

## Best Practices

1. **Isolation**: Each test should be independent and idempotent
2. **Cleanup**: Use API helpers to clean up test data after tests
3. **Selectors**: Prefer `getByRole`, `getByLabel` over CSS selectors
4. **Assertions**: Use Playwright's `expect()` for auto-retry
5. **Data**: Use fixtures for consistent, realistic test data

## Performance

- **Parallel execution**: Tests run in parallel by default
- **Test sharding**: Use `--shard` flag for distributed execution
- **Browser reuse**: `webServer.reuseExistingServer` avoids restarts

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [API Reference](https://playwright.dev/docs/api/class-playwright)
- [Project README](../CLAUDE.md) for system architecture
