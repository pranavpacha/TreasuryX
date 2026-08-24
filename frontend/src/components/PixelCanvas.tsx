import { useEffect, useRef } from "react";
import type { Pixel } from "../graphics/rasterAlgorithms";

interface PixelCanvasProps {
  gridSize: number;
  cellPx?: number;
  pixels: Pixel[];
  color?: string;
  secondaryPixels?: Pixel[];
  secondaryColor?: string;
}

/** Renders a discrete pixel grid (each logical pixel drawn as a filled square), origin at
 * bottom-left, so the algorithm's actual integer output is what's visible -- not a smooth
 * canvas-native line/arc. */
export function PixelCanvas({ gridSize, cellPx = 8, pixels, color = "#3b82f6", secondaryPixels, secondaryColor = "#e5484d" }: PixelCanvasProps) {
  const ref = useRef<HTMLCanvasElement>(null);
  const size = gridSize * cellPx;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = "#05070a";
    ctx.fillRect(0, 0, size, size);

    ctx.strokeStyle = "#161b24";
    ctx.lineWidth = 1;
    for (let i = 0; i <= gridSize; i++) {
      ctx.beginPath(); ctx.moveTo(i * cellPx, 0); ctx.lineTo(i * cellPx, size); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * cellPx); ctx.lineTo(size, i * cellPx); ctx.stroke();
    }

    const plot = (p: Pixel, c: string) => {
      if (p.x < 0 || p.y < 0 || p.x >= gridSize || p.y >= gridSize) return;
      ctx.fillStyle = c;
      const py = gridSize - 1 - p.y; // flip so y increases upward
      ctx.fillRect(p.x * cellPx + 1, py * cellPx + 1, cellPx - 2, cellPx - 2);
    };
    secondaryPixels?.forEach((p) => plot(p, secondaryColor));
    pixels.forEach((p) => plot(p, color));
  }, [gridSize, cellPx, pixels, color, secondaryPixels, secondaryColor, size]);

  return <canvas ref={ref} width={size} height={size} style={{ border: "1px solid var(--border)", borderRadius: 3, imageRendering: "pixelated" }} />;
}
