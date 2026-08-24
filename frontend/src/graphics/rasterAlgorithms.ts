/**
 * Low-level rasterization algorithms -- CS4104 Module 1 lab requirements
 * ("Implement DDA and Bresenham line drawing algorithms", "Implement the Midpoint Circle
 * Drawing Algorithm"). Modern GPUs rasterize lines/circles in hardware, so a WebGL scene
 * never exercises this code path -- these are implemented explicitly, pixel-by-pixel, on a
 * 2D canvas grid so the actual integer algorithms (not the browser's built-in line/arc
 * drawing) are what's running and visible.
 */

export interface Pixel { x: number; y: number; }

/** Digital Differential Analyzer: steps along the line's dominant axis using floating-point
 * increments, rounding to the nearest pixel each step. Simple but uses float arithmetic. */
export function ddaLine(x0: number, y0: number, x1: number, y1: number): Pixel[] {
  const dx = x1 - x0;
  const dy = y1 - y0;
  const steps = Math.max(Math.abs(dx), Math.abs(dy));
  if (steps === 0) return [{ x: Math.round(x0), y: Math.round(y0) }];
  const xInc = dx / steps;
  const yInc = dy / steps;
  const pixels: Pixel[] = [];
  let x = x0, y = y0;
  for (let i = 0; i <= steps; i++) {
    pixels.push({ x: Math.round(x), y: Math.round(y) });
    x += xInc;
    y += yInc;
  }
  return pixels;
}

/** Bresenham's line algorithm: integer-only arithmetic using a running error term to decide
 * whether to step diagonally -- the classic hardware-friendly alternative to DDA. */
export function bresenhamLine(x0: number, y0: number, x1: number, y1: number): Pixel[] {
  x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
  const pixels: Pixel[] = [];
  const dx = Math.abs(x1 - x0);
  const dy = -Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1;
  const sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  let x = x0, y = y0;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    pixels.push({ x, y });
    if (x === x1 && y === y1) break;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x += sx; }
    if (e2 <= dx) { err += dx; y += sy; }
  }
  return pixels;
}

/** Midpoint Circle Algorithm: computes one octant using integer decisions, then mirrors the
 * points across all 8 octants by symmetry. */
export function midpointCircle(cx: number, cy: number, radius: number): Pixel[] {
  cx = Math.round(cx); cy = Math.round(cy); radius = Math.round(radius);
  const pixels: Pixel[] = [];
  let x = radius;
  let y = 0;
  let decision = 1 - radius;

  const plotOctants = (x: number, y: number) => {
    pixels.push(
      { x: cx + x, y: cy + y }, { x: cx - x, y: cy + y }, { x: cx + x, y: cy - y }, { x: cx - x, y: cy - y },
      { x: cx + y, y: cy + x }, { x: cx - y, y: cy + x }, { x: cx + y, y: cy - x }, { x: cx - y, y: cy - x },
    );
  };

  plotOctants(x, y);
  while (y < x) {
    y += 1;
    if (decision <= 0) {
      decision += 2 * y + 1;
    } else {
      x -= 1;
      decision += 2 * (y - x) + 1;
    }
    plotOctants(x, y);
  }
  return pixels;
}
