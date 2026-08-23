import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface Series {
  key: string;
  color: string;
  label: string;
}

export function MultiCurveChart({
  data, xKey, series, height = 260,
// eslint-disable-next-line @typescript-eslint/no-explicit-any
}: { data: any[]; xKey: string; series: Series[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
        <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: "var(--text-lo)" }} />
        <YAxis tick={{ fontSize: 10, fill: "var(--text-lo)" }} width={54} />
        <Tooltip contentStyle={{ background: "var(--bg-2)", border: "1px solid var(--border)", fontSize: 11 }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {series.map((s) => (
          <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} dot={{ r: 2 }} strokeWidth={1.75} isAnimationActive={false} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
