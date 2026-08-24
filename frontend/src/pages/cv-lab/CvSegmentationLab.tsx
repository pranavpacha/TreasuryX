import { Metric, Panel } from "../../components/Common";
import { useApi } from "../../hooks/useApi";
import { fetchSegmentationBenchmark, runSegmentationLab } from "../../services/academicCvApi";
import type { LabImageResult } from "../../services/academicCvApi";
import { ImageGrid, SingleUploadLab } from "../../components/CvLabShared";

type SegmentationUploadResult = LabImageResult & { init_rect: number[] };

export default function CvSegmentationLab() {
  const benchmark = useApi(fetchSegmentationBenchmark);

  return (
    <div>
      <Panel title="Segmentation Benchmark (synthetic ground truth)">
        <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>
          The syllabus's U-Net/medical-imaging segmentation lab is out of scope for this build (wrong domain, no
          such labeled dataset for financial charts -- see the Course Mapping page). Instead, this is a real,
          working classical segmentation pipeline (GrabCut) for the in-scope task -- isolating the chart panel from
          a screenshot -- validated with genuine IoU/Dice against a synthetic dataset where the ground-truth region
          is known by construction.
        </p>
        {benchmark.data && (
          <div className="grid grid-4">
            <Metric label="Samples" value={String(benchmark.data.n_samples)} />
            <Metric label="Mean IoU" value={benchmark.data.mean_iou.toFixed(3)} />
            <Metric label="Mean Dice" value={benchmark.data.mean_dice.toFixed(3)} />
            <Metric label="Min IoU" value={benchmark.data.min_iou.toFixed(3)} />
          </div>
        )}
      </Panel>

      <SingleUploadLab<SegmentationUploadResult>
        title="Try Segmentation on Your Own Image"
        description="GrabCut foreground/background segmentation, initialized with a margin-based rectangle guess."
        run={runSegmentationLab}
      >
        {(result) => result && <ImageGrid images={result.images} />}
      </SingleUploadLab>
    </div>
  );
}
