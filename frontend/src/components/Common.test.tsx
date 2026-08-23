import { describe, expect, it } from "vitest";
import { fmtInr, fmtNumber, toneFor } from "./Common";

describe("fmtNumber", () => {
  it("formats with default 2 decimals", () => {
    expect(fmtNumber(1234.5)).toBe("1,234.50");
  });
  it("formats with 0 decimals", () => {
    expect(fmtNumber(1234.5, 0)).toBe("1,235");
  });
});

describe("fmtInr", () => {
  it("formats crores for values >= 1 crore", () => {
    expect(fmtInr(15_000_000)).toBe("₹1.50Cr");
  });
  it("formats lakhs for values >= 1 lakh and < 1 crore", () => {
    expect(fmtInr(250_000)).toBe("₹2.50L");
  });
  it("formats plain rupees for small values", () => {
    expect(fmtInr(4200)).toBe("₹4,200");
  });
  it("preserves negative sign", () => {
    expect(fmtInr(-15_000_000)).toBe("-₹1.50Cr");
  });
});

describe("toneFor", () => {
  it("returns up for positive", () => { expect(toneFor(5)).toBe("up"); });
  it("returns down for negative", () => { expect(toneFor(-5)).toBe("down"); });
  it("returns neutral for zero", () => { expect(toneFor(0)).toBe("neutral"); });
});
