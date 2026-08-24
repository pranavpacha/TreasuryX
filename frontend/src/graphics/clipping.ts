/** Line clipping algorithms against an axis-aligned rectangular window -- CS4104 Module 2. */

export interface ClipWindow { xmin: number; xmax: number; ymin: number; ymax: number; }
export interface Segment { x0: number; y0: number; x1: number; y1: number; }

const INSIDE = 0, LEFT = 1, RIGHT = 2, BOTTOM = 4, TOP = 8;

function outcode(x: number, y: number, w: ClipWindow): number {
  let code = INSIDE;
  if (x < w.xmin) code |= LEFT;
  else if (x > w.xmax) code |= RIGHT;
  if (y < w.ymin) code |= BOTTOM;
  else if (y > w.ymax) code |= TOP;
  return code;
}

/** Cohen-Sutherland: classifies each endpoint into a 4-bit outcode region relative to the
 * clip window, then iteratively clips against whichever boundary an out-of-bounds endpoint
 * violates until the segment is trivially accepted (both codes 0) or rejected (codes share a
 * bit, i.e. both points are outside on the same side). */
export function cohenSutherlandClip(seg: Segment, w: ClipWindow): { segment: Segment | null; steps: string[] } {
  let { x0, y0, x1, y1 } = seg;
  let code0 = outcode(x0, y0, w);
  let code1 = outcode(x1, y1, w);
  const steps: string[] = [`Initial outcodes: A=${code0.toString(2).padStart(4, "0")} B=${code1.toString(2).padStart(4, "0")}`];

  for (let iter = 0; iter < 8; iter++) {
    if ((code0 | code1) === 0) {
      steps.push("Both outcodes 0 -> trivially ACCEPT");
      return { segment: { x0, y0, x1, y1 }, steps };
    }
    if ((code0 & code1) !== 0) {
      steps.push("Outcodes share a set bit -> trivially REJECT (fully outside on one side)");
      return { segment: null, steps };
    }
    const codeOut = code0 !== 0 ? code0 : code1;
    let x = 0, y = 0;
    if (codeOut & TOP) { x = x0 + (x1 - x0) * (w.ymax - y0) / (y1 - y0); y = w.ymax; }
    else if (codeOut & BOTTOM) { x = x0 + (x1 - x0) * (w.ymin - y0) / (y1 - y0); y = w.ymin; }
    else if (codeOut & RIGHT) { y = y0 + (y1 - y0) * (w.xmax - x0) / (x1 - x0); x = w.xmax; }
    else { y = y0 + (y1 - y0) * (w.xmin - x0) / (x1 - x0); x = w.xmin; }

    if (codeOut === code0) {
      x0 = x; y0 = y; code0 = outcode(x0, y0, w);
      steps.push(`Clipped point A to (${x.toFixed(1)}, ${y.toFixed(1)}), new outcode ${code0.toString(2).padStart(4, "0")}`);
    } else {
      x1 = x; y1 = y; code1 = outcode(x1, y1, w);
      steps.push(`Clipped point B to (${x.toFixed(1)}, ${y.toFixed(1)}), new outcode ${code1.toString(2).padStart(4, "0")}`);
    }
  }
  return { segment: null, steps };
}

/** Liang-Barsky: parametrizes the line as P(t) = P0 + t*(P1-P0), t in [0,1], and clips the
 * parametric range against each of the 4 window boundaries algebraically (no iteration over
 * boundary crossings the way Cohen-Sutherland does) -- generally fewer operations per line. */
export function liangBarskyClip(seg: Segment, w: ClipWindow): { segment: Segment | null; steps: string[] } {
  const dx = seg.x1 - seg.x0;
  const dy = seg.y1 - seg.y0;
  let t0 = 0, t1 = 1;
  const p = [-dx, dx, -dy, dy];
  const q = [seg.x0 - w.xmin, w.xmax - seg.x0, seg.y0 - w.ymin, w.ymax - seg.y0];
  const steps: string[] = [];

  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) {
      if (q[i] < 0) {
        steps.push(`Edge ${i}: line parallel to boundary and outside -> REJECT`);
        return { segment: null, steps };
      }
      continue;
    }
    const r = q[i] / p[i];
    if (p[i] < 0) {
      if (r > t1) { steps.push(`Edge ${i}: t0 candidate ${r.toFixed(3)} > t1 -> REJECT`); return { segment: null, steps }; }
      if (r > t0) { t0 = r; steps.push(`Edge ${i}: raise t0 to ${r.toFixed(3)}`); }
    } else {
      if (r < t0) { steps.push(`Edge ${i}: t1 candidate ${r.toFixed(3)} < t0 -> REJECT`); return { segment: null, steps }; }
      if (r < t1) { t1 = r; steps.push(`Edge ${i}: lower t1 to ${r.toFixed(3)}`); }
    }
  }

  const clipped: Segment = {
    x0: seg.x0 + t0 * dx, y0: seg.y0 + t0 * dy,
    x1: seg.x0 + t1 * dx, y1: seg.y0 + t1 * dy,
  };
  steps.push(`Final t range [${t0.toFixed(3)}, ${t1.toFixed(3)}] -> ACCEPT`);
  return { segment: clipped, steps };
}
