import { Html, OrbitControls, OrthographicCamera, PerspectiveCamera } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";

/**
 * Production 3D surface renderer for the Treasury visualizations (yield curve, FX volatility,
 * portfolio stress). Built from real BufferGeometry (not a canned chart library), so the
 * transformation / camera / projection / depth / lighting / shader pipeline is genuine and
 * inspectable -- this component IS the Computer Graphics implementation, not a separate demo of
 * it. See GraphicsDetailsPanel (rendered by the pages that use this) for the live introspection
 * UI, and docs/graphics_pipeline.md for the full writeup.
 *
 * Coordinate mapping (object space, right-handed, Y-up as in Three.js):
 *   world X <- column index (xLabels)     scaled to [-halfWidth, halfWidth]
 *   world Y <- normalized data value      scaled to [0, heightScale]  (the "height")
 *   world Z <- row index (yLabels)        scaled to [-halfDepth, halfDepth]
 */

export interface GraphicsMatrices {
  model: THREE.Matrix4;
  view: THREE.Matrix4;
  projection: THREE.Matrix4;
  depthTest: boolean;
  depthFuncName: string;
}

const DEPTH_FUNC_NAMES: Record<number, string> = {
  [THREE.NeverDepth]: "NEVER",
  [THREE.AlwaysDepth]: "ALWAYS",
  [THREE.LessDepth]: "LESS",
  [THREE.LessEqualDepth]: "LEQUAL",
  [THREE.EqualDepth]: "EQUAL",
  [THREE.GreaterEqualDepth]: "GEQUAL",
  [THREE.GreaterDepth]: "GREATER",
  [THREE.NotEqualDepth]: "NOTEQUAL",
};

export interface SurfacePlotProps {
  xLabels: string[]; // columns
  yLabels: string[]; // rows
  values: number[][]; // values[row][col]
  formatValue?: (v: number) => string;
  xAxisName: string;
  yAxisName: string; // height axis
  zAxisName: string; // depth axis (rows)
  colorMode?: "sequential" | "diverging"; // diverging centers at 0 (red/green P&L style)
  heightScale?: number;
  /** "material" = standard PBR-lite material (default). "shader" = the hand-written GLSL
   * risk shader, blending color by height vs. shaderThreshold -- this is the same production
   * code path used for every surface's "Risk View", not a separate demo shader. */
  renderMode?: "material" | "shader";
  shaderThreshold?: number;
  projectionMode?: "perspective" | "orthographic";
  fov?: number;
  depthTest?: boolean;
  ambientIntensity?: number;
  directionalIntensity?: number;
  onMatrices?: (m: GraphicsMatrices) => void;
}

function colorFor(norm: number, mode: "sequential" | "diverging"): THREE.Color {
  if (mode === "diverging") {
    // norm in [-1, 1]: red (loss) -> dark -> green (gain)
    if (norm >= 0) return new THREE.Color().setRGB(0.15 + 0.1 * (1 - norm), 0.55 + 0.35 * norm, 0.35);
    const n = -norm;
    return new THREE.Color().setRGB(0.55 + 0.35 * n, 0.15 + 0.1 * (1 - n), 0.3);
  }
  // sequential: blue (low) -> amber (high), matches terminal accent palette
  return new THREE.Color().setHSL(0.58 - 0.45 * norm, 0.55, 0.35 + 0.25 * norm);
}

