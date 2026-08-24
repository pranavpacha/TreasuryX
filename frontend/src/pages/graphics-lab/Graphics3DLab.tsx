import { OrbitControls, OrthographicCamera, PerspectiveCamera } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useRef, useState } from "react";
import * as THREE from "three";
import { Link } from "react-router-dom";
import { Panel } from "../../components/Common";
import { MatrixReadout } from "../../three/MatrixReadout";

function TransformedBox({
  pos, rot, scale, onMatrices,
}: { pos: [number, number, number]; rot: [number, number, number]; scale: [number, number, number]; onMatrices: (m: THREE.Matrix4, v: THREE.Matrix4, p: THREE.Matrix4) => void }) {
  const ref = useRef<THREE.Mesh>(null);
  const { camera } = useThree();
  useFrame(() => {
    if (ref.current) {
      ref.current.updateMatrixWorld();
      camera.updateMatrixWorld();
      onMatrices(ref.current.matrixWorld, camera.matrixWorldInverse, (camera as THREE.PerspectiveCamera).projectionMatrix);
    }
  });
  return (
    <mesh ref={ref} position={pos} rotation={rot} scale={scale}>
      <boxGeometry args={[1.5, 1, 1]} />
      <meshStandardMaterial color="#3b82f6" />
    </mesh>
  );
}

function TransformMatrixSection() {
  const [pos, setPos] = useState<[number, number, number]>([1, 0.5, 0]);
  const [rot, setRot] = useState<[number, number, number]>([0, 0.5, 0]);
  const [scale, setScale] = useState<[number, number, number]>([1, 1, 1]);
  const [matrices, setMatrices] = useState<{ model: THREE.Matrix4; view: THREE.Matrix4; proj: THREE.Matrix4 } | null>(null);

  return (
    <Panel title="3D Transformations & the Model / View / Projection Pipeline">
      <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>
        Object space → (Model matrix) → World space → (View matrix) → Camera space → (Projection matrix) → Clip space → (perspective divide + viewport) → Screen space.
        Adjust the box below; the actual matrices Three.js computes are read out live, not simulated.
      </p>
      <div className="grid grid-2">
        <div>
          <div className="grid grid-3">
            {(["X", "Y", "Z"] as const).map((axis, i) => (
              <div className="field" key={`p${axis}`}><label>Position {axis}</label><input type="range" min={-3} max={3} step={0.1} value={pos[i]} onChange={(e) => { const p = [...pos] as [number, number, number]; p[i] = Number(e.target.value); setPos(p); }} /></div>
            ))}
            {(["X", "Y", "Z"] as const).map((axis, i) => (
              <div className="field" key={`r${axis}`}><label>Rotation {axis}</label><input type="range" min={-3.14} max={3.14} step={0.05} value={rot[i]} onChange={(e) => { const r = [...rot] as [number, number, number]; r[i] = Number(e.target.value); setRot(r); }} /></div>
            ))}
            {(["X", "Y", "Z"] as const).map((axis, i) => (
              <div className="field" key={`s${axis}`}><label>Scale {axis}</label><input type="range" min={0.3} max={2.5} step={0.1} value={scale[i]} onChange={(e) => { const s = [...scale] as [number, number, number]; s[i] = Number(e.target.value); setScale(s); }} /></div>
            ))}
          </div>
          {matrices && (
            <div style={{ marginTop: 10 }}>
              <MatrixReadout label="Model matrix (object → world)" matrix={matrices.model} />
              <MatrixReadout label="View matrix (world → camera)" matrix={matrices.view} />
              <MatrixReadout label="Projection matrix (camera → clip)" matrix={matrices.proj} />
            </div>
          )}
        </div>
        <div style={{ height: 340, background: "#05070a", borderRadius: 4, border: "1px solid var(--border)" }}>
          <Canvas camera={{ position: [5, 4, 5], fov: 45 }}>
            <ambientLight intensity={0.5} />
            <directionalLight position={[4, 5, 3]} intensity={1} />
            <TransformedBox pos={pos} rot={rot} scale={scale} onMatrices={(m, v, p) => setMatrices({ model: m, view: v, proj: p })} />
            <axesHelper args={[3]} />
            <OrbitControls />
          </Canvas>
        </div>
      </div>
    </Panel>
  );
}

