import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "../services/api";
import Overview from "./Overview";

const mockOverview = {
  as_of: "2026-08-21",
  fx_snapshot: [{ pair: "USDINR", rate: 83.5 }],
  curve_snapshot: [{ tenor: "10Y", yield_pct: 7.1 }],
  selected_bond: { isin: "IN001", name: "GS 7.10% 2029", current_yield_pct: 7.02 },
  risk: {
    as_of: "2026-08-21", fx_exposure_inr: 100000, fx_pnl_inr: 5000, bond_market_value_inr: 200000,
    bond_dv01_inr_per_bp: 100, total_pnl_inr: 5000, portfolio_value_inr: 300000,
    var: { var_amount_inr: 1000, es_amount_inr: 1500, confidence: 0.95, horizon_days: 1, lookback_obs: 250, method: "historical" },
    var_warning: null, max_drawdown_inr: -2000, regime: "NORMAL", regime_reasons: ["No threshold breached"],
    risk_limits: { fx_exposure_limit_inr: 1000000, fx_exposure_utilization_pct: 10, bond_dv01_limit_inr: 200000, bond_dv01_utilization_pct: 5 },
  },
  market_events: [{ headline: "Test event", category: "FX", severity: "INFO", created_at: "2026-08-21T00:00:00Z" }],
  is_demo: true,
  disclaimer: "Educational/simulated Treasury analytics platform. No real-money trading.",
};

describe("Overview page", () => {
  it("renders the disclaimer, FX snapshot and risk metrics after loading", async () => {
    vi.spyOn(api, "get").mockResolvedValueOnce({ data: mockOverview });
    render(<Overview />);

    expect(screen.getByText(/Loading Treasury overview/i)).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText(/No real-money trading/i)).toBeInTheDocument());
    expect(screen.getByText("USDINR")).toBeInTheDocument();
    expect(screen.getByText("83.5000")).toBeInTheDocument();
    expect(screen.getByText("NORMAL")).toBeInTheDocument();
  });

  it("shows an error state when the API call fails", async () => {
    vi.spyOn(api, "get").mockRejectedValueOnce(new Error("Network error"));
    render(<Overview />);
    await waitFor(() => expect(screen.getByText(/Error: Network error/i)).toBeInTheDocument());
  });
});
