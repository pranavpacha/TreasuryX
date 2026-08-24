import { useMemo, useState } from "react";
import { Panel, Tooltip } from "../../components/Common";
import { PixelCanvas } from "../../components/PixelCanvas";
import { cmyToRgb, hsvToRgb, rgbToCmy, rgbToHsv } from "../../graphics/colorModels";
import { bresenhamLine, ddaLine, midpointCircle } from "../../graphics/rasterAlgorithms";

const GRID = 32;

function LineAlgorithmPanel({ title, algo, notes }: { title: string; algo: (x0: number, y0: number, x1: number, y1: number) => { x: number; y: number }[]; notes: string }) {
  const [x0, setX0] = useState(2); const [y0, setY0] = useState(3);
  const [x1, setX1] = useState(27); const [y1, setY1] = useState(18);
  const pixels = useMemo(() => algo(x0, y0, x1, y1), [algo, x0, y0, x1, y1]);

  return (
    <Panel title={title}>
      <div className="grid grid-2">
        <div>
          <div className="grid grid-4" style={{ marginBottom: 8 }}>
            <div className="field"><label>x0</label><input type="number" value={x0} onChange={(e) => setX0(Number(e.target.value))} /></div>
            <div className="field"><label>y0</label><input type="number" value={y0} onChange={(e) => setY0(Number(e.target.value))} /></div>
            <div className="field"><label>x1</label><input type="number" value={x1} onChange={(e) => setX1(Number(e.target.value))} /></div>
            <div className="field"><label>y1</label><input type="number" value={y1} onChange={(e) => setY1(Number(e.target.value))} /></div>
          </div>
          <p style={{ fontSize: 11, color: "var(--text-mid)" }}>{notes}</p>
          <div style={{ fontSize: 11 }}>Pixels plotted: <strong>{pixels.length}</strong></div>
        </div>
        <PixelCanvas gridSize={GRID} pixels={pixels} />
      </div>
    </Panel>
  );
}

function MidpointCirclePanel() {
  const [cx, setCx] = useState(16); const [cy, setCy] = useState(16); const [r, setR] = useState(10);
  const pixels = useMemo(() => midpointCircle(cx, cy, r), [cx, cy, r]);
  return (
    <Panel title="Midpoint Circle Drawing Algorithm">
      <div className="grid grid-2">
        <div>
          <div className="grid grid-3" style={{ marginBottom: 8 }}>
            <div className="field"><label>center x</label><input type="number" value={cx} onChange={(e) => setCx(Number(e.target.value))} /></div>
            <div className="field"><label>center y</label><input type="number" value={cy} onChange={(e) => setCy(Number(e.target.value))} /></div>
            <div className="field"><label>radius</label><input type="number" value={r} onChange={(e) => setR(Number(e.target.value))} /></div>
          </div>
          <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
            Computes one octant using an integer decision parameter (avoiding sqrt/trig per pixel), then mirrors the
            points across all 8 octants by circular symmetry.
          </p>
          <div style={{ fontSize: 11 }}>Pixels plotted: <strong>{pixels.length}</strong></div>
        </div>
        <PixelCanvas gridSize={GRID} pixels={pixels} color="var(--up)" />
      </div>
    </Panel>
  );
}

function ColorModelWidget() {
  const [r, setR] = useState(59); const [g, setG] = useState(130); const [b, setB] = useState(246);
  const cmy = rgbToCmy(r, g, b);
  const hsv = rgbToHsv(r, g, b);
  const rgbFromCmy = cmyToRgb(cmy.c, cmy.m, cmy.y);
  const rgbFromHsv = hsvToRgb(hsv.h, hsv.s, hsv.v);

  return (
    <Panel title="Color Models — RGB / CMY / HSV">
      <div className="grid grid-3">
        <div className="field"><label>R</label><input type="range" min={0} max={255} value={r} onChange={(e) => setR(Number(e.target.value))} /></div>
        <div className="field"><label>G</label><input type="range" min={0} max={255} value={g} onChange={(e) => setG(Number(e.target.value))} /></div>
        <div className="field"><label>B</label><input type="range" min={0} max={255} value={b} onChange={(e) => setB(Number(e.target.value))} /></div>
      </div>
      <div style={{ display: "flex", gap: 16, alignItems: "center", marginTop: 8 }}>
        <div style={{ width: 60, height: 60, background: `rgb(${r},${g},${b})`, border: "1px solid var(--border)", borderRadius: 4 }} />
        <table className="data-table">
          <tbody>
            <tr><td style={{ textAlign: "left" }}>RGB</td><td>({r}, {g}, {b})</td></tr>
            <tr><td style={{ textAlign: "left" }}>CMY</td><td>({cmy.c.toFixed(2)}, {cmy.m.toFixed(2)}, {cmy.y.toFixed(2)})</td></tr>
            <tr><td style={{ textAlign: "left" }}>HSV</td><td>({hsv.h.toFixed(0)}°, {hsv.s.toFixed(2)}, {hsv.v.toFixed(2)})</td></tr>
            <tr><td style={{ textAlign: "left" }}>CMY → RGB round-trip <Tooltip text="Converting back verifies the transform is invertible" /></td><td>({rgbFromCmy.r}, {rgbFromCmy.g}, {rgbFromCmy.b})</td></tr>
            <tr><td style={{ textAlign: "left" }}>HSV → RGB round-trip</td><td>({rgbFromHsv.r}, {rgbFromHsv.g}, {rgbFromHsv.b})</td></tr>
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

export default function Raster2DLab() {
  return (
    <div>
      <Panel title="Raster Graphics — CS4104 Module 1 (Technical Evidence)">
        <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
          Modern GPUs rasterize lines and circles in hardware, so a WebGL scene never runs this code. These are the
          actual pixel-generation algorithms, implemented explicitly in TypeScript and plotted pixel-by-pixel on a
          32x32 grid (not the canvas's built-in line/arc drawing) — see <code>src/graphics/rasterAlgorithms.ts</code>.
        </p>
      </Panel>
      <LineAlgorithmPanel
        title="DDA (Digital Differential Analyzer) Line Algorithm"
        algo={ddaLine}
        notes="Steps along the dominant axis using floating-point increments, rounding to the nearest pixel each step. Simple but relies on float arithmetic and rounding."
      />
      <LineAlgorithmPanel
        title="Bresenham's Line Algorithm"
        algo={bresenhamLine}
        notes="Integer-only arithmetic using a running error term to decide whether to step diagonally -- the classic hardware-efficient alternative to DDA."
      />
      <MidpointCirclePanel />
      <ColorModelWidget />
    </div>
  );
}
