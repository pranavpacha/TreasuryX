import { describe, expect, it } from "vitest";
import { cmyToRgb, hsvToRgb, rgbToCmy, rgbToHsv } from "./colorModels";

describe("RGB <-> CMY round trip", () => {
  it("recovers the original RGB after converting to CMY and back", () => {
    const cmy = rgbToCmy(59, 130, 246);
    const back = cmyToRgb(cmy.c, cmy.m, cmy.y);
    expect(back.r).toBeCloseTo(59, 0);
    expect(back.g).toBeCloseTo(130, 0);
    expect(back.b).toBeCloseTo(246, 0);
  });

  it("pure white has CMY all zero", () => {
    const cmy = rgbToCmy(255, 255, 255);
    expect(cmy.c).toBeCloseTo(0);
    expect(cmy.m).toBeCloseTo(0);
    expect(cmy.y).toBeCloseTo(0);
  });

  it("pure black has CMY all one", () => {
    const cmy = rgbToCmy(0, 0, 0);
    expect(cmy.c).toBeCloseTo(1);
    expect(cmy.m).toBeCloseTo(1);
    expect(cmy.y).toBeCloseTo(1);
  });
});

describe("RGB <-> HSV round trip", () => {
  it("recovers the original RGB after converting to HSV and back", () => {
    const hsv = rgbToHsv(200, 50, 100);
    const back = hsvToRgb(hsv.h, hsv.s, hsv.v);
    expect(back.r).toBeCloseTo(200, 0);
    expect(back.g).toBeCloseTo(50, 0);
    expect(back.b).toBeCloseTo(100, 0);
  });

  it("pure red is hue 0, full saturation and value", () => {
    const hsv = rgbToHsv(255, 0, 0);
    expect(hsv.h).toBeCloseTo(0);
    expect(hsv.s).toBeCloseTo(1);
    expect(hsv.v).toBeCloseTo(1);
  });

  it("pure green is hue 120", () => {
    const hsv = rgbToHsv(0, 255, 0);
    expect(hsv.h).toBeCloseTo(120);
  });

  it("grayscale colors have zero saturation", () => {
    const hsv = rgbToHsv(128, 128, 128);
    expect(hsv.s).toBeCloseTo(0);
  });
});
