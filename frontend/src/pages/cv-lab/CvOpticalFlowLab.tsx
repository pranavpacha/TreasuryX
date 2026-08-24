import { Badge, Metric } from "../../components/Common";
import { DualUploadLab, ImageGrid } from "../../components/CvLabShared";
import type { OpticalFlowResult } from "../../services/academicCvApi";
import { runOpticalFlowLab } from "../../services/academicCvApi";

export default function CvOpticalFlowLab() {
  return (
    <DualUploadLab<OpticalFlowResult>
      title="Optical Flow — Technical Evidence"
      description="CS4231 Module 2: 'Optical Flow.' Dense Farneback optical flow estimates a per-pixel motion field between two frames. Upload two snapshots of a moving/updating chart, or upload just one image -- a synthetically shifted second frame will be generated for demonstration."
      run={runOpticalFlowLab}
      secondOptional
    >
      {(result) => result && (
        <>
          {result.second_frame_synthetic && <Badge kind="warn">Second frame synthetically shifted (no second image uploaded)</Badge>}
          <div className="grid grid-2" style={{ margin: "12px 0" }}>
            <Metric label="Mean flow magnitude (px)" value={result.mean_magnitude.toFixed(2)} />
            <Metric label="Max flow magnitude (px)" value={result.max_magnitude.toFixed(2)} />
          </div>
          <ImageGrid images={result.images} labels={{ flow_field_color: "Flow field (HSV: hue=direction, value=speed)", vector_overlay: "Vector overlay on frame B" }} />
        </>
      )}
    </DualUploadLab>
  );
}
