import "@testing-library/jest-dom";

// jsdom has no ResizeObserver; Recharts' ResponsiveContainer needs one to mount at all.
// A no-op stub is standard practice for testing Recharts under jsdom -- layout/resize
// behavior itself isn't what these tests exercise.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver = ResizeObserverStub;
