import { Metric, Panel } from "../../components/Common";
import { DualUploadLab, ImageGrid } from "../../components/CvLabShared";
import type { SiftResult } from "../../services/academicCvApi";
import { runSiftLab } from "../../services/academicCvApi";

export default function CvSiftLab() {
  return (
    <DualUploadLab<SiftResult>
      title="SIFT (Scale-Invariant Feature Transform) Lab"
      description="CS4231 Module 2 lab: 'Implement Feature extraction using SIFT.' Upload two related chart/report screenshots (e.g. the same chart at two different crops or resolutions) to detect keypoints in each and match them with Lowe's ratio test. Treasury use case: identifying a repeated chart template/layout or measuring visual similarity between two report screenshots -- NOT a market predictor."
      run={(a, b) => runSiftLab(a, b!, 0.75)}
    >
      {(result) => result && (
        <>
          <div className="grid grid-4" style={{ marginBottom: 12 }}>
            <Metric label="Keypoints (A)" value={String(result.result.n_keypoints_a)} />
            <Metric label="Keypoints (B)" value={String(result.result.n_keypoints_b)} />
            <Metric label="Raw matches (k=2 NN)" value={String(result.result.n_matches_raw)} />
            <Metric label="Good matches (ratio test)" value={String(result.result.n_good_matches)} />
          </div>
          <ImageGrid images={result.images} />
          <Panel title="Method">
            <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
              1) Detect scale-space extrema -&gt; keypoints with orientation. 2) Build a 128-D gradient-histogram descriptor per keypoint.
              3) Brute-force match descriptors between images (k=2 nearest neighbors). 4) Lowe's ratio test keeps a match only if the
              best match is meaningfully closer than the second-best (ratio &lt; {result.result.match_ratio_threshold}), rejecting ambiguous matches.
            </p>
          </Panel>
        </>
      )}
    </DualUploadLab>
  );
}
