import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface SnapshotPoint {
  label: string;
  value: number;
}

/**
 * Renders extracted financial points (real CV-extracted values, in the order the pipeline
 * found them -- never a fabricated/assumed ordering) as a small interactive chart, with
 * clickable points kept in sync with the source image's highlighted region and the
 * extracted-fields table (shared selectedIndex state in the parent page).
 */
export function MarketSnapshotChart({
  points, selectedIndex, onSelect, mode, valueLabel,
}: {
  points: SnapshotPoint[];
  selectedIndex?: number | null;
  onSelect?: (idx: number) => void;
  mode: "curve" | "points";
  valueLabel: string;
}) {
  if (points.length === 0) {
    return <div className="empty-state">No extracted points to reconstruct.</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
        <XAxis dataKey="label" tick={{ fontSize: 10, fill: "var(--text-lo)" }} />
        <YAxis tick={{ fontSize: 10, fill: "var(--text-lo)" }} width={54} domain={["auto", "auto"]} />
        <Tooltip
          contentStyle={{ background: "var(--bg-2)", border: "1px solid var(--border)", fontSize: 11 }}
          formatter={(v: number) => [v, valueLabel]}
        />
        <Line
          type="monotone" dataKey="value" stroke="var(--accent)" strokeWidth={mode === "curve" ? 1.75 : 0}
          isAnimationActive={false}
          dot={(dotProps: { cx?: number; cy?: number; index?: number }) => {
            const { cx, cy, index } = dotProps;
            const isSel = index === selectedIndex;
            return (
              <circle
                key={`snapshot-dot-${index}`} cx={cx} cy={cy} r={isSel ? 6 : 4}
                fill={isSel ? "#e5484d" : "var(--accent)"} stroke="#05070a" strokeWidth={1}
                style={{ cursor: onSelect ? "pointer" : "default" }}
                onClick={() => index != null && onSelect?.(index)}
              />
            );
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
