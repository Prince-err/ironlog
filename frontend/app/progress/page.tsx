"use client";

import { useEffect, useState } from "react";
import type {
  AnalyticsSummary,
  MuscleVolume,
} from "@/lib/types";
import {
  fetchAnalyticsSummary,
  fetchMuscleVolumes,
  fetchRecommendations,
} from "@/lib/api";
import { formatVolume } from "@/lib/format";
import {
  Card,
  ErrorState,
  SectionTitle,
  Skeleton,
  Stat,
} from "@/components/ui/primitives";

const RANGES = [
  { key: "7d", label: "Week" },
  { key: "30d", label: "Month" },
  { key: "3m", label: "3 Months" },
  { key: "6m", label: "6 Months" },
  { key: "1y", label: "Year" },
  { key: "all", label: "All Time" },
];

type Tab = "overview" | "muscles";

export default function ProgressPage() {
  const [range, setRange] = useState("30d");
  const [tab, setTab] = useState<Tab>("overview");
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [muscles, setMuscles] = useState<MuscleVolume[] | null>(null);
  const [recs, setRecs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await Promise.resolve(); // let the effect settle before setState
      if (cancelled) return;
      setSummary(null);
      setMuscles(null);
      try {
        const [s, m, r] = await Promise.all([
          fetchAnalyticsSummary(range),
          fetchMuscleVolumes(range),
          fetchRecommendations().catch(() => ({ recommendations: [] })),
        ]);
        if (cancelled) return;
        setSummary(s);
        setMuscles(m);
        setRecs(r.recommendations);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load analytics");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [range]);

  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-3 pt-2">
      <h1 className="text-2xl font-bold">Progress</h1>

      {/* range switcher */}
      <div className="flex flex-wrap gap-1.5">
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

      <div className="grid grid-cols-2 gap-2">
        <TabButton active={tab === "overview"} onClick={() => setTab("overview")}>
          Strength & Volume
        </TabButton>
        <TabButton active={tab === "muscles"} onClick={() => setTab("muscles")}>
          Muscle Groups
        </TabButton>
      </div>

      {!summary ? <Skeleton className="h-64" /> : tab === "overview" ? (
        <>
          <div className="grid grid-cols-2 gap-2">
            <Stat label="Total volume" value={formatVolume(summary.total_volume)} accent />
            <Stat label="Sessions" value={summary.sessions} />
            <Stat label="Total sets" value={summary.total_sets} />
            <Stat label="Total reps" value={summary.total_reps} />
          </div>

          <SectionTitle>Average session</SectionTitle>
          <Card className="py-3">
            <div className="tabular text-2xl font-bold">
              {summary.avg_session_minutes} min
            </div>
          </Card>

          {recs.length > 0 ? (
            <>
              <SectionTitle>Insights</SectionTitle>
              <div className="space-y-2">
                {recs.map((r, i) => (
                  <Card key={i} className="py-3 text-sm">
                    {r}
                  </Card>
                ))}
              </div>
            </>
          ) : null}
        </>
      ) : (
        <>
          <SectionTitle>Volume by muscle group</SectionTitle>
          {!muscles ? (
            <Skeleton className="h-48" />
          ) : (
            <div className="space-y-2">
              {muscles.map((m) => (
                <Card key={m.muscle_group} className="py-3">
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="font-semibold">{m.muscle_group}</span>
                    <span className="tabular text-muted">
                      {formatVolume(m.volume)} · {m.share}%
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${m.share}%` }}
                    />
                  </div>
                </Card>
              ))}
              {muscles.length === 0 ? (
                <Card className="py-6 text-center text-sm text-muted">
                  No training volume in this range.
                </Card>
              ) : null}
              <p className="px-1 text-[11px] text-muted">
                Volume is weight × reps — a useful training-load indicator, not a
                direct measure of muscle growth.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-xl border px-3 py-2 text-xs font-semibold transition ${
        active
          ? "border-accent/60 text-accent"
          : "border-border text-muted hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}
