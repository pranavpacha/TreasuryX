import { Metric, Panel } from "../../components/Common";
import { DualUploadLab, ImageGrid } from "../../components/CvLabShared";
import type { SiftResult } from "../../services/academicCvApi";
import { runSiftLab } from "../../services/academicCvApi";

export default function CompareMarketScreens() {
  return (
    <div>
      <Panel title="Compare Market Screens">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          Upload two Treasury/market screenshots — e.g. today's and yesterday's rates screen, two
          brokers' quote sheets, or a report before/after revision — to find matching visual regions
          and flag where they differ. Useful for spotting a changed number on an otherwise identical
          layout, or confirming two report exports came from the same template. This is a real
          product capability, not a benchmark: it uses SIFT (Scale-Invariant Feature Transform)
          keypoint matching under the hood — see <em>Methodology → Computer Vision</em> for the algorithm.
        </p>
      </Panel>
      <DualUploadLab<SiftResult>
        title="Upload Two Screens"
        description="Both images are analyzed for keypoints, matched with Lowe's ratio test, and the confident matches are visualized."
        run={(a, b) => runSiftLab(a, b!, 0.75)}
      >
        {(result) => result && (
          <>
            <div className="grid grid-4" style={{ marginBottom: 12 }}>
              <Metric label="Keypoints (Screen A)" value={String(result.result.n_keypoints_a)} />
              <Metric label="Keypoints (Screen B)" value={String(result.result.n_keypoints_b)} />
              <Metric label="Confident matches" value={String(result.result.n_good_matches)} />
              <Metric label="Similarity" value={`${result.result.similarity_pct}%`} />
            </div>
            <ImageGrid images={result.images} labels={{ keypoints_a: "Screen A keypoints", keypoints_b: "Screen B keypoints", matches: "Matched regions" }} />
            <Panel title="How this works">
              <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
                Each image is reduced to scale-invariant keypoints with 128-dimension descriptors. Descriptors are
                matched between the two screens (k=2 nearest neighbors) and Lowe's ratio test discards ambiguous
                matches — a match is kept only if the best candidate is meaningfully closer than the second-best
                (ratio &lt; {result.result.match_ratio_threshold}). Similarity is confident matches as a percentage
                of the smaller image's keypoint count: a high value suggests the two screens share substantial
                visual structure (same layout/template); a low value suggests they're materially different
                documents.
              </p>
            </Panel>
          </>
        )}
      </DualUploadLab>
    </div>
  );
}
