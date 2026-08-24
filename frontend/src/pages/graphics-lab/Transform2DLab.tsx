import { useMemo, useState } from "react";
import { Badge, Panel } from "../../components/Common";
import { ClipWindow, Segment, cohenSutherlandClip, liangBarskyClip } from "../../graphics/clipping";
import {
  Mat3, Point2, composeTransforms, rotationMatrix, scalingMatrix,
  shearMatrix, transformPolygon, translationMatrix,
} from "../../graphics/transform2d";

const SVG_SIZE = 320;
const WORLD_HALF = 10;

function toScreen([x, y]: Point2): Point2 {
  const scale = SVG_SIZE / (2 * WORLD_HALF);
  return [SVG_SIZE / 2 + x * scale, SVG_SIZE / 2 - y * scale];
}

function MatrixView({ m, label }: { m: Mat3; label: string }) {
  return (
    <div style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>
      <div style={{ color: "var(--text-mid)", marginBottom: 3 }}>{label}</div>
      {m.map((row, i) => (
        <div key={i}>[{row.map((v) => v.toFixed(2)).join(", ")}]</div>
      ))}
    </div>
  );
}

const SHAPE: Point2[] = [[-2, -1], [2, -1], [2, 1], [-2, 1], [-2, -1]]; // a small "bond bar" rectangle

function TransformPanel() {
  const [tx, setTx] = useState(2); const [ty, setTy] = useState(1);
  const [rot, setRot] = useState(20);
  const [sx, setSx] = useState(1.3); const [sy, setSy] = useState(1.0);
  const [shx, setShx] = useState(0); const [shy, setShy] = useState(0);
  const [order, setOrder] = useState<("T" | "R" | "S" | "SH")[]>(["S", "R", "T"]);

  const matrices: Record<string, Mat3> = {
    T: translationMatrix(tx, ty), R: rotationMatrix(rot), S: scalingMatrix(sx, sy), SH: shearMatrix(shx, shy),
  };
  const composite = useMemo(() => composeTransforms(order.map((k) => matrices[k])), [order, tx, ty, rot, sx, sy, shx, shy]);
  const transformed = transformPolygon(composite, SHAPE);

  const toggleOrder = (k: "T" | "R" | "S" | "SH") => {
    setOrder((o) => (o.includes(k) ? o.filter((x) => x !== k) : [...o, k]));
  };

  return (
    <Panel title="2D Transformations — Homogeneous Coordinates & Composite Transforms">
      <div className="grid grid-2">
        <div>
          <div className="grid grid-2">
            <div className="field"><label>Translate X</label><input type="range" min={-5} max={5} step={0.5} value={tx} onChange={(e) => setTx(Number(e.target.value))} /></div>
            <div className="field"><label>Translate Y</label><input type="range" min={-5} max={5} step={0.5} value={ty} onChange={(e) => setTy(Number(e.target.value))} /></div>
            <div className="field"><label>Rotate (deg)</label><input type="range" min={-180} max={180} value={rot} onChange={(e) => setRot(Number(e.target.value))} /></div>
            <div className="field"><label>Scale X</label><input type="range" min={0.2} max={2.5} step={0.1} value={sx} onChange={(e) => setSx(Number(e.target.value))} /></div>
            <div className="field"><label>Scale Y</label><input type="range" min={0.2} max={2.5} step={0.1} value={sy} onChange={(e) => setSy(Number(e.target.value))} /></div>
            <div className="field"><label>Shear X</label><input type="range" min={-1} max={1} step={0.1} value={shx} onChange={(e) => setShx(Number(e.target.value))} /></div>
            <div className="field"><label>Shear Y</label><input type="range" min={-1} max={1} step={0.1} value={shy} onChange={(e) => setShy(Number(e.target.value))} /></div>
          </div>
          <label>Composition order (click to toggle inclusion, applied left-to-right)</label>
          <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
            {(["S", "R", "SH", "T"] as const).map((k) => (
              <button key={k} onClick={() => toggleOrder(k)} style={{ fontWeight: order.includes(k) ? 700 : 400, borderColor: order.includes(k) ? "var(--accent)" : undefined }}>
                {k} {order.includes(k) && `(${order.indexOf(k) + 1})`}
              </button>
            ))}
          </div>
          <MatrixView m={composite} label={`Composite matrix M = ${order.map((k) => k).reverse().join(" · ")} (applied ${order.join(" then ")})`} />
        </div>
        <svg width={SVG_SIZE} height={SVG_SIZE} style={{ background: "#05070a", border: "1px solid var(--border)", borderRadius: 3 }}>
          <line x1={0} y1={SVG_SIZE / 2} x2={SVG_SIZE} y2={SVG_SIZE / 2} stroke="#262d3a" />
          <line x1={SVG_SIZE / 2} y1={0} x2={SVG_SIZE / 2} y2={SVG_SIZE} stroke="#262d3a" />
          <polygon points={SHAPE.map((p) => toScreen(p).join(",")).join(" ")} fill="none" stroke="#616b7d" strokeWidth={1.5} strokeDasharray="4 3" />
          <polygon points={transformed.map((p) => toScreen(p).join(",")).join(" ")} fill="rgba(59,130,246,0.15)" stroke="var(--accent)" strokeWidth={2} />
        </svg>
      </div>
    </Panel>
  );
}

