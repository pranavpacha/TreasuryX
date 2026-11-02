import { useEffect, useState } from "react";
import { Badge, ErrorState, LoadingState, Metric, Panel } from "../../components/Common";
import { DualUploadLab } from "../../components/CvLabShared";
import type { IndexItem, SimilarityResult } from "../../services/visionApi";
import { addToIndex, compareSimilarity, deleteIndexItem, listIndex, searchIndex, seedSyntheticIndex } from "../../services/visionApi";

const VERDICT_TONE: Record<string, "info" | "warn" | "sim"> = { near_duplicate: "warn", same_template: "info", similar_layout: "info", different: "sim" };

function PairwiseCompare() {
  return (
    <DualUploadLab<SimilarityResult> title="Compare Two Screenshots" description="A Siamese network (contrastive loss, trained on synthetic layouts) scores embedding similarity; SIFT/SSIM confirm it before calling anything a near-duplicate." run={(a, b) => compareSimilarity(a, b!)}>
      {(result) => result && (
        <>
          <div className="grid grid-4" style={{ marginBottom: 12 }}>
            <Metric label="Cosine Similarity" value={result.cosine_similarity.toFixed(4)} />
            <Metric label="SSIM" value={result.ssim !== null ? result.ssim.toFixed(4) : "—"} />
            <Metric label="Verdict" value={result.verdict.label.replace(/_/g, " ")} />
            <Metric label="SIFT Inliers" value={String(result.sift.inliers)} />
          </div>
          <Badge kind={VERDICT_TONE[result.verdict.label] ?? "info"}>{result.verdict.text}</Badge>
          {result.matched_regions_image && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4 }}>Matched regions (SIFT)</div>
              <img src={result.matched_regions_image} alt="matches" style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3, background: "#000" }} />
            </div>
          )}
          <p style={{ fontSize: 11, color: "var(--text-mid)", marginTop: 10 }}>{result.caveat}</p>
        </>
      )}
    </DualUploadLab>
  );
}

function IndexSearch() {
  const [items, setItems] = useState<IndexItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<(IndexItem & { similarity: number; verdict: string })[] | null>(null);
  const [searching, setSearching] = useState(false);

  const refresh = () => listIndex().then((d) => setItems(d.items)).finally(() => setLoading(false));
  useEffect(() => { refresh(); }, []);

  const onSearch = async (f: File | null) => {
    if (!f) return;
    setSearching(true);
    setError(null);
    try {
      const r = await searchIndex(f);
      setResults(r.results);
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Search failed");
    } finally {
      setSearching(false);
    }
  };

  return (
    <>
      <Panel title="Screenshot Index" right={<button onClick={() => seedSyntheticIndex().then(refresh)}>Seed with synthetic examples</button>}>
        <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
          Every screenshot uploaded to Financial Image Intelligence is automatically embedded and added here
          (layout only — the image itself isn't re-stored beyond a small thumbnail). Upload or search to find
          previously seen reports with a similar layout.
        </p>
        <div style={{ display: "flex", gap: 10, alignItems: "center", margin: "8px 0" }}>
          <input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={(e) => { const f = e.target.files?.[0]; if (f) addToIndex(f).then(refresh); }} />
          <span style={{ fontSize: 11, color: "var(--text-mid)" }}>add to index</span>
        </div>
        {loading ? <LoadingState /> : items.length === 0 ? <div className="empty-state">Index is empty.</div> : (
          <div className="grid grid-5">
            {items.map((it) => (
              <div key={it.id} style={{ position: "relative" }}>
                <img src={it.thumbnail} alt={it.filename} style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3 }} />
                <div style={{ fontSize: 9.5, color: "var(--text-mid)", marginTop: 2 }}>{it.filename}</div>
                {it.kind_guess && <div style={{ fontSize: 9, color: "var(--text-lo)" }}>{it.kind_guess}</div>}
                <button style={{ position: "absolute", top: 2, right: 2, fontSize: 9, padding: "1px 5px" }} onClick={() => deleteIndexItem(it.id).then(refresh)}>×</button>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <Panel title="Search by Image">
        <input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={(e) => onSearch(e.target.files?.[0] ?? null)} disabled={searching} />
        {searching && <LoadingState label="Searching…" />}
        {error && <ErrorState message={error} />}
        {results && (
          results.length === 0 ? <div className="empty-state">Index is empty — nothing to compare against.</div> : (
            <table className="data-table" style={{ marginTop: 8 }}>
              <thead><tr><th>File</th><th>Similarity</th><th>Verdict</th></tr></thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.id}><td style={{ textAlign: "left" }}>{r.filename}</td><td>{r.similarity.toFixed(4)}</td><td style={{ textAlign: "left" }}>{r.verdict.replace(/_/g, " ")}</td></tr>
                ))}
              </tbody>
            </table>
          )
        )}
      </Panel>
    </>
  );
}

export default function SimilaritySearch() {
  return (
    <div>
      <Panel title="Similarity Search (Siamese Network)">
        <p style={{ fontSize: 12, color: "var(--text-mid)" }}>
          A Siamese network — two identical encoder branches sharing weights, trained with a
          contrastive loss so same-template screenshots land close together in embedding space and
          different ones land far apart — compares document and chart layouts. This is layout/template
          similarity, not face recognition, and not a market signal.
        </p>
      </Panel>
      <PairwiseCompare />
      <IndexSearch />
    </div>
  );
}
