import { useState } from "react";
import { Badge, ErrorState, Panel } from "./Common";
import type { ProposalItem, VisionProposal } from "../services/visionApi";
import { approveProposal, createProposals, listProposals, rejectProposal } from "../services/visionApi";

/**
 * Shared "stage -> analyst review -> approve/reject" panel used by every CV feature that reads a
 * market value (Chart Digitization, Screenshot Comparison). Staging never changes Treasury state;
 * only an explicit Approve click does, through the same commit path as Financial Image
 * Intelligence (see backend/app/services/commit.py). A flagged value needs a second confirmation.
 */
export function ProposalReview({ source, candidates, sourceRef }: { source: string; candidates: ProposalItem[]; sourceRef?: string }) {
  const [staged, setStaged] = useState<VisionProposal[]>([]);
  const [skipped, setSkipped] = useState<{ instrument_id: string; value: number; reason: string }[]>([]);
  const [staging, setStaging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [confirmFlag, setConfirmFlag] = useState<number | null>(null);

  const stageAll = async () => {
    setStaging(true);
    setError(null);
    try {
      const r = await createProposals(source, candidates, sourceRef);
      setStaged(r.created);
      setSkipped(r.skipped);
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Failed to stage proposals");
    } finally {
      setStaging(false);
    }
  };

  const refresh = async () => setStaged((await listProposals()).filter((p) => staged.some((s) => s.id === p.id)));

  const approve = async (id: number, confirmFlagged: boolean) => {
    setBusyId(id);
    setError(null);
    try {
      await approveProposal(id, { confirm_flagged: confirmFlagged });
      setConfirmFlag(null);
      await refresh();
    } catch (e) {
      const err = e as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = err.response?.data?.detail;
      if (detail && typeof detail === "object" && (detail as { code?: string }).code === "confirmation_required") {
        setConfirmFlag(id);
      } else {
        setError(typeof detail === "string" ? detail : err.message ?? "Approval failed");
      }
    } finally {
      setBusyId(null);
    }
  };

  const reject = async (id: number) => {
    setBusyId(id);
    try {
      await rejectProposal(id);
      await refresh();
    } finally {
      setBusyId(null);
    }
  };

  if (candidates.length === 0) return null;

  return (
    <Panel title="Apply to Treasury (requires approval)">
      <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>
        {candidates.length} value{candidates.length !== 1 ? "s" : ""} read from this image. Staging creates nothing in Treasury yet —
        it only queues a proposal for review. A value is only ever applied after you click Approve.
      </p>
      {staged.length === 0 ? (
        <button className="primary" onClick={stageAll} disabled={staging}>{staging ? "Staging…" : `Stage ${candidates.length} value(s) for review`}</button>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Instrument</th><th>Previous</th><th>Proposed</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {staged.map((p) => (
              <tr key={p.id}>
                <td style={{ textAlign: "left" }}>{p.instrument_id}{p.resolved_isin && p.resolved_isin !== p.instrument_id ? ` (${p.resolved_isin})` : ""}</td>
                <td>{p.previous_value ?? "—"}</td>
                <td>{p.proposed_value}{p.unit === "pct" ? "%" : ""}</td>
                <td>
                  {p.status === "pending" && <Badge kind="warn">PENDING</Badge>}
                  {p.status === "approved" && <Badge kind="info">APPROVED</Badge>}
                  {p.status === "rejected" && <Badge>REJECTED</Badge>}
                </td>
                <td>
                  {p.status === "pending" && (
                    confirmFlag === p.id ? (
                      <span style={{ display: "flex", gap: 4, justifyContent: "flex-end" }}>
                        <span style={{ fontSize: 10, color: "var(--warn)" }}>{p.validation.warnings[0]}</span>
                        <button onClick={() => approve(p.id, true)} disabled={busyId === p.id}>Confirm anyway</button>
                        <button onClick={() => setConfirmFlag(null)}>Cancel</button>
                      </span>
                    ) : (
                      <span style={{ display: "flex", gap: 4, justifyContent: "flex-end" }}>
                        <button className="primary" onClick={() => approve(p.id, false)} disabled={busyId === p.id}>Approve</button>
                        <button onClick={() => reject(p.id)} disabled={busyId === p.id}>Reject</button>
                      </span>
                    )
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {skipped.length > 0 && (
        <p style={{ fontSize: 10.5, color: "var(--text-lo)", marginTop: 8 }}>
          {skipped.length} value(s) could not be staged: {skipped.map((s) => `${s.instrument_id} (${s.reason})`).join("; ")}
        </p>
      )}
      {error && <ErrorState message={error} />}
    </Panel>
  );
}