function ClippingPanel() {
  const [seg, setSeg] = useState<Segment>({ x0: -9, y0: -6, x1: 9, y1: 7 });
  const win: ClipWindow = { xmin: -4, xmax: 4, ymin: -3, ymax: 3 };
  const cs = useMemo(() => cohenSutherlandClip(seg, win), [seg]);
  const lb = useMemo(() => liangBarskyClip(seg, win), [seg]);

  return (
    <Panel title="Line Clipping — Cohen–Sutherland & Liang–Barsky">
      <div className="grid grid-2" style={{ marginBottom: 8 }}>
        <div className="field"><label>x0</label><input type="number" value={seg.x0} onChange={(e) => setSeg({ ...seg, x0: Number(e.target.value) })} /></div>
        <div className="field"><label>y0</label><input type="number" value={seg.y0} onChange={(e) => setSeg({ ...seg, y0: Number(e.target.value) })} /></div>
        <div className="field"><label>x1</label><input type="number" value={seg.x1} onChange={(e) => setSeg({ ...seg, x1: Number(e.target.value) })} /></div>
        <div className="field"><label>y1</label><input type="number" value={seg.y1} onChange={(e) => setSeg({ ...seg, y1: Number(e.target.value) })} /></div>
      </div>
      <div className="grid grid-2">
        <div>
          <Badge kind={cs.segment ? "info" : "warn"}>Cohen–Sutherland: {cs.segment ? "ACCEPTED" : "REJECTED"}</Badge>
          <ul style={{ fontSize: 10.5, color: "var(--text-mid)", marginTop: 6 }}>{cs.steps.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
        <div>
          <Badge kind={lb.segment ? "info" : "warn"}>Liang–Barsky: {lb.segment ? "ACCEPTED" : "REJECTED"}</Badge>
          <ul style={{ fontSize: 10.5, color: "var(--text-mid)", marginTop: 6 }}>{lb.steps.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      </div>
      <svg width={SVG_SIZE} height={SVG_SIZE} style={{ background: "#05070a", border: "1px solid var(--border)", borderRadius: 3, marginTop: 10 }}>
        <rect
          x={toScreen([win.xmin, win.ymax])[0]} y={toScreen([win.xmin, win.ymax])[1]}
          width={toScreen([win.xmax, win.ymin])[0] - toScreen([win.xmin, win.ymax])[0]}
          height={toScreen([win.xmax, win.ymin])[1] - toScreen([win.xmin, win.ymax])[1]}
          fill="rgba(59,130,246,0.08)" stroke="var(--accent)" strokeDasharray="3 2"
        />
        <line {...{ x1: toScreen([seg.x0, seg.y0])[0], y1: toScreen([seg.x0, seg.y0])[1], x2: toScreen([seg.x1, seg.y1])[0], y2: toScreen([seg.x1, seg.y1])[1] }} stroke="#616b7d" strokeWidth={1.5} strokeDasharray="4 3" />
        {cs.segment && (
          <line
            x1={toScreen([cs.segment.x0, cs.segment.y0])[0]} y1={toScreen([cs.segment.x0, cs.segment.y0])[1]}
            x2={toScreen([cs.segment.x1, cs.segment.y1])[0]} y2={toScreen([cs.segment.x1, cs.segment.y1])[1]}
            stroke="var(--up)" strokeWidth={3}
          />
        )}
      </svg>
    </Panel>
  );
}

export default function Transform2DLab() {
  return (
    <div>
      <TransformPanel />
      <ClippingPanel />
    </div>
  );
}
