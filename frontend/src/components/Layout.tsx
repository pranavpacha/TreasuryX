import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Overview" },
  { to: "/fx", label: "FX Desk" },
  { to: "/rates", label: "Rates & Bonds" },
  { to: "/yield-curve", label: "Yield Curve" },
  { to: "/risk", label: "Risk" },
  { to: "/scenario", label: "Scenario / Stress" },
  { to: "/blotter", label: "Trade Blotter" },
  { to: "/vision", label: "Market Intelligence (CV)" },
  { to: "/3d", label: "3D Market" },
];

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
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="app-main">{children}</main>
      <footer className="app-footer">
        <span>Educational/simulated Treasury analytics platform. No real-money trading. Outputs are for academic and demonstration purposes only.</span>
        <span>TreasuryX v0.1</span>
      </footer>
    </div>
  );
}
