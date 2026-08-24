import type { ReactNode } from "react";
import { useState } from "react";
import { ErrorState, LoadingState, Panel } from "./Common";

export function ImageGrid({ images, labels }: { images: Record<string, string>; labels?: Record<string, string> }) {
  return (
    <div className="grid grid-4">
      {Object.entries(images).map(([key, src]) => (
        <div key={key}>
          <div style={{ fontSize: 10.5, color: "var(--text-mid)", marginBottom: 4, textTransform: "capitalize" }}>
            {labels?.[key] ?? key.replace(/_/g, " ")}
          </div>
          <img src={src} alt={key} style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 3, background: "#000" }} />
        </div>
      ))}
    </div>
  );
}

interface SingleUploadLabProps<T> {
  title: string;
  description: string;
  run: (file: File) => Promise<T>;
  children: (result: T | null, loading: boolean) => ReactNode;
  controls?: (rerun: () => void) => ReactNode;
}

export function SingleUploadLab<T>({ title, description, run, children, controls }: SingleUploadLabProps<T>) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = async (f: File | null = file) => {
    if (!f) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await run(f));
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel title={title}>
      <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>{description}</p>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10 }}>
        <input
          type="file" accept=".png,.jpg,.jpeg,.webp"
          onChange={(e) => { const f = e.target.files?.[0] ?? null; setFile(f); if (f) execute(f); }}
        />
        {controls && controls(() => execute())}
      </div>
      {loading && <LoadingState label="Processing…" />}
      {error && <ErrorState message={error} />}
      {children(result, loading)}
    </Panel>
  );
}

interface DualUploadLabProps<T> {
  title: string;
  description: string;
  run: (fileA: File, fileB: File | null) => Promise<T>;
  children: (result: T | null, loading: boolean) => ReactNode;
  secondOptional?: boolean;
}

export function DualUploadLab<T>({ title, description, run, children, secondOptional }: DualUploadLabProps<T>) {
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [result, setResult] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = async () => {
    if (!fileA) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await run(fileA, fileB));
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail ?? err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel title={title}>
      <p style={{ fontSize: 11, color: "var(--text-mid)", marginBottom: 8 }}>{description}</p>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
        <div>
          <label>Image A</label>
          <input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={(e) => setFileA(e.target.files?.[0] ?? null)} />
        </div>
        <div>
          <label>Image B {secondOptional && "(optional)"}</label>
          <input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={(e) => setFileB(e.target.files?.[0] ?? null)} />
        </div>
        <button className="primary" disabled={!fileA} onClick={execute}>Run</button>
      </div>
      {loading && <LoadingState label="Processing…" />}
      {error && <ErrorState message={error} />}
      {children(result, loading)}
    </Panel>
  );
}
