"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import type { ExerciseHistoryData } from "@/lib/types";
import { fetchExerciseHistory } from "@/lib/api";
import {
  formatPRValue,
  formatSetCompact,
  PR_CATEGORY_LABELS,
  relativeDay,
  trim,
} from "@/lib/format";
import { LineChart, type ChartPoint } from "@/components/charts/LineChart";
import {
  Badge,
  Card,
  ErrorState,
  SectionTitle,
  Skeleton,
  Stat,
} from "@/components/ui/primitives";

type GraphKey = "weight" | "reps" | "volume" | "e1rm" | "sets";

const GRAPHS: { key: GraphKey; label: string }[] = [
  { key: "weight", label: "Weight" },
  { key: "reps", label: "Reps" },
  { key: "volume", label: "Volume" },
  { key: "e1rm", label: "Est. 1RM" },
  { key: "sets", label: "Sets" },
];

const RANGES = [
  { key: "30d", label: "30d" },
  { key: "3m", label: "3M" },
  { key: "6m", label: "6M" },
  { key: "1y", label: "1Y" },
  { key: "all", label: "All" },
];

export default function ExerciseDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [data, setData] = useState<ExerciseHistoryData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [graph, setGraph] = useState<GraphKey>("weight");
  const [range, setRange] = useState("all");

  useEffect(() => {
    fetchExerciseHistory(Number(id), range)
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load")
      );
  }, [id, range]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Skeleton className="mt-4 h-72" />;

  const ex = data.exercise;

  const points: ChartPoint[] = data.series
    .map((s) => ({
      date: s.date,
      value:
        graph === "weight"
          ? (s.top_weight ?? 0)
          : graph === "reps"
            ? (s.top_reps ?? 0)
            : graph === "volume"
              ? s.volume
              : graph === "e1rm"
                ? (s.estimated_1rm ?? 0)
                : s.sets,
    }))
    .filter((p) => p.value > 0);

  const valueLabel = (v: number) =>
    graph === "weight" || graph === "e1rm"
      ? `${trim(v)} kg`
      : graph === "volume"
        ? `${trim(v)} kg`
        : String(Math.round(v));

  return (
    <div className="space-y-3 pt-2">
      {/* header */}
      <div>
        <div className="flex items-center gap-2 text-[11px] text-muted">
          <Link href="/history" className="hover:text-foreground">
            ← Exercises
          </Link>
        </div>
        <h1 className="mt-1 text-2xl font-bold">{ex.name}</h1>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <Badge tone="accent">{ex.primary_muscle ?? "—"}</Badge>
          <Badge>{ex.exercise_type.replace(/_/g, " ")}</Badge>
          {ex.secondary_muscles.map((m) => (
            <Badge key={m}>{m}</Badge>
          ))}
        </div>
      </div>

      {ex.form_description ? (
        <Card>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
            Form
          </div>
          <p className="mt-1 text-sm">{ex.form_description}</p>
          {ex.technique_tips ? (
            <p className="mt-2 text-xs text-muted">💡 {ex.technique_tips}</p>
          ) : null}
        </Card>
      ) : null}

      {/* bests */}
      <div className="grid grid-cols-2 gap-2">
        <Stat
          label="Current best"
          value={
            data.bests.heaviest_weight != null
              ? `${trim(data.bests.heaviest_weight)} kg`
              : data.bests.longest_duration != null
                ? `${trim(data.bests.longest_duration)}s`
                : data.bests.most_reps != null
                  ? `${data.bests.most_reps} reps`
                  : "—"
          }
          accent
        />
        <Stat
          label="Best est. 1RM"
          value={
            data.bests.best_estimated_1rm != null
              ? `~${trim(data.bests.best_estimated_1rm)} kg`
              : "—"
          }
          sub="calculated (Epley), not measured"
        />
        <Stat
          label="Best session volume"
          value={
            data.bests.best_volume_session != null
              ? `${trim(data.bests.best_volume_session)} kg`
              : "—"
          }
        />
        <Stat
          label="Sessions"
          value={data.totals.sessions}
          sub={`${data.totals.sets} sets total`}
        />
      </div>

      {/* overload recommendation */}
      {data.recommendation ? (
        <Card className="border-accent/25 bg-accent/5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-accent">
            Suggested next session
          </div>
          <div className="mt-1 text-sm font-semibold">
            {data.recommendation.headline}
          </div>
          <div className="mt-0.5 text-xs text-muted">
            {data.recommendation.detail}
          </div>
        </Card>
      ) : null}

      {/* PRs */}
      {data.prs.length > 0 ? (
        <>
          <SectionTitle>Personal records</SectionTitle>
          <div className="grid grid-cols-2 gap-2">
            {data.prs.map((pr) => (
              <Card key={pr.category} className="py-3">
                <div className="text-[11px] text-muted">
                  {PR_CATEGORY_LABELS[pr.category] ?? pr.category}
                </div>
                <div className="tabular mt-0.5 text-sm font-bold">
                  {formatPRValue(pr)}
                </div>
              </Card>
            ))}
          </div>
        </>
      ) : null}

      {/* graphs */}
      <SectionTitle>Progress</SectionTitle>
      <Card>
        <div className="mb-3 flex flex-wrap gap-1.5">
          {GRAPHS.map((g) => (
            <button
              key={g.key}
              onClick={() => setGraph(g.key)}
              className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${
                graph === g.key
                  ? "border-accent/60 text-accent"
                  : "border-border text-muted hover:text-foreground"
              }`}
            >
              {g.label}
            </button>
          ))}
        </div>
        <LineChart
          points={points}
          formatValue={valueLabel}
          formatTooltip={(p) =>
            `${valueLabel(p.value)}${
              graph === "e1rm" ? " (estimated)" : ""
            }`
          }
        />
        {graph === "e1rm" ? (
          <p className="mt-1 text-[11px] text-muted">
            Estimated 1RM (Epley formula) — a calculation, not a measured max.
          </p>
        ) : null}
        <div className="mt-3 flex gap-1.5">
          {RANGES.map((r) => (
            <button
              key={r.key}
              onClick={() => setRange(r.key)}
              className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${
                range === r.key
                  ? "border-accent/60 text-accent"
                  : "border-border text-muted hover:text-foreground"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </Card>

      {/* history */}
      <SectionTitle>History</SectionTitle>
      <div className="space-y-2">
        {data.sessions.map((sess) => (
          <Card key={sess.date}>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
              {relativeDay(sess.date)}
            </div>
            <div className="tabular mt-1.5 space-y-1">
              {sess.sets.map((s, i) => (
                <div key={i} className="flex justify-between text-sm">
                  <span className="text-muted">Set {i + 1}</span>
                  <span className="font-semibold">{formatSetCompact(s)}</span>
                </div>
              ))}
            </div>
          </Card>
        ))}
        {data.sessions.length === 0 ? (
          <Card className="py-6 text-center text-sm text-muted">
            No history in this range.
          </Card>
        ) : null}
      </div>
    </div>
  );
}
