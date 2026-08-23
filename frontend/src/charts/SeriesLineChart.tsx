import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function SeriesLineChart({
  data, xKey, yKey, color = "var(--accent)", height = 220, yDomain,
}: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[];
  xKey: string;
  yKey: string;
  color?: string;
  height?: number;
  yDomain?: [number | string, number | string];
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
        <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: "var(--text-lo)" }} minTickGap={40} />
        <YAxis tick={{ fontSize: 10, fill: "var(--text-lo)" }} domain={yDomain ?? ["auto", "auto"]} width={54} />
        <Tooltip
          contentStyle={{ background: "var(--bg-2)", border: "1px solid var(--border)", fontSize: 11 }}
          labelStyle={{ color: "var(--text-mid)" }}
        />
        <Line type="monotone" dataKey={yKey} stroke={color} dot={false} strokeWidth={1.5} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
