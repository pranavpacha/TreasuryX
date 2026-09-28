import type { ReactEventHandler } from "react";
import { useState } from "react";

export interface PixelRegion {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Displays an image with clickable highlight boxes over real detected regions (e.g. a
 * CvField's source_region, in the pixel coordinate space of the SAME resized image the
 * backend pipeline emitted -- see cv_engine/preprocessing.py, every stage shares one
 * resize so region coordinates are valid against any of them). Boxes are scaled from the
 * image's natural pixel size to its rendered CSS size, so this stays correct at any
 * viewport width. Used to make "image -> CV detection -> financial value" visually
 * obvious without faking exact geometric alignment.
 */
export function ImageRegionOverlay({
  src, regions, selectedIndex, onSelect, alt = "market snapshot",
}: {
  src: string;
  regions: (PixelRegion | null | undefined)[];
  selectedIndex?: number | null;
  onSelect?: (idx: number) => void;
  alt?: string;
}) {
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const [displayed, setDisplayed] = useState<{ w: number; h: number } | null>(null);

  const onLoad: ReactEventHandler<HTMLImageElement> = (e) => {
    const img = e.currentTarget;
    setNatural({ w: img.naturalWidth, h: img.naturalHeight });
    setDisplayed({ w: img.clientWidth, h: img.clientHeight });
  };

  const scaleX = natural && displayed && natural.w ? displayed.w / natural.w : 1;
  const scaleY = natural && displayed && natural.h ? displayed.h / natural.h : 1;

  return (
    <div style={{ position: "relative", display: "block", width: "100%" }}>
      <img
        src={src} alt={alt} onLoad={onLoad}
        style={{ width: "100%", display: "block", border: "1px solid var(--border)", borderRadius: 3, background: "#000" }}
      />
      {regions.map((r, i) => {
        if (!r) return null;
        const isSelected = selectedIndex === i;
        return (
          <div
            key={i}
            role={onSelect ? "button" : undefined}
            onClick={() => onSelect?.(i)}
            title={`Region ${i + 1}`}
            style={{
              position: "absolute",
              left: r.x * scaleX, top: r.y * scaleY, width: Math.max(4, r.w * scaleX), height: Math.max(4, r.h * scaleY),
              border: `2px solid ${isSelected ? "#e5484d" : "#3b82f6"}`,
              background: isSelected ? "rgba(229,72,77,0.18)" : "rgba(59,130,246,0.08)",
              cursor: onSelect ? "pointer" : "default",
              boxSizing: "border-box",
              transition: "border-color 0.15s, background 0.15s",
              pointerEvents: onSelect ? "auto" : "none",
            }}
          />
        );
      })}
    </div>
  );
}
