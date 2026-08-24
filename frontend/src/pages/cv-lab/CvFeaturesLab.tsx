import { Metric, Panel } from "../../components/Common";
import { ImageGrid, SingleUploadLab } from "../../components/CvLabShared";
import { runFeaturesLab } from "../../services/academicCvApi";
import type { LabImageResult } from "../../services/academicCvApi";

export default function CvFeaturesLab() {
  return (
    <SingleUploadLab<LabImageResult>
      title="Corner & Blob Detection — Technical Evidence"
      description="CS4231 Module 2: 'Blobs, Corner Detection; Scale Space and Scale Selection.' Harris corner detection locates axis/gridline intersections; blob detection locates marker/legend-swatch-like regions on a financial chart."
      run={runFeaturesLab}
    >
      {(result) => result && (
        <>
          <div className="grid grid-2" style={{ marginBottom: 12 }}>
            <Metric label="Harris corners found" value={String(result.n_corners)} />
            <Metric label="Blobs found" value={String(result.n_blobs)} />
          </div>
          <ImageGrid images={result.images} />
          <Panel title="Method notes">
            <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
              Harris corner response = det(M) - k·trace(M)² from the local structure tensor M; points above a threshold are marked as corners.
              Blob detection groups connected dark regions by area (SimpleBlobDetector) to find marker-like shapes.
            </p>
          </Panel>
        </>
      )}
    </SingleUploadLab>
  );
}
