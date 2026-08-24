/**
 * 2D transformations via 3x3 homogeneous-coordinate matrices -- CS4104 Module 2.
 * Matrices are row-major 3x3 arrays; points are (x, y, 1)^T column vectors.
 */

export type Mat3 = [[number, number, number], [number, number, number], [number, number, number]];
export type Point2 = [number, number];

export const identity3: Mat3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];

export function multiply3(a: Mat3, b: Mat3): Mat3 {
  const result: Mat3 = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (let i = 0; i < 3; i++) {
    for (let j = 0; j < 3; j++) {
      result[i][j] = a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j];
    }
  }
  return result;
}

export function applyToPoint(m: Mat3, p: Point2): Point2 {
  const x = m[0][0] * p[0] + m[0][1] * p[1] + m[0][2];
  const y = m[1][0] * p[0] + m[1][1] * p[1] + m[1][2];
  return [x, y];
}

export function translationMatrix(tx: number, ty: number): Mat3 {
  return [[1, 0, tx], [0, 1, ty], [0, 0, 1]];
}

export function rotationMatrix(degrees: number): Mat3 {
  const rad = (degrees * Math.PI) / 180;
  const c = Math.cos(rad), s = Math.sin(rad);
  return [[c, -s, 0], [s, c, 0], [0, 0, 1]];
}

export function scalingMatrix(sx: number, sy: number): Mat3 {
  return [[sx, 0, 0], [0, sy, 0], [0, 0, 1]];
}

export function reflectionMatrix(axis: "x" | "y" | "origin"): Mat3 {
  if (axis === "x") return [[1, 0, 0], [0, -1, 0], [0, 0, 1]];
  if (axis === "y") return [[-1, 0, 0], [0, 1, 0], [0, 0, 1]];
  return [[-1, 0, 0], [0, -1, 0], [0, 0, 1]];
}

export function shearMatrix(shx: number, shy: number): Mat3 {
  return [[1, shx, 0], [shy, 1, 0], [0, 0, 1]];
}

/** Composes transforms in the given order (first entry applied first). "Apply T1 then T2 then
 * T3" corresponds to the matrix product T3 * T2 * T1, so each new matrix is pre-multiplied
 * onto the accumulator as we walk the list left to right. */
export function composeTransforms(matrices: Mat3[]): Mat3 {
  return matrices.reduce((acc, m) => multiply3(m, acc), identity3);
}

export function transformPolygon(m: Mat3, points: Point2[]): Point2[] {
  return points.map((p) => applyToPoint(m, p));
}
