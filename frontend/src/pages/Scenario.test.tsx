import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "../services/api";
import Scenario from "./Scenario";

const mockResult = {
  id: 1,
  label: "USD/INR +2%",
  inputs: { fx_shock_pct: { USDINR: 0.02 }, parallel_yield_shock_bps: 0, curve_tilt_bps: 0 },
  fx_pnl_by_pair: { USDINR: 1_000_000 },
  bond_pnl_by_isin: {},
  total_fx_pnl: 1_000_000,
  total_bond_pnl: 0,
  total_pnl: 1_000_000,
  shocked_fx_rates: { USDINR: 85.17 },
  shocked_bond_yields: {},
  method_notes: ["FX P&L = (shocked_rate - current_rate) * notional_base"],
};

describe("Scenario page", () => {
  it("submits a preset scenario and displays the audited result", async () => {
    const postSpy = vi.spyOn(api, "post").mockResolvedValueOnce({ data: mockResult });
    render(<Scenario />);

    fireEvent.click(screen.getByText("USD/INR +2%"));

    await waitFor(() => expect(screen.getByText(/SCN-00001/)).toBeInTheDocument());
    expect(postSpy).toHaveBeenCalledWith("/scenario/run", expect.objectContaining({
      label: "USD/INR +2%", fx_shock_pct: { USDINR: 0.02 },
    }));
    expect(screen.getByText(/FX P&L = \(shocked_rate/)).toBeInTheDocument();
  });

  it("runs a custom scenario with user-entered shocks", async () => {
    const postSpy = vi.spyOn(api, "post").mockResolvedValueOnce({ data: { ...mockResult, label: "Custom scenario" } });
    render(<Scenario />);

    const [, parallelInput] = screen.getAllByRole("spinbutton");
    fireEvent.change(parallelInput, { target: { value: "25" } });
    fireEvent.click(screen.getByText("Run Custom Scenario"));

    await waitFor(() => expect(postSpy).toHaveBeenCalled());
    expect(postSpy).toHaveBeenCalledWith("/scenario/run", expect.objectContaining({ parallel_yield_shock_bps: 25 }));
  });
});
