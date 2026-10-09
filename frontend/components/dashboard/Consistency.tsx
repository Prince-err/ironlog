"use client";

import { useMemo } from "react";
import type { HeatmapDay } from "@/lib/types";

const DOW_LABELS = ["M", "T", "W", "T", "F", "S", "S"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

type Level = 0 | 1 | 2 | 3 | 4;

function levelFor(workouts: number, max: number): Level {
  if (workouts <= 0) return 0;
  if (max <= 1) return 3;
  const ratio = workouts / max;
  if (ratio >= 0.75) return 4;
  if (ratio >= 0.5) return 3;
  return 2;
}

/**
 * Consistency card (spec §10): GitHub-style heatmap of completed workouts.
 * Weeks as columns, Mon–Sun rows, with weekday/month labels, a 4-level
 * intensity scale, a month ticker, per-period totals and a legend.
 */
export function Consistency({ days }: { days: HeatmapDay[] }) {
  const model = useMemo(() => {
    const real = days.filter((d) => d.date !== "");
    const counts = real.map((d) => d.workouts);
    const total = counts.reduce((a, b) => a + b, 0);
    const activeDays = counts.filter((n) => n > 0).length;
    const max = Math.max(...counts, 1);

    // Longest run of consecutive days with ≥1 workout (1 rest day tolerated).
    let longestRun = 0;
    let run = 0;
    let gap = 0;
    for (const n of counts) {
      if (n > 0) {
        run += gap + 1;
        gap = 0;
        longestRun = Math.max(longestRun, run);
      } else if (run > 0) {
        gap += 1;
        if (gap > 1) {
          run = 0;
          gap = 0;
        }
      }
    }

    // Per-weekday totals (Mon..Sun).
    const weekdayTotals = [0, 0, 0, 0, 0, 0, 0];
    for (const d of real) {
      const jsDow = new Date(`${d.date}T12:00:00`).getDay();
      const isoDow = jsDow === 0 ? 6 : jsDow - 1; // Mon=0
      weekdayTotals[isoDow] += d.workouts;
    }

    // Weeks as columns (Mon top). First column padded so rows align.
    const weeks: (HeatmapDay | null)[][] = [];
    let current: (HeatmapDay | null)[] = [];
    real.forEach((d, i) => {
      const jsDow = new Date(`${d.date}T12:00:00`).getDay();
      const isoDow = jsDow === 0 ? 6 : jsDow - 1;
      if (i === 0) {
        for (let j = 0; j < isoDow; j++) current.push(null);
      }
      current.push(d);
      if (current.length === 7) {
        weeks.push(current);
        current = [];
      }
    });
    if (current.length) {
      while (current.length < 7) current.push(null);
      weeks.push(current);
    }

    // Month ticker: one label per column where a new month starts.
    const monthTicks: { index: number; label: string }[] = [];
    let lastMonth = -1;
    weeks.forEach((week, wi) => {
      const first = week.find((c): c is HeatmapDay => c !== null);
      if (!first) return;
      const m = Number(first.date.slice(5, 7)) - 1;
      if (m !== lastMonth) {
        monthTicks.push({ index: wi, label: MONTHS[m] });
        lastMonth = m;
      }
    });

    return { weeks, monthTicks, total, activeDays, longestRun, weekdayTotals, max };
  }, [days]);

  const { weeks, monthTicks, total, activeDays, longestRun, weekdayTotals, max } = model;
  const bestDow = weekdayTotals.indexOf(Math.max(...weekdayTotals));
  const dayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

  return (
    <div>
      {/* headline stats */}
      <div className="mb-3 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-xl border border-border bg-surface-2/60 py-2">
          <div className="tabular text-lg font-bold text-accent">{total}</div>
          <div className="text-[10px] uppercase tracking-wider text-muted">workouts</div>
        </div>
        <div className="rounded-xl border border-border bg-surface-2/60 py-2">
          <div className="tabular text-lg font-bold">{activeDays}</div>
          <div className="text-[10px] uppercase tracking-wider text-muted">active days</div>
        </div>
        <div className="rounded-xl border border-border bg-surface-2/60 py-2">
          <div className="tabular text-lg font-bold">{longestRun}</div>
          <div className="text-[10px] uppercase tracking-wider text-muted">best run</div>
        </div>
      </div>

      {/* month ticker */}
      <div className="mb-1 flex gap-[3px] overflow-hidden pl-6">
        {weeks.map((_, wi) => {
          const tick = monthTicks.find((t) => t.index === wi);
          return (
            <div
              key={wi}
              className="w-3 shrink-0 text-[9px] font-medium text-muted"
              style={{ visibility: tick ? "visible" : "hidden" }}
            >
              {tick ? tick.label : "·"}
            </div>
          );
        })}
      </div>

      {/* grid: weekday labels + heat columns */}
      <div className="flex gap-[3px] overflow-x-auto pb-1">
        <div className="flex w-3 shrink-0 flex-col gap-[3px] pr-0.5 text-right">
          {DOW_LABELS.map((l, i) => (
            <div
              key={i}
              className={`flex h-3 items-center justify-center text-[9px] font-medium ${
                i === bestDow ? "text-accent" : "text-muted"
              }`}
            >
              {l}
            </div>
          ))}
        </div>
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-[3px]">
            {week.map((d, di) => {
              if (d === null) {
                return <div key={di} className="h-3 w-3 rounded-[3px] opacity-0" />;
              }
              const lvl = levelFor(d.workouts, max);
              return (
                <div
                  key={di}
                  title={
                    d.workouts > 0
                      ? `${d.date} · ${d.workouts} workout${d.workouts > 1 ? "s" : ""}`
                      : d.date
                  }
                  className={`h-3 w-3 rounded-[3px] transition-colors ${CELL_CLASSES[lvl]}`}
                />
              );
            })}
          </div>
        ))}
      </div>

      {/* weekday preference + legend */}
      <div className="mt-3 flex items-center justify-between">
        <p className="text-[11px] text-muted">
          Last 26 weeks · best day{" "}
          <span className="font-semibold text-foreground">{dayNames[bestDow]}</span>
        </p>
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-muted">less</span>
          {([0, 1, 2, 3, 4] as Level[]).map((lvl) => (
            <div key={lvl} className={`h-2.5 w-2.5 rounded-[3px] ${CELL_CLASSES[lvl]}`} />
          ))}
          <span className="text-[10px] text-muted">more</span>
        </div>
      </div>
    </div>
  );
}

const CELL_CLASSES: Record<Level, string> = {
  0: "bg-surface-2 border border-border/60",
  1: "bg-accent/25",
  2: "bg-accent/45",
  3: "bg-accent/70",
  4: "bg-accent",
};
