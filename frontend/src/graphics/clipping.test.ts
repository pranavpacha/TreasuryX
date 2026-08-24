import { describe, expect, it } from "vitest";
import { ClipWindow, cohenSutherlandClip, liangBarskyClip } from "./clipping";

const WINDOW: ClipWindow = { xmin: -5, xmax: 5, ymin: -5, ymax: 5 };

describe("cohenSutherlandClip", () => {
  it("trivially accepts a line fully inside the window", () => {
    const result = cohenSutherlandClip({ x0: -2, y0: -2, x1: 2, y1: 2 }, WINDOW);
    expect(result.segment).toEqual({ x0: -2, y0: -2, x1: 2, y1: 2 });
  });

  it("trivially rejects a line fully outside on one side", () => {
    const result = cohenSutherlandClip({ x0: 10, y0: 10, x1: 20, y1: 20 }, WINDOW);
    expect(result.segment).toBeNull();
  });

  it("clips a line crossing the window boundary to the window edge", () => {
    const result = cohenSutherlandClip({ x0: -10, y0: 0, x1: 10, y1: 0 }, WINDOW);
    expect(result.segment).not.toBeNull();
    expect(result.segment!.x0).toBeCloseTo(-5, 5);
    expect(result.segment!.x1).toBeCloseTo(5, 5);
    expect(result.segment!.y0).toBeCloseTo(0, 5);
    expect(result.segment!.y1).toBeCloseTo(0, 5);
  });
});

describe("liangBarskyClip", () => {
  it("trivially accepts a line fully inside the window", () => {
    const result = liangBarskyClip({ x0: -2, y0: -2, x1: 2, y1: 2 }, WINDOW);
    expect(result.segment).not.toBeNull();
    expect(result.segment!.x0).toBeCloseTo(-2);
    expect(result.segment!.x1).toBeCloseTo(2);
  });

  it("rejects a line fully outside the window", () => {
    const result = liangBarskyClip({ x0: 10, y0: 10, x1: 20, y1: 20 }, WINDOW);
    expect(result.segment).toBeNull();
  });

  it("agrees with Cohen-Sutherland on a boundary-crossing line", () => {
    const seg = { x0: -10, y0: 0, x1: 10, y1: 0 };
    const cs = cohenSutherlandClip(seg, WINDOW);
    const lb = liangBarskyClip(seg, WINDOW);
    expect(cs.segment).not.toBeNull();
    expect(lb.segment).not.toBeNull();
    expect(lb.segment!.x0).toBeCloseTo(cs.segment!.x0, 5);
    expect(lb.segment!.x1).toBeCloseTo(cs.segment!.x1, 5);
  });

  it("clips a diagonal line to the correct parametric range", () => {
    const result = liangBarskyClip({ x0: -10, y0: -10, x1: 10, y1: 10 }, WINDOW);
    expect(result.segment).not.toBeNull();
    expect(result.segment!.x0).toBeCloseTo(-5, 5);
    expect(result.segment!.y0).toBeCloseTo(-5, 5);
    expect(result.segment!.x1).toBeCloseTo(5, 5);
    expect(result.segment!.y1).toBeCloseTo(5, 5);
  });
});
