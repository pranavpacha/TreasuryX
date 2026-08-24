import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

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
  { to: "/intelligence/compare-screens", label: "Compare Market Screens" },
];

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
      <div style={{ padding: "10px 16px 4px", fontSize: 9.5, fontWeight: 700, letterSpacing: 0.6, color: "var(--text-lo)", textTransform: "uppercase" }}>{title}</div>
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
          {item.label}
        </NavLink>
      ))}
    </div>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const now = new Date();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="logo">
          TREASURY<span>X</span>
        </div>
        <span className="demo-badge">DEMO / SIMULATED DATA</span>
        <div style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-mid)" }} className="mono">
          {now.toLocaleDateString("en-IN")} · Asia/Kolkata
        </div>
      </header>
      <nav className="app-nav">
        <NavSection title="Workstation" items={WORKSTATION_NAV} />
        <NavSection title="Intelligence" items={INTELLIGENCE_NAV} />
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
