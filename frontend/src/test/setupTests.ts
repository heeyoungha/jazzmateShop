import "@testing-library/jest-dom/vitest";
import { transferableAbortController } from "node:util";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./msw/server";
import { requestLog } from "./msw/handlers";

class TestAbortController {
  constructor() {
    return transferableAbortController();
  }
}

globalThis.AbortController = TestAbortController as typeof AbortController;
window.AbortController = TestAbortController as typeof AbortController;

// jsdom에 IntersectionObserver가 없으므로 mock으로 대체
// scroll 이벤트 발생 시 isIntersecting=true로 콜백 (1회 scroll → 1회 콜백)
class MockIntersectionObserver {
  private callback: IntersectionObserverCallback;
  private targets: Map<Element, EventListener> = new Map();
  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback;
  }
  observe(target: Element) {
    let pending = false;
    const handler = () => {
      if (pending) return;
      pending = true;
      this.callback(
        [{ isIntersecting: true, target } as IntersectionObserverEntry],
        this as unknown as IntersectionObserver,
      );
      setTimeout(() => {
        pending = false;
      }, 0);
    };
    this.targets.set(target, handler);
    window.addEventListener("scroll", handler);
  }
  unobserve(target: Element) {
    const handler = this.targets.get(target);
    if (handler) {
      window.removeEventListener("scroll", handler);
      this.targets.delete(target);
    }
  }
  disconnect() {
    this.targets.forEach((handler) =>
      window.removeEventListener("scroll", handler),
    );
    this.targets.clear();
  }
}
globalThis.IntersectionObserver =
  MockIntersectionObserver as unknown as typeof IntersectionObserver;

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));

afterEach(() => {
  server.resetHandlers();
  requestLog.reset();
});

afterAll(() => server.close());