function ProjectionCompareSection() {
  const [fov, setFov] = useState(45);
  const scene = (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[4, 5, 3]} intensity={1} />
      {[0, 1, 2, 3].map((i) => (
        <mesh key={i} position={[0, 0, -i * 2.2]}>
          <boxGeometry args={[1, 1, 1]} />
          <meshStandardMaterial color={i % 2 === 0 ? "#3b82f6" : "#2fbf71"} />
        </mesh>
      ))}
      <axesHelper args={[2]} />
    </>
  );
  return (
    <Panel title="Camera & Projection — Perspective vs. Orthographic">
      <div className="field" style={{ maxWidth: 240 }}>
        <label>Perspective FOV: {fov}°</label>
        <input type="range" min={15} max={110} value={fov} onChange={(e) => setFov(Number(e.target.value))} />
      </div>
      <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>
        Same 4 boxes receding along -Z in both scenes. Perspective: farther boxes appear smaller (foreshortening).
        Orthographic: parallel lines stay parallel and apparent size does not change with distance.
      </p>
      <div className="grid grid-2">
        <div>
          <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>Perspective projection</div>
          <div style={{ height: 240, background: "#05070a", borderRadius: 4, border: "1px solid var(--border)" }}>
            <Canvas>
              <PerspectiveCamera makeDefault position={[3, 2, 5]} fov={fov} near={0.1} far={50} />
              {scene}
              <OrbitControls />
            </Canvas>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>Orthographic projection</div>
          <div style={{ height: 240, background: "#05070a", borderRadius: 4, border: "1px solid var(--border)" }}>
            <Canvas>
              <OrthographicCamera makeDefault position={[3, 2, 5]} zoom={60} near={0.1} far={50} />
              {scene}
              <OrbitControls />
            </Canvas>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function LitObject({ ambient, directional, wireframe }: { ambient: number; directional: number; wireframe: boolean }) {
  return (
    <>
      <ambientLight intensity={ambient} />
      <directionalLight position={[3, 4, 2]} intensity={directional} />
      <mesh>
        <sphereGeometry args={[1.4, 32, 32]} />
        <meshStandardMaterial color="#3b82f6" roughness={0.4} metalness={0.3} wireframe={wireframe} />
      </mesh>
    </>
  );
}

function LightingSection() {
  const [ambient, setAmbient] = useState(0.4);
  const [directional, setDirectional] = useState(1.0);
  const [wireframe, setWireframe] = useState(false);

  return (
    <Panel title="Illumination Model & Shading">
      <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>
        Ambient light approximates indirect/global light (uniform, no direction). Directional light approximates a
        distant light source (e.g. sunlight) and contributes diffuse + specular terms based on the surface normal
        and view direction (Blinn-Phong, via MeshStandardMaterial's PBR-lite shading model).
      </p>
      <div className="grid grid-3" style={{ marginBottom: 8 }}>
        <div className="field"><label>Ambient intensity</label><input type="range" min={0} max={1.5} step={0.05} value={ambient} onChange={(e) => setAmbient(Number(e.target.value))} /></div>
        <div className="field"><label>Directional intensity</label><input type="range" min={0} max={2.5} step={0.05} value={directional} onChange={(e) => setDirectional(Number(e.target.value))} /></div>
        <div className="field"><label><input type="checkbox" checked={wireframe} onChange={(e) => setWireframe(e.target.checked)} /> Show wireframe (geometry)</label></div>
      </div>
      <div style={{ height: 260, background: "#05070a", borderRadius: 4, border: "1px solid var(--border)" }}>
        <Canvas camera={{ position: [3, 2, 4], fov: 45 }}>
          <LitObject ambient={ambient} directional={directional} wireframe={wireframe} />
          <OrbitControls />
        </Canvas>
      </div>
    </Panel>
  );
}

function ShaderPointerSection() {
  return (
    <Panel title="Custom GLSL Shader — Now in Production">
      <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
        The hand-written vertex + fragment shader that used to live only in this lab now powers the
        actual <strong>Risk View</strong> on the production 3D Market page (shared implementation in
        <code> frontend/src/three/SurfacePlot.tsx</code> — <code>RISK_VERTEX_SHADER</code> /
        <code> RISK_FRAGMENT_SHADER</code>), applied to real yield-curve, FX-volatility, and
        portfolio-stress data. See <Link to="/visualization/3d-market">3D Market</Link> and toggle
        Market View / Risk View there, with "Graphics Details" open to see the live uniforms.
        This keeps one implementation instead of a separate demo copy.
      </p>
    </Panel>
  );
}

export default function Graphics3DLab() {
  return (
    <div>
      <TransformMatrixSection />
      <ProjectionCompareSection />
      <LightingSection />
      <ShaderPointerSection />
    </div>
  );
}
