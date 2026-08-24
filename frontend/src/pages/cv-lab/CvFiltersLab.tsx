import { useState } from "react";
import { Panel } from "../../components/Common";
import { ImageGrid, SingleUploadLab } from "../../components/CvLabShared";
import { runFiltersLab } from "../../services/academicCvApi";
import type { LabImageResult } from "../../services/academicCvApi";

export default function CvFiltersLab() {
  const [kernel, setKernel] = useState(5);
  const [sigma, setSigma] = useState(1.5);

  return (
    <div>
      <SingleUploadLab<LabImageResult>
        title="Filter Comparison Lab"
        description="CS4231 Module 1: Spatial Domain Processing & Spatial Filtering. Compares Gaussian, median, bilateral, and CLAHE filtering on the same image so their trade-offs (noise removal vs. edge preservation vs. contrast) are visible side by side."
        run={(file) => runFiltersLab(file, kernel, sigma)}
        controls={(rerun) => (
          <>
            <label style={{ margin: 0 }}>Kernel<input type="number" style={{ width: 50 }} value={kernel} min={3} max={15} step={2} onChange={(e) => { setKernel(Number(e.target.value)); rerun(); }} /></label>
            <label style={{ margin: 0 }}>Sigma<input type="number" style={{ width: 50 }} value={sigma} min={0.5} max={5} step={0.5} onChange={(e) => { setSigma(Number(e.target.value)); rerun(); }} /></label>
          </>
        )}
      >
        {(result) => result && (
          <>
            <ImageGrid images={result.images} />
            <Panel title="What each filter does">
              <table className="data-table">
                <tbody>
                  {Object.entries((result.notes as Record<string, string>) ?? {}).map(([k, v]) => (
                    <tr key={k}><td style={{ textAlign: "left", textTransform: "capitalize" }}>{k}</td><td style={{ textAlign: "left" }}>{v}</td></tr>
                  ))}
                </tbody>
              </table>
            </Panel>
          </>
        )}
      </SingleUploadLab>
    </div>
  );
}
