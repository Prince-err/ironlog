"use client";

import { useMemo, useState } from "react";

export interface ChartPoint {
  date: string;
  value: number;
  label?: string;
}

/**
 * Minimal dependency-free SVG line chart with hover interaction.
 * Rendered responsively via viewBox; hover uses nearest-point detection.
 */
export function LineChart({
  points,
  color = "var(--accent)",
  formatValue,
  formatTooltip,
  height = 180,
}: {
  points: ChartPoint[];
  color?: string;
  formatValue?: (v: number) => string;
  formatTooltip?: (p: ChartPoint) => string;
  height?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 600;
  const H = height;
  const PAD_L = 8;
  const PAD_R = 8;
  const PAD_T = 14;
  const PAD_B = 22;

  const fmt = formatValue ?? ((v: number) => String(Math.round(v * 100) / 100));

  const { path, areaPath, coords, min, max } = useMemo(() => {
    if (points.length === 0)
      return { path: "", areaPath: "", coords: [], min: 0, max: 1 };
    const values = points.map((p) => p.value);
    let lo = Math.min(...values);
    let hi = Math.max(...values);
    if (lo === hi) {
      lo = lo - 1;
      hi = hi + 1;
    }
    const span = hi - lo;
    const n = points.length;
    const coords = points.map((p, i) => {
      const x =
        PAD_L +
        (n === 1 ? (W - PAD_L - PAD_R) / 2 : (i / (n - 1)) * (W - PAD_L - PAD_R));
      const y = PAD_T + (1 - (p.value - lo) / span) * (H - PAD_T - PAD_B);
      return { x, y, ...p };
    });
    const path = coords
      .map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
      .join(" ");
    const areaPath =
      n > 1
        ? `${path} L${coords[coords.length - 1].x.toFixed(1)},${H - PAD_B} L${coords[0].x.toFixed(1)},${H - PAD_B} Z`
        : "";
    return { path, areaPath, coords, min: lo, max: hi };
  }, [points, H]);

  if (points.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted">
        No data yet
      </div>
    );
  }

  const hoverPoint = hover != null ? coords[hover] : null;

  function onMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = ((e.clientX - rect.left) / rect.width) * W;
    let best = 0;
    let bestDist = Infinity;
    coords.forEach((c, i) => {
      const d = Math.abs(c.x - relX);
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    });
    setHover(best);
  }

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full touch-none"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label="progress chart"
      >
        {areaPath ? (
          <path d={areaPath} fill={color} opacity={0.08} />
        ) : null}
        <path
          d={path}
          fill="none"
          stroke={color}
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {coords.map((c, i) => (
          <circle
            key={i}
            cx={c.x}
            cy={c.y}
            r={hover === i ? 5 : 2.5}
            fill={hover === i ? color : "var(--surface)"}
            stroke={color}
            strokeWidth={hover === i ? 2 : 1.5}
          />
        ))}
        {/* x-axis first / last labels */}
        <text x={PAD_L} y={H - 6} fontSize={11} fill="var(--muted)">
          {shortDate(points[0].date)}
        </text>
        <text
          x={W - PAD_R}
          y={H - 6}
          fontSize={11}
          fill="var(--muted)"
          textAnchor="end"
        >
          {shortDate(points[points.length - 1].date)}
        </text>
        {/* max/min gridline labels */}
        <text x={PAD_L} y={PAD_T - 2} fontSize={10} fill="var(--muted)">
          {fmt(max)}
        </text>
      </svg>
      {hoverPoint ? (
        <div
          className="pointer-events-none absolute left-1/2 top-0 z-10 -translate-x-1/2 animate-pop rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs shadow-lg"
          style={{ width: "max-content", maxWidth: "90%" }}
        >
          <div className="font-semibold">{shortDate(hoverPoint.date)}</div>
          <div className="text-muted">
            {formatTooltip
              ? formatTooltip(hoverPoint)
              : `${fmt(hoverPoint.value)}`}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function shortDate(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function BarChart({
  points,
  formatValue,
  height = 160,
}: {
  points: ChartPoint[];
  formatValue?: (v: number) => string;
  height?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const fmt = formatValue ?? ((v: number) => String(Math.round(v)));
  if (points.length === 0)
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted">
        No data yet
      </div>
    );
  const max = Math.max(...points.map((p) => p.value), 1);
  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {points.map((p, i) => (
        <button
          key={p.date}
          type="button"
          className="group relative flex-1 self-stretch pt-4"
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(null)}
          aria-label={`${p.date}: ${fmt(p.value)}`}
        >
          <div
            className="w-full rounded-t-md bg-accent/70 transition-all group-hover:bg-accent"
            style={{ height: `${Math.max(3, (p.value / max) * (height - 28))}px` }}
          />
          {hover === i ? (
            <div className="pointer-events-none absolute -top-1 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-lg border border-border bg-surface-2 px-2 py-1 text-[11px]">
              {shortDate(p.date)}: {fmt(p.value)}
            </div>
          ) : null}
        </button>
      ))}
    </div>
  );
}
