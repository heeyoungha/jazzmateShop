import '@testing-library/jest-dom/vitest';
import { transferableAbortController } from 'node:util';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { server } from './msw/server';
import { requestLog } from './msw/handlers';

class TestAbortController {
  constructor() {
    return transferableAbortController();
  }
}

globalThis.AbortController = TestAbortController as typeof AbortController;
window.AbortController = TestAbortController as typeof AbortController;

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

afterEach(() => {
  server.resetHandlers();
  requestLog.reset();
});

afterAll(() => server.close());
