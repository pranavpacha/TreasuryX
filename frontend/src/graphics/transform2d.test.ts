import { describe, expect, it } from "vitest";
import {
  applyToPoint, composeTransforms, identity3, multiply3, reflectionMatrix,
  rotationMatrix, scalingMatrix, shearMatrix, translationMatrix,
} from "./transform2d";

describe("multiply3 / applyToPoint", () => {
  it("identity matrix leaves points unchanged", () => {
    expect(applyToPoint(identity3, [3, -2])).toEqual([3, -2]);
  });

  it("multiplying by identity returns the same matrix", () => {
    const m = rotationMatrix(30);
    expect(multiply3(m, identity3)).toEqual(m);
    expect(multiply3(identity3, m)).toEqual(m);
  });
});

describe("translationMatrix", () => {
  it("translates a point by (tx, ty)", () => {
    const m = translationMatrix(5, -3);
    expect(applyToPoint(m, [1, 1])).toEqual([6, -2]);
  });
});

describe("rotationMatrix", () => {
  it("rotates (1,0) by 90 degrees to approximately (0,1)", () => {
    const m = rotationMatrix(90);
    const [x, y] = applyToPoint(m, [1, 0]);
    expect(x).toBeCloseTo(0, 5);
    expect(y).toBeCloseTo(1, 5);
  });

  it("360 degree rotation is the identity", () => {
    const m = rotationMatrix(360);
    const [x, y] = applyToPoint(m, [2, 3]);
    expect(x).toBeCloseTo(2, 5);
    expect(y).toBeCloseTo(3, 5);
  });
});

describe("scalingMatrix", () => {
  it("scales x and y independently", () => {
    const m = scalingMatrix(2, 3);
    expect(applyToPoint(m, [1, 1])).toEqual([2, 3]);
  });
});

describe("reflectionMatrix", () => {
  it("reflects across the x axis", () => {
    expect(applyToPoint(reflectionMatrix("x"), [3, 4])).toEqual([3, -4]);
  });
  it("reflects across the y axis", () => {
    expect(applyToPoint(reflectionMatrix("y"), [3, 4])).toEqual([-3, 4]);
  });
  it("reflects across the origin", () => {
    expect(applyToPoint(reflectionMatrix("origin"), [3, 4])).toEqual([-3, -4]);
  });
});

describe("shearMatrix", () => {
  it("shears x proportional to y", () => {
    const m = shearMatrix(0.5, 0);
    expect(applyToPoint(m, [0, 2])).toEqual([1, 2]);
  });
});

describe("composeTransforms", () => {
  it("applies transforms in the stated left-to-right order (translate then rotate != rotate then translate)", () => {
    const translateThenRotate = composeTransforms([translationMatrix(2, 0), rotationMatrix(90)]);
    const rotateThenTranslate = composeTransforms([rotationMatrix(90), translationMatrix(2, 0)]);

    // Start at origin, translate by (2,0) -> (2,0), then rotate 90 -> (0,2)
    const p1 = applyToPoint(translateThenRotate, [0, 0]);
    expect(p1[0]).toBeCloseTo(0, 5);
    expect(p1[1]).toBeCloseTo(2, 5);

    // Start at origin, rotate 90 -> (0,0) still, then translate -> (2,0)
    const p2 = applyToPoint(rotateThenTranslate, [0, 0]);
    expect(p2[0]).toBeCloseTo(2, 5);
    expect(p2[1]).toBeCloseTo(0, 5);
  });

  it("empty list of transforms is the identity", () => {
    expect(composeTransforms([])).toEqual(identity3);
  });
});
