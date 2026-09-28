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
  image_quality: { width: 300, height: 200, blur_variance: 250.0, contrast_std: 60.0, verdict: "ok" as const, reasons: [], recommendation: null },
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

const mockYieldCurveExtraction = {
  ...mockExtraction,
  chart_type: "yield_curve",
  stages: { original: "data:image/png;base64,YIELD" },
  fields: [
    { instrument: "2Y", metric: "yield", value: 6.82, unit: "pct", confidence: 0.9, source_region: [10, 10, 20, 10] },
    { instrument: "5Y", metric: "yield", value: 6.95, unit: "pct", confidence: 0.88, source_region: [40, 20, 20, 10] },
    { instrument: "10Y", metric: "yield", value: 7.12, unit: "pct", confidence: 0.93, source_region: [70, 30, 20, 10] },
  ],
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

  it("shows an image quality warning banner when the pipeline flags low quality", async () => {
    vi.spyOn(api, "post").mockResolvedValueOnce({
      data: {
        ...mockExtraction,
        image_quality: {
          width: 80, height: 60, blur_variance: 12.0, contrast_std: 8.0, verdict: "low" as const,
          reasons: ["Low resolution (80x60px, smaller side under 200px)."],
          recommendation: "Upload a higher-resolution, well-lit, in-focus screenshot for more reliable extraction.",
        },
      },
    });
    renderPage();
    uploadChart();

    await waitFor(() => expect(screen.getByText("IMAGE QUALITY: LOW")).toBeInTheDocument());
    expect(screen.getByText(/Low resolution/)).toBeInTheDocument();
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

  describe("Market Snapshot", () => {
    it("reconstructs exactly the extracted points -- no fabricated values", async () => {
      vi.spyOn(api, "post").mockResolvedValueOnce({ data: mockYieldCurveExtraction });
      renderPage();
      uploadChart();
      await waitFor(() => expect(screen.getByText("Market Snapshot")).toBeInTheDocument());

      // Extraction summary reflects the real pipeline output, not an invented count
      expect(screen.getByText("Extracted Market Structure")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument(); // Points extracted -- matches mock field count exactly
      expect(screen.getByText("yield_curve")).toBeInTheDocument(); // Detected chart type
      expect(screen.getByText("Reconstructed Market View")).toBeInTheDocument();
    });

    it("shows nothing to reconstruct (not a fabricated chart) when no numeric values were extracted", async () => {
      vi.spyOn(api, "post").mockResolvedValueOnce({
        data: { ...mockExtraction, fields: [{ instrument: null, metric: "unlabeled_value", value: null, unit: "unitless", confidence: 0.2, source_region: null }] },
      });
      renderPage();
      uploadChart();
      await waitFor(() => expect(screen.getByText("Market Snapshot")).toBeInTheDocument());

      expect(screen.getByText(/nothing to reconstruct/)).toBeInTheDocument();
    });

    it("clicking an extracted field row selects it and surfaces its real value in the Selected Point panel", async () => {
      vi.spyOn(api, "post").mockResolvedValueOnce({ data: mockYieldCurveExtraction });
      renderPage();
      uploadChart();
      await waitFor(() => expect(screen.getByText("10Y")).toBeInTheDocument());

      // Click the 10Y row in the extracted-fields table
      fireEvent.click(screen.getByText("10Y"));

      await waitFor(() => expect(screen.getByText("Selected Point")).toBeInTheDocument());
      // The panel must show the ACTUAL extracted value (7.12), not a placeholder/fabricated one
      expect(screen.getByText("7.12pct")).toBeInTheDocument();
    });
  });
});
