import { OrbitControls } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import * as THREE from "three";

/**
 * A genuine custom vertex + fragment shader (GLSL, via THREE.ShaderMaterial) driving a 3D
 * yield-curve surface. Height comes from real yield values (passed in as `heights`); color is
 * computed per-fragment from an interactive `riskThreshold` uniform -- points above the
 * threshold shade red, below shade the accent blue, with a soft transition band. This is
 * hand-written GLSL, not a material-property tweak on a built-in material.
 */

const VERTEX_SHADER = `
varying float vHeight;
varying vec3 vNormal;
void main() {
  vHeight = position.y;
  vNormal = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const FRAGMENT_SHADER = `
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
  vec3 lit = baseColor * (0.4 + 0.6 * diffuse);
  gl_FragColor = vec4(lit, 1.0);
}
`;

/** Renders the mesh + drives its animated uniform. Must live INSIDE <Canvas> -- useFrame
 * (like all r3f hooks) only works within the Canvas's render tree, not in the parent
 * component that renders the <Canvas> element itself. */
function YieldMesh({ geometry, uniforms }: { geometry: THREE.BufferGeometry; uniforms: Record<string, THREE.IUniform> }) {
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    (uniforms.uLightDir.value as THREE.Vector3).set(Math.sin(t * 0.3) * 2, 3, Math.cos(t * 0.3) * 2);
  });
  return (
    <mesh geometry={geometry}>
      <shaderMaterial vertexShader={VERTEX_SHADER} fragmentShader={FRAGMENT_SHADER} side={THREE.DoubleSide} uniforms={uniforms} />
    </mesh>
  );
}

export function ShaderYieldSurface({
  yields, riskThreshold,
}: { yields: number[]; riskThreshold: number }) {
  const geometry = useMemo(() => {
    const n = yields.length;
    const positions: number[] = [];
    const indices: number[] = [];
    const min = Math.min(...yields), max = Math.max(...yields);
    const range = max - min || 1;
    const depth = 2;
    for (let row = 0; row < 2; row++) {
      for (let i = 0; i < n; i++) {
        const x = (i / (n - 1)) * 8 - 4;
        const y = ((yields[i] - min) / range) * 3;
        const z = row === 0 ? -depth / 2 : depth / 2;
        positions.push(x, y, z);
      }
    }
    for (let i = 0; i < n - 1; i++) {
      const a = i, b = i + 1, c = n + i, d = n + i + 1;
      indices.push(a, c, b, b, c, d);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geo.setIndex(indices);
    geo.computeVertexNormals();
    return geo;
  }, [yields]);

  const maxHeight = 3; // matches the height normalization in the geometry above (always scaled into [0,3])

  // A stable uniforms object (created once) whose `.value` fields are mutated in place --
  // replacing the whole object on every render would break Three.js's cached uniform
  // bindings from the initial shader compile.
  const uniforms = useMemo(() => ({
    uThreshold: { value: riskThreshold },
    uMaxHeight: { value: maxHeight },
    uLowColor: { value: new THREE.Color("#3b82f6") },
    uHighColor: { value: new THREE.Color("#e5484d") },
    uLightDir: { value: new THREE.Vector3(2, 3, 2) },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), []);

  useEffect(() => {
    uniforms.uThreshold.value = riskThreshold;
  }, [riskThreshold, uniforms]);

  return (
    <div style={{ height: 320, background: "#05070a", borderRadius: 4, border: "1px solid var(--border)" }}>
      <Canvas camera={{ position: [7, 5, 7], fov: 45 }}>
        <YieldMesh geometry={geometry} uniforms={uniforms} />
        <OrbitControls />
      </Canvas>
    </div>
  );
}

export { VERTEX_SHADER, FRAGMENT_SHADER };