function buildGeometry(values: number[][], colorMode: "sequential" | "diverging", heightScale: number) {
  const rows = values.length;
  const cols = values[0]?.length ?? 0;
  const flat = values.flat();
  const min = Math.min(...flat);
  const max = Math.max(...flat);
  const range = max - min || 1;
  const width = 10;
  const depth = 10;

  const positions = new Float32Array(rows * cols * 3);
  const colors = new Float32Array(rows * cols * 3);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      const v = values[r][c];
      const normHeight = (v - min) / range;
      const x = (c / Math.max(1, cols - 1)) * width - width / 2;
      const z = (r / Math.max(1, rows - 1)) * depth - depth / 2;
      const y = normHeight * heightScale;
      positions[idx * 3] = x;
      positions[idx * 3 + 1] = y;
      positions[idx * 3 + 2] = z;

      const normForColor = colorMode === "diverging" ? Math.max(-1, Math.min(1, v / (Math.max(Math.abs(min), Math.abs(max)) || 1))) : normHeight;
      const col = colorFor(normForColor, colorMode);
      colors[idx * 3] = col.r;
      colors[idx * 3 + 1] = col.g;
      colors[idx * 3 + 2] = col.b;
    }
  }

  const indices: number[] = [];
  for (let r = 0; r < rows - 1; r++) {
    for (let c = 0; c < cols - 1; c++) {
      const a = r * cols + c;
      const b = r * cols + c + 1;
      const cc = (r + 1) * cols + c;
      const d = (r + 1) * cols + c + 1;
      indices.push(a, cc, b, b, cc, d);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();

  return { geometry, positions, min, max, width, depth };
}

const RISK_VERTEX_SHADER = `
varying float vHeight;
varying vec3 vNormal;
void main() {
  vHeight = position.y;
  vNormal = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const RISK_FRAGMENT_SHADER = `
uniform float uThreshold;
uniform float uMaxHeight;
uniform vec3 uLowColor;
uniform vec3 uHighColor;
uniform vec3 uLightDir;
varying float vHeight;
varying vec3 vNormal;

void main() {
  float t = clamp(vHeight / max(uMaxHeight, 0.0001), 0.0, 1.0);
  float band = smoothstep(uThreshold - 0.05, uThreshold + 0.05, t);
  vec3 baseColor = mix(uLowColor, uHighColor, band);
  float diffuse = max(dot(normalize(vNormal), normalize(uLightDir)), 0.0);
  gl_FragColor = vec4(baseColor * (0.4 + 0.6 * diffuse), 1.0);
}
`;

export { RISK_FRAGMENT_SHADER, RISK_VERTEX_SHADER };

function Surface({
  values, colorMode, heightScale, renderMode, shaderThreshold, depthTest, onMatrices,
}: {
  values: number[][]; colorMode: "sequential" | "diverging"; heightScale: number;
  renderMode: "material" | "shader"; shaderThreshold: number; depthTest: boolean;
  onMatrices?: (m: GraphicsMatrices) => void;
}) {
  const { geometry, max: maxHeight } = useMemo(() => {
    const built = buildGeometry(values, colorMode, heightScale);
    return { ...built, max: heightScale }; // height is normalized into [0, heightScale] by construction
  }, [values, colorMode, heightScale]);
  const wireframe = useMemo(() => new THREE.WireframeGeometry(geometry), [geometry]);

  const uniforms = useMemo(() => ({
    uThreshold: { value: shaderThreshold },
    uMaxHeight: { value: maxHeight },
    uLowColor: { value: new THREE.Color("#3b82f6") },
    uHighColor: { value: new THREE.Color("#e5484d") },
    uLightDir: { value: new THREE.Vector3(2, 3, 2) },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [maxHeight]);
  uniforms.uThreshold.value = shaderThreshold;

  const { camera } = useThree();
  const meshRef = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    uniforms.uLightDir.value.set(Math.sin(t * 0.25) * 2, 3, Math.cos(t * 0.25) * 2);
    if (onMatrices && meshRef.current) {
      meshRef.current.updateMatrixWorld();
      camera.updateMatrixWorld();
      const material = meshRef.current.material as THREE.Material;
      onMatrices({
        model: meshRef.current.matrixWorld.clone(),
        view: camera.matrixWorldInverse.clone(),
        projection: (camera as THREE.PerspectiveCamera).projectionMatrix.clone(),
        depthTest: material.depthTest,
        depthFuncName: DEPTH_FUNC_NAMES[material.depthFunc] ?? `unknown (${material.depthFunc})`,
      });
    }
  });

  return (
    <group>
      <mesh geometry={geometry} ref={meshRef}>
        {renderMode === "shader" ? (
          <shaderMaterial vertexShader={RISK_VERTEX_SHADER} fragmentShader={RISK_FRAGMENT_SHADER} uniforms={uniforms} side={THREE.DoubleSide} depthTest={depthTest} />
        ) : (
          <meshStandardMaterial vertexColors flatShading side={THREE.DoubleSide} roughness={0.6} metalness={0.05} depthTest={depthTest} />
        )}
      </mesh>
      <lineSegments geometry={wireframe}>
        <lineBasicMaterial color="#0a0d12" transparent opacity={0.35} />
      </lineSegments>
    </group>
  );
}

function HoverMarkers({
  values, xLabels, yLabels, formatValue, heightScale,
}: {
  values: number[][]; xLabels: string[]; yLabels: string[]; formatValue: (v: number) => string; heightScale: number;
}) {
  const rows = values.length;
  const cols = values[0]?.length ?? 0;
  const flat = values.flat();
  const min = Math.min(...flat);
  const max = Math.max(...flat);
  const range = max - min || 1;
  const width = 10;
  const depth = 10;
  const [hover, setHover] = useState<{ r: number; c: number; pos: [number, number, number] } | null>(null);

  const points: { pos: [number, number, number]; r: number; c: number }[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const v = values[r][c];
      const x = (c / Math.max(1, cols - 1)) * width - width / 2;
      const z = (r / Math.max(1, rows - 1)) * depth - depth / 2;
      const y = ((v - min) / range) * heightScale;
      points.push({ pos: [x, y, z], r, c });
    }
  }

  return (
    <group>
      {points.map((p) => (
        <mesh
          key={`${p.r}-${p.c}`}
          position={p.pos}
          onPointerOver={(e) => { e.stopPropagation(); setHover({ r: p.r, c: p.c, pos: p.pos }); }}
          onPointerOut={() => setHover((h) => (h && h.r === p.r && h.c === p.c ? null : h))}
        >
          <sphereGeometry args={[0.06, 8, 8]} />
          <meshBasicMaterial color={hover && hover.r === p.r && hover.c === p.c ? "#e6e9ef" : "#3b82f6"} transparent opacity={hover && hover.r === p.r && hover.c === p.c ? 1 : 0.35} />
        </mesh>
      ))}
      {hover && (
        <Html position={hover.pos} distanceFactor={8} style={{ pointerEvents: "none" }}>
          <div style={{
            background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 4, padding: "4px 8px",
            fontSize: 11, color: "var(--text-hi)", whiteSpace: "nowrap", fontFamily: "monospace",
          }}>
            {xLabels[hover.c]} / {yLabels[hover.r]}: <strong>{formatValue(values[hover.r][hover.c])}</strong>
          </div>
        </Html>
      )}
    </group>
  );
}

export function SurfacePlot({
  xLabels, yLabels, values, formatValue = (v) => v.toFixed(2), xAxisName, yAxisName, zAxisName,
  colorMode = "sequential", heightScale = 3.5, renderMode = "material", shaderThreshold = 0.5,
  projectionMode = "perspective", fov = 45, depthTest = true,
  ambientIntensity = 0.55, directionalIntensity = 1.1, onMatrices,
}: SurfacePlotProps) {
  if (values.length === 0 || values[0].length === 0) {
    return <div className="empty-state">No data to visualize.</div>;
  }
  return (
    <div>
      <div style={{ height: 380, background: "#05070a", borderRadius: 4, border: "1px solid var(--border)" }}>
        <Canvas>
          {projectionMode === "perspective" ? (
            <PerspectiveCamera makeDefault position={[9, 7, 9]} fov={fov} near={0.1} far={100} />
          ) : (
            <OrthographicCamera makeDefault position={[9, 7, 9]} zoom={45} near={0.1} far={100} />
          )}
          <ambientLight intensity={ambientIntensity} />
          <directionalLight position={[6, 10, 4]} intensity={directionalIntensity} />
          <directionalLight position={[-6, 4, -4]} intensity={0.3} />
          <Surface values={values} colorMode={colorMode} heightScale={heightScale} renderMode={renderMode} shaderThreshold={shaderThreshold} depthTest={depthTest} onMatrices={onMatrices} />
          <HoverMarkers values={values} xLabels={xLabels} yLabels={yLabels} formatValue={formatValue} heightScale={heightScale} />
          <axesHelper args={[6]} />
          <OrbitControls enablePan enableZoom enableRotate makeDefault />
        </Canvas>
      </div>
      <div style={{ display: "flex", gap: 16, fontSize: 10.5, color: "var(--text-lo)", marginTop: 6 }}>
        <span>X axis: {xAxisName}</span>
        <span>Height (Y): {yAxisName}</span>
        <span>Z axis (depth): {zAxisName}</span>
        <span style={{ marginLeft: "auto" }}>Drag to rotate · scroll to zoom · hover a point for its value</span>
      </div>
    </div>
  );
}
