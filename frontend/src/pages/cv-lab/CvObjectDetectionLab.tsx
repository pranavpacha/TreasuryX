import { Badge, ErrorState, LoadingState, Panel } from "../../components/Common";
import { useApi } from "../../hooks/useApi";
import type { ObjectDetectionStatus } from "../../services/academicCvApi";
import { fetchObjectDetectionStatus } from "../../services/academicCvApi";

export default function CvObjectDetectionLab() {
  const { data, loading, error } = useApi<ObjectDetectionStatus>(fetchObjectDetectionStatus);

  return (
    <Panel title="Deep Object Detection (Fast R-CNN / FPN / RetinaNet / YOLO)">
      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {data && (
        <>
          <div style={{ marginBottom: 12 }}><Badge kind="warn">{data.status}</Badge></div>
          <p style={{ fontSize: 12, marginBottom: 12 }}>{data.reason}</p>

          <div className="panel-title">What is implemented instead</div>
          <p style={{ fontSize: 12, color: "var(--text-mid)", marginBottom: 12 }}>{data.what_is_implemented_instead}</p>

          <div className="panel-title">Reproducible pipeline, if undertaken</div>
          <table className="data-table">
            <tbody>
              <tr><td style={{ textAlign: "left" }}>Dataset schema</td><td style={{ textAlign: "left" }} className="mono">{JSON.stringify(data.reproducible_pipeline_if_undertaken.dataset_schema, null, 1)}</td></tr>
              <tr><td style={{ textAlign: "left" }}>Training config</td><td style={{ textAlign: "left" }} className="mono">{JSON.stringify(data.reproducible_pipeline_if_undertaken.training_config, null, 1)}</td></tr>
              <tr><td style={{ textAlign: "left" }}>Inference script</td><td style={{ textAlign: "left" }}>{data.reproducible_pipeline_if_undertaken.inference_script}</td></tr>
            </tbody>
          </table>
        </>
      )}
    </Panel>
  );
}
