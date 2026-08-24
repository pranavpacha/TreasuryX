import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useMode } from "../context/ModeContext";

const TERMINAL_NAV = [
  { to: "/", label: "Overview" },
  { to: "/fx", label: "FX Desk" },
  { to: "/rates", label: "Rates & Bonds" },
  { to: "/yield-curve", label: "Yield Curve" },
  { to: "/risk", label: "Portfolio Risk" },
  { to: "/scenario", label: "Stress Testing" },
  { to: "/blotter", label: "Trade Blotter" },
];

const MARKET_INTEL_NAV = [{ to: "/vision", label: "Financial Image Intelligence" }];
const MARKET_3D_NAV = [{ to: "/3d", label: "3D Market" }];

const CV_LAB_NAV = [
  { to: "/academic/cv", label: "CV Lab Home" },
  { to: "/academic/cv/filters", label: "Filters" },
  { to: "/academic/cv/edges", label: "Edges" },
  { to: "/academic/cv/features", label: "Corners & Blobs" },
  { to: "/academic/cv/sift", label: "SIFT" },
  { to: "/academic/cv/segmentation", label: "Segmentation" },
  { to: "/academic/cv/optical-flow", label: "Optical Flow" },
  { to: "/academic/cv/models", label: "CNN vs ViT" },
  { to: "/academic/cv/object-detection", label: "Object Detection" },
];

const GRAPHICS_LAB_NAV = [
  { to: "/academic/graphics", label: "Graphics Lab Home" },
  { to: "/academic/graphics/raster", label: "Raster Graphics" },
  { to: "/academic/graphics/transform2d", label: "2D Transform & Clip" },
  { to: "/academic/graphics/3d", label: "3D Transform & Shader" },
  { to: "/academic/graphics/depth", label: "Depth Buffer" },
  { to: "/academic/graphics/vr-ar", label: "VR/AR Concepts" },
];

const DOCS_NAV = [
  { to: "/academic/course-mapping", label: "Course Mapping" },
  { to: "/academic/methodology", label: "Methodology" },
  { to: "/academic/limitations", label: "Limitations & Future Work" },
  { to: "/academic/demo-guide", label: "Demo Guide" },
];

function NavSection({ title, items }: { title: string; items: { to: string; label: string }[] }) {
  return (
    <div>
      <div style={{ padding: "10px 16px 4px", fontSize: 9.5, fontWeight: 700, letterSpacing: 0.6, color: "var(--text-lo)", textTransform: "uppercase" }}>{title}</div>
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} end={item.to === "/" || item.to === "/academic/cv" || item.to === "/academic/graphics"} className={({ isActive }) => (isActive ? "active" : "")}>
          {item.label}
        </NavLink>
      ))}
    </div>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const now = new Date();
  const { mode, setMode } = useMode();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="logo">
          TREASURY<span>X</span>
        </div>
        <span className="demo-badge">DEMO / SIMULATED DATA</span>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: 4, overflow: "hidden" }}>
            <button
              onClick={() => setMode("terminal")}
              style={{ border: "none", borderRadius: 0, background: mode === "terminal" ? "var(--accent)" : "var(--bg-2)", color: mode === "terminal" ? "white" : "var(--text-mid)", fontWeight: mode === "terminal" ? 700 : 400 }}
            >
              TERMINAL
            </button>
            <button
              onClick={() => setMode("academic")}
              style={{ border: "none", borderRadius: 0, background: mode === "academic" ? "var(--accent)" : "var(--bg-2)", color: mode === "academic" ? "white" : "var(--text-mid)", fontWeight: mode === "academic" ? 700 : 400 }}
            >
              ACADEMIC
            </button>
          </div>
          <div style={{ fontSize: 11, color: "var(--text-mid)" }} className="mono">
            {now.toLocaleDateString("en-IN")} · Asia/Kolkata
          </div>
        </div>
      </header>
      <nav className="app-nav">
        <NavSection title="Terminal" items={TERMINAL_NAV} />
        <NavSection title="Market Intelligence" items={MARKET_INTEL_NAV} />
        <NavSection title="3D Markets" items={MARKET_3D_NAV} />
        {mode === "academic" && (
          <>
            <NavSection title="Computer Vision Lab" items={CV_LAB_NAV} />
            <NavSection title="Computer Graphics Lab" items={GRAPHICS_LAB_NAV} />
            <NavSection title="Academic & Documentation" items={DOCS_NAV} />
          </>
        )}
      </nav>
      <main className="app-main">{children}</main>
      <footer className="app-footer">
        <span>Educational/simulated Treasury analytics platform. No real-money trading. Outputs are for academic and demonstration purposes only.</span>
        <span>TreasuryX v0.2 · {mode === "academic" ? "Academic Mode" : "Terminal Mode"}</span>
      </footer>
    </div>
  );
}
