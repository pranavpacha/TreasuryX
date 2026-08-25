import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { api } from "../services/api";
import MarketIntelligence from "./MarketIntelligence";

function renderPage() {
  return render(<MemoryRouter><MarketIntelligence /></MemoryRouter>);
}

const mockExtraction = {
  id: 1,
  original_filename: "chart.png",
  chart_type: "fx_chart",
  stages: { original: "data:image/png;base64,AAA" },
  ocr_text_raw: "USD/INR 83.45",
  ocr_available: true,
  fields: [
    { instrument: "USD/INR", metric: "spot", value: 83.45, unit: "INR per unit", confidence: 0.91, source_region: [1, 2, 3, 4] },
  ],
  mean_confidence: 0.91,
  warnings: [],
  model_details: { available: false, reason: "Live model inference requires torch, a dev-only dependency not installed in this deployment." },
};

const mockExtractionWithModels = {
  ...mockExtraction,
  model_details: {
    available: true,
    classes: ["fx_line_chart", "yield_curve_chart", "bar_chart", "table_report"],
    cnn: { label: "fx_line_chart", confidence: 0.87, inference_ms: 1.2 },
    vit: { label: "fx_line_chart", confidence: 0.73, inference_ms: 2.4 },
    agree: true,
    note: "Both models were trained from scratch on a small synthetic 4-class chart dataset.",
  },
};

function uploadChart() {
  const file = new File(["fake-image-bytes"], "chart.png", { type: "image/png" });
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  fireEvent.change(input, { target: { files: [file] } });
}

describe("Financial Image Intelligence page", () => {
  it("uploads an image and displays extracted fields, with pipeline stages hidden by default", async () => {
    vi.spyOn(api, "post").mockResolvedValueOnce({ data: mockExtraction });
    renderPage();

    uploadChart();

    await waitFor(() => expect(screen.getByText("USD/INR")).toBeInTheDocument());
    expect(screen.getByDisplayValue("83.45")).toBeInTheDocument();
    // Stage images are behind the "Processing Details" disclosure, not shown by default
    expect(screen.queryByText(/1\. Original/)).not.toBeInTheDocument();
    expect(screen.getByText("Processing Details")).toBeInTheDocument();
  });

  it("shows a low-confidence warning banner when the pipeline reports one", async () => {
    vi.spyOn(api, "post").mockResolvedValueOnce({
      data: { ...mockExtraction, warnings: ["Mean extraction confidence is low (<0.5) -- manual review strongly recommended."] },
    });
    renderPage();

    uploadChart();

    await waitFor(() => expect(screen.getByText(/manual review strongly recommended/)).toBeInTheDocument());
  });

  it("reveals pipeline stages when 'Show' is clicked", async () => {
    vi.spyOn(api, "post").mockResolvedValueOnce({ data: mockExtraction });
    renderPage();
    uploadChart();
    await waitFor(() => expect(screen.getByText("USD/INR")).toBeInTheDocument());

    fireEvent.click(screen.getAllByText("Show")[0]);
    expect(screen.getByText(/1\. Original/)).toBeInTheDocument();
  });

  it("shows a graceful unavailable message for Model Details when torch/weights aren't present", async () => {
    vi.spyOn(api, "post").mockResolvedValueOnce({ data: mockExtraction });
    renderPage();
    uploadChart();
    await waitFor(() => expect(screen.getByText("USD/INR")).toBeInTheDocument());

    fireEvent.click(screen.getAllByText("Show")[1]);
    expect(screen.getByText(/Live model inference requires torch/)).toBeInTheDocument();
  });

  it("shows live CNN vs. ViT predictions in Model Details when available", async () => {
    vi.spyOn(api, "post").mockResolvedValueOnce({ data: mockExtractionWithModels });
    renderPage();
    uploadChart();
    await waitFor(() => expect(screen.getByText("USD/INR")).toBeInTheDocument());

    fireEvent.click(screen.getAllByText("Show")[1]);
    expect(screen.getByText("Models agree")).toBeInTheDocument();
    expect(screen.getAllByText("fx_line_chart").length).toBeGreaterThan(0);
  });

  it("saves the corrected value BEFORE committing, then applies it and shows the portfolio update", async () => {
    const postSpy = vi.spyOn(api, "post");
    postSpy.mockResolvedValueOnce({ data: mockExtraction }); // /cv/extract
    postSpy.mockResolvedValueOnce({ data: { id: 1, status: "corrected" } }); // /cv/correct
    postSpy.mockResolvedValueOnce({
      data: {
        instrument_id: "USDINR", field: "spot rate", previous_value: 83.2, new_value: 90.0, delta: 6.8,
        affected_open_positions: [{ pair: "USDINR", pnl_inr: 12345 }],
      },
    }); // /cv/commit

    renderPage();
    uploadChart();
    await waitFor(() => expect(screen.getByText("USD/INR")).toBeInTheDocument());

    // Edit the value before applying -- this must be persisted via /cv/correct first
    const input = screen.getByDisplayValue("83.45");
    fireEvent.change(input, { target: { value: "90" } });

    fireEvent.click(screen.getByText("Apply to Treasury"));

    await waitFor(() => expect(screen.getByText("Portfolio updated")).toBeInTheDocument());

    // Verify /cv/correct was called with the edited value before /cv/commit
    expect(postSpy).toHaveBeenCalledWith("/cv/correct", expect.objectContaining({
      extraction_id: 1,
      corrected_fields: [expect.objectContaining({ value: 90 })],
    }));
    expect(postSpy).toHaveBeenCalledWith("/cv/commit", expect.objectContaining({ extraction_id: 1, target: "fx" }));
    expect(screen.getByText(/1 open position\(s\) repriced/)).toBeInTheDocument();
  });

  it("shows the 'How Detected?' technical trace for a field", async () => {
    vi.spyOn(api, "post").mockResolvedValueOnce({ data: mockExtraction });
    renderPage();
    uploadChart();
    await waitFor(() => expect(screen.getByText("USD/INR")).toBeInTheDocument());

    fireEvent.click(screen.getByText("How Detected?"));
    expect(screen.getByText(/Trace:/)).toBeInTheDocument();
  });
});
