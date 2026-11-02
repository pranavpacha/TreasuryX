import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

const WORKSTATION_NAV = [
  { to: "/", label: "Overview" },
  { to: "/fx", label: "FX Desk" },
  { to: "/rates", label: "Rates & Bonds" },
  { to: "/yield-curve", label: "Yield Curve" },
  { to: "/risk", label: "Portfolio Risk" },
  { to: "/scenario", label: "Stress Testing" },
  { to: "/blotter", label: "Trade Blotter" },
];

const INTELLIGENCE_NAV = [
  { to: "/intelligence/financial-image", label: "Financial Image Intelligence" },
  { to: "/intelligence/chart-digitization", label: "Chart Digitization" },
  { to: "/intelligence/compare-screens", label: "Compare Market Screens" },
  { to: "/intelligence/anomaly-detection", label: "Visual Anomaly Detection" },
  { to: "/intelligence/video", label: "Video Intelligence" },
  { to: "/intelligence/image-quality", label: "Image Quality Analyzer" },
  { to: "/intelligence/optical-flow", label: "Optical Flow" },
  { to: "/intelligence/similarity-search", label: "Similarity Search" },
  { to: "/intelligence/zero-shot-search", label: "Zero-Shot Search" },
];

const VISION_MODELS_NAV = [{ to: "/vision-models/cnn-vs-vit", label: "CNN vs. ViT" }];

const VISUALIZATION_NAV = [{ to: "/visualization/3d-market", label: "3D Market" }];

const METHODOLOGY_NAV = [
  { to: "/methodology/treasury", label: "Treasury Methodology" },
  { to: "/methodology/computer-vision", label: "Computer Vision Methodology" },
  { to: "/methodology/computer-graphics", label: "Computer Graphics Methodology" },
  { to: "/methodology/course-mapping", label: "Course Mapping" },
  { to: "/methodology/technical-evidence", label: "Technical Evidence" },
];

function NavSection({ title, items }: { title: string; items: { to: string; label: string }[] }) {
  return (
    <div>
      <div className="nav-section-title">{title}</div>
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
          {item.label}
        </NavLink>
      ))}
    </div>
  );
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const now = new Date();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);

  // Close the mobile nav drawer automatically whenever the route changes, so picking a
  // page doesn't leave the overlay sitting on top of the new content.
  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <button
          className="nav-toggle"
          type="button"
          aria-label={navOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={navOpen}
          onClick={() => setNavOpen((v) => !v)}
        >
          <MenuIcon />
        </button>
        <div className="logo">
          TREASURY<span>X</span>
        </div>
        <span className="demo-badge">DEMO / SIMULATED DATA</span>
        <div style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-mid)" }} className="mono">
          {now.toLocaleDateString("en-IN")} · Asia/Kolkata
        </div>
      </header>
      <div className={`nav-scrim ${navOpen ? "open" : ""}`} onClick={() => setNavOpen(false)} aria-hidden="true" />
      <nav className={`app-nav ${navOpen ? "open" : ""}`} aria-label="Primary">
        <NavSection title="Workstation" items={WORKSTATION_NAV} />
        <NavSection title="Intelligence" items={INTELLIGENCE_NAV} />
        <NavSection title="Vision Models" items={VISION_MODELS_NAV} />
        <NavSection title="Visualization" items={VISUALIZATION_NAV} />
        <NavSection title="Methodology" items={METHODOLOGY_NAV} />
      </nav>
      <main className="app-main">{children}</main>
      <footer className="app-footer">
        <span>Educational/simulated Treasury analytics platform. No real-money trading. Outputs are for academic and demonstration purposes only.</span>
        <span>TreasuryX v0.3</span>
      </footer>
    </div>
  );
}
