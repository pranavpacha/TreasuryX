import { describe, expect, it } from "vitest";
import { bresenhamLine, ddaLine, midpointCircle } from "./rasterAlgorithms";

describe("ddaLine", () => {
  it("draws a horizontal line", () => {
    const pixels = ddaLine(0, 0, 5, 0);
    expect(pixels).toHaveLength(6);
    expect(pixels.every((p) => p.y === 0)).toBe(true);
    expect(pixels[0]).toEqual({ x: 0, y: 0 });
    expect(pixels[5]).toEqual({ x: 5, y: 0 });
  });

  it("draws a 45-degree diagonal line", () => {
    const pixels = ddaLine(0, 0, 4, 4);
    expect(pixels).toHaveLength(5);
    pixels.forEach((p, i) => expect(p).toEqual({ x: i, y: i }));
  });

  it("handles a single-point line", () => {
    expect(ddaLine(3, 3, 3, 3)).toEqual([{ x: 3, y: 3 }]);
  });
});

describe("bresenhamLine", () => {
  it("draws a horizontal line matching DDA", () => {
    expect(bresenhamLine(0, 0, 5, 0)).toEqual(ddaLine(0, 0, 5, 0));
  });

  it("draws a steep line without gaps (each step moves at most 1px on x or y)", () => {
    const pixels = bresenhamLine(0, 0, 3, 10);
    for (let i = 1; i < pixels.length; i++) {
      const dx = Math.abs(pixels[i].x - pixels[i - 1].x);
      const dy = Math.abs(pixels[i].y - pixels[i - 1].y);
      expect(dx).toBeLessThanOrEqual(1);
      expect(dy).toBeLessThanOrEqual(1);
    }
  });

  it("connects the exact start and end points", () => {
    const pixels = bresenhamLine(2, 3, 14, 9);
    expect(pixels[0]).toEqual({ x: 2, y: 3 });
    expect(pixels[pixels.length - 1]).toEqual({ x: 14, y: 9 });
  });
});

describe("midpointCircle", () => {
  it("produces points all at approximately the given radius from center", () => {
    const cx = 20, cy = 20, r = 10;
    const pixels = midpointCircle(cx, cy, r);
    expect(pixels.length).toBeGreaterThan(0);
    for (const p of pixels) {
      const dist = Math.sqrt((p.x - cx) ** 2 + (p.y - cy) ** 2);
      expect(dist).toBeGreaterThan(r - 1.5);
      expect(dist).toBeLessThan(r + 1.5);
    }
  });

  it("is symmetric across all 4 quadrants", () => {
    const pixels = midpointCircle(0, 0, 8);
    const has = (x: number, y: number) => pixels.some((p) => p.x === x && p.y === y);
    // Pick one plotted point and verify its mirror across each axis is also present
    const sample = pixels.find((p) => p.x !== 0 && p.y !== 0)!;
    expect(has(sample.x, sample.y)).toBe(true);
    expect(has(-sample.x, sample.y)).toBe(true);
    expect(has(sample.x, -sample.y)).toBe(true);
    expect(has(-sample.x, -sample.y)).toBe(true);
  });
});
