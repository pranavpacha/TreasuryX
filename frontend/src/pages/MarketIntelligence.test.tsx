import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "../services/api";
import MarketIntelligence from "./MarketIntelligence";

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
};

describe("MarketIntelligence (CV) page", () => {
  it("uploads an image and displays pipeline stages and extracted fields", async () => {
    vi.spyOn(api, "post").mockResolvedValueOnce({ data: mockExtraction });
    render(<MarketIntelligence />);

    const file = new File(["fake-image-bytes"], "chart.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(screen.getByText(/Pipeline Stages/)).toBeInTheDocument());
    expect(screen.getByText("USD/INR")).toBeInTheDocument();
    expect(screen.getByDisplayValue("83.45")).toBeInTheDocument();
  });

  it("shows a low-confidence warning banner when the pipeline reports one", async () => {
    vi.spyOn(api, "post").mockResolvedValueOnce({
      data: { ...mockExtraction, warnings: ["Mean extraction confidence is low (<0.5) -- manual review strongly recommended."] },
    });
    render(<MarketIntelligence />);

    const file = new File(["fake-image-bytes"], "chart.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(screen.getByText(/manual review strongly recommended/)).toBeInTheDocument());
  });
});
