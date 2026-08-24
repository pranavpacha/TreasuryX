import * as THREE from "three";

function fmt4x4(elements: Float32Array | number[]): string[] {
  // three.js stores matrices column-major; transpose for conventional row display
  const m = Array.from(elements);
  const rows: string[] = [];
  for (let r = 0; r < 4; r++) {
    const row = [0, 1, 2, 3].map((c) => m[c * 4 + r].toFixed(2));
    rows.push(`[${row.join(", ")}]`);
  }
  return rows;
}

export function MatrixReadout({ label, matrix }: { label: string; matrix: THREE.Matrix4 }) {
  return (
    <div style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, marginBottom: 8 }}>
      <div style={{ color: "var(--text-mid)", marginBottom: 3 }}>{label}</div>
      {fmt4x4(matrix.elements).map((row, i) => <div key={i}>{row}</div>)}
    </div>
  );
}
