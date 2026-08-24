import { useState } from "react";
import { ImageGrid, SingleUploadLab } from "../../components/CvLabShared";
import { runEdgesLab } from "../../services/academicCvApi";
import type { LabImageResult } from "../../services/academicCvApi";

export default function CvEdgesLab() {
  const [cannyLow, setCannyLow] = useState(50);
  const [cannyHigh, setCannyHigh] = useState(150);

  return (
    <SingleUploadLab<LabImageResult>
      title="Edge Detection — Technical Evidence"
      description="CS4231 Module 2 lab: 'Implement Edge detection using DoG, LoG, Canny and Hough Transform.' Shows Sobel X/Y, gradient magnitude, Laplacian, Difference-of-Gaussians (DoG), Laplacian-of-Gaussian (LoG), and Canny with adjustable thresholds. (Hough line detection is demonstrated on the Market Intelligence page's region-detection stage.)"
      run={(file) => runEdgesLab(file, cannyLow, cannyHigh, 1.0, 2.0)}
      controls={(rerun) => (
        <>
          <label style={{ margin: 0 }}>Canny low
            <input type="range" min={0} max={255} value={cannyLow} onChange={(e) => { setCannyLow(Number(e.target.value)); rerun(); }} />
            {cannyLow}
          </label>
          <label style={{ margin: 0 }}>Canny high
            <input type="range" min={0} max={255} value={cannyHigh} onChange={(e) => { setCannyHigh(Number(e.target.value)); rerun(); }} />
            {cannyHigh}
          </label>
        </>
      )}
    >
      {(result) => result && <ImageGrid images={result.images} />}
    </SingleUploadLab>
  );
}
