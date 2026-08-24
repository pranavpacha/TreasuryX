import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import { Badge, Panel } from "../../components/Common";

function OverlappingPlanes({ depthTest }: { depthTest: boolean }) {
  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[3, 4, 2]} intensity={0.8} />
      {/* Blue plane drawn first, farther away */}
      <mesh position={[0, 0, -0.5]}>
        <planeGeometry args={[2.5, 2.5]} />
        <meshBasicMaterial color="#3b82f6" depthTest={depthTest} side={2} />
      </mesh>
      {/* Red plane drawn second, closer -- with depth test ON it correctly occludes the blue
          plane where they overlap; with depth test OFF, whichever draws last simply wins,
          ignoring actual distance. */}
      <mesh position={[0.6, 0.3, 0.5]}>
        <planeGeometry args={[2, 2]} />
        <meshBasicMaterial color="#e5484d" depthTest={depthTest} side={2} />
      </mesh>
    </>
  );
}

function WebglDepthSection() {
  const [depthTest, setDepthTest] = useState(true);
  return (
    <Panel title="WebGL Depth Buffer (Z-buffer) Toggle">
      <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>
        The red plane is physically closer to the camera than the blue one. With the depth test ON, the GPU's
        per-pixel Z-buffer correctly resolves occlusion regardless of draw order. With it OFF, whichever object
        is drawn last simply overwrites the framebuffer -- occlusion becomes draw-order-dependent and wrong.
      </p>
      <label style={{ marginBottom: 8, display: "block" }}>
        <input type="checkbox" checked={depthTest} onChange={(e) => setDepthTest(e.target.checked)} /> Depth test enabled
      </label>
      <Badge kind={depthTest ? "info" : "warn"}>{depthTest ? "CORRECT occlusion" : "INCORRECT occlusion (depth test disabled)"}</Badge>
      <div style={{ height: 260, background: "#05070a", borderRadius: 4, border: "1px solid var(--border)", marginTop: 8 }}>
        <Canvas camera={{ position: [0, 0, 4], fov: 45 }}>
          <OverlappingPlanes depthTest={depthTest} />
          <OrbitControls />
        </Canvas>
      </div>
    </Panel>
  );
}

/** A literal, from-scratch implementation of the Z-buffer / depth-buffer algorithm on a 2D
 * canvas -- CS4104 Module 3 lab requirement ("Implement the Z-buffer algorithm for hidden
 * surface removal"). Two overlapping rectangles, each with a per-pixel depth (nearer = smaller
 * z), are rasterized into a shared color buffer + depth buffer using the textbook algorithm:
 * initialize depth to +infinity everywhere; for each pixel of each primitive, only draw
 * (and update the depth buffer) if the primitive's depth at that pixel is nearer than what's
 * currently stored. */
function SoftwareZBufferDemo() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const W = 200, H = 200, SCALE = 2;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const depthBuffer = new Float32Array(W * H).fill(Infinity);
    const colorBuffer = new Uint8ClampedArray(W * H * 3).fill(10);

    // Rectangle A: farther (larger z), blue
    const rectA = { x0: 30, y0: 30, x1: 150, y1: 120, z: 0.8, color: [59, 130, 246] };
    // Rectangle B: nearer (smaller z), red -- overlaps A in the bottom-right region
    const rectB = { x0: 80, y0: 80, x1: 180, y1: 170, z: 0.3, color: [229, 72, 77] };

    const rasterize = (rect: typeof rectA) => {
      for (let y = rect.y0; y < rect.y1; y++) {
        for (let x = rect.x0; x < rect.x1; x++) {
          const idx = y * W + x;
          if (rect.z < depthBuffer[idx]) {  // the actual Z-buffer test
            depthBuffer[idx] = rect.z;
            colorBuffer[idx * 3] = rect.color[0];
            colorBuffer[idx * 3 + 1] = rect.color[1];
            colorBuffer[idx * 3 + 2] = rect.color[2];
          }
        }
      }
    };
    rasterize(rectA);
    rasterize(rectB);

    const imageData = ctx.createImageData(W, H);
    for (let i = 0; i < W * H; i++) {
      imageData.data[i * 4] = colorBuffer[i * 3];
      imageData.data[i * 4 + 1] = colorBuffer[i * 3 + 1];
      imageData.data[i * 4 + 2] = colorBuffer[i * 3 + 2];
      imageData.data[i * 4 + 3] = 255;
    }
    const off = document.createElement("canvas");
    off.width = W; off.height = H;
    off.getContext("2d")!.putImageData(imageData, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, W * SCALE, H * SCALE);
    ctx.drawImage(off, 0, 0, W * SCALE, H * SCALE);
  }, []);

  return (
    <Panel title="Software Z-Buffer Algorithm (from scratch, pixel-by-pixel)">
      <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>
        Rectangle A (blue, z=0.8, farther) is rasterized first; Rectangle B (red, z=0.3, nearer) is rasterized
        second and overlaps A's bottom-right corner. Despite being drawn second, B correctly wins in the overlap
        region only because its z is smaller -- this is the actual per-pixel depth comparison, not draw order.
      </p>
      <canvas ref={canvasRef} width={W * SCALE} height={H * SCALE} style={{ border: "1px solid var(--border)", borderRadius: 3 }} />
    </Panel>
  );
}

export default function DepthBufferLab() {
  return (
    <div>
      <SoftwareZBufferDemo />
      <WebglDepthSection />
    </div>
  );
}
