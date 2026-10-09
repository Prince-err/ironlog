"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { DashboardData, HeatmapDay } from "@/lib/types";
import { fetchDashboard, fetchHeatmap } from "@/lib/api";
import { Consistency } from "@/components/dashboard/Consistency";
import {
  Badge,
  Card,
  ErrorState,
  ProgressBar,
  SectionTitle,
  Skeleton,
  Stat,
} from "@/components/ui/primitives";

/** Home screen (spec §9 / §22). */
export function DashboardView() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapDay[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // async but always resolves after paint — safe to set state here
    (async () => {
      await Promise.resolve();
      if (cancelled) return;
      try {
        const [d, h] = await Promise.all([fetchDashboard(), fetchHeatmap(182)]);
        if (cancelled) return;
        setData(d);
        setHeatmap(h);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!data) {
    return (
      <div className="space-y-3 pt-2">
        <Skeleton className="h-20" />
        <Skeleton className="h-28" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  const streak = data.streak;

  return (
    <div className="space-y-3 pt-2">
      {/* header */}
      <div className="flex items-end justify-between">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent">
            {data.greeting}
          </div>
          <h1 className="text-2xl font-bold">Iron Log</h1>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold">🔥 {streak.current_streak}</div>
          <div className="text-[11px] text-muted">
            day streak{streak.longest_streak > streak.current_streak
              ? ` · best ${streak.longest_streak}`
              : ""}
          </div>
        </div>
      </div>

      {/* today's workout */}
      {data.todays_workout ? (
        <Card className="animate-fade-up border-accent/40">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <Badge tone="accent">Today</Badge>
              <div className="mt-1.5 font-bold">{data.todays_workout.name ?? "Workout"}</div>
              <div className="mb-2 text-xs text-muted">
                {data.todays_workout.progress_exercises_done} /{" "}
                {data.todays_workout.progress_exercises_total} exercises done
              </div>
              <ProgressBar
                value={data.todays_workout.progress_exercises_done}
                max={data.todays_workout.progress_exercises_total}
              />
            </div>
            <Link
              href={`/workout/${data.todays_workout.session_id}`}
              className="shrink-0 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-foreground"
            >
              Resume
            </Link>
          </div>
        </Card>
      ) : (
        <Card className="animate-fade-up">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold">No workout yet today</div>
              <div className="text-xs text-muted">
                Keep the 🔥 {streak.current_streak}-day streak alive.
              </div>
            </div>
            <Link
              href="/workout"
              className="shrink-0 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-foreground"
            >
              Start
            </Link>
          </div>
        </Card>
      )}

      {/* quick stats */}
      <Stat label="This week" value={`${data.weekly_sessions} sessions`} accent />

      {/* daily mission */}
      {data.mission ? (
        <>
          <SectionTitle>Daily mission</SectionTitle>
          <Card className="animate-fade-up">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm font-semibold">{data.mission.description}</div>
                <div className="mb-2 mt-1.5 text-xs text-muted">
                  {Math.min(data.mission.progress, data.mission.target)} /{" "}
                  {data.mission.target}
                </div>
                <ProgressBar value={data.mission.progress} max={data.mission.target} />
              </div>
              {data.mission.completed ? <Badge tone="success">DONE</Badge> : null}
            </div>
          </Card>
        </>
      ) : null}

      {/* next overload target */}
      {data.next_target ? (
        <>
          <SectionTitle>Next target</SectionTitle>
          <Card className="animate-fade-up border-accent/25">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <Link
                  href={`/exercises/${data.next_target.exercise_id}`}
                  className="text-sm font-bold hover:text-accent"
                >
                  {data.next_target.exercise}
                </Link>
                <div className="mt-0.5 text-xs text-muted">
                  {data.next_target.headline}
                </div>
              </div>
              <Badge tone="accent">
                {data.next_target.weight != null
                  ? `${data.next_target.weight} kg`
                  : data.next_target.added_weight != null
                    ? `+${data.next_target.added_weight} kg`
                    : data.next_target.reps != null
                      ? `${data.next_target.reps} reps`
                      : ""}
              </Badge>
            </div>
          </Card>
        </>
      ) : null}

      {/* recent PRs */}
      {data.recent_prs.length > 0 ? (
        <>
          <SectionTitle
            action={
              <Link href="/history/prs" className="text-xs text-accent">
                All PRs
              </Link>
            }
          >
            Recent PRs
          </SectionTitle>
          <div className="space-y-2">
            {data.recent_prs.slice(0, 3).map((pr, i) => (
              <Card key={i} className="flex items-center justify-between py-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold">{pr.exercise}</div>
                  <div className="text-[11px] text-muted">
                    {pr.category.replace(/_/g, " ")}
                  </div>
                </div>
                <div className="tabular shrink-0 text-sm font-bold text-accent">
                  {pr.weight != null
                    ? `${pr.weight} kg${pr.reps ? ` × ${pr.reps}` : ""}`
                    : pr.duration != null
                      ? `${pr.duration}s`
                      : pr.added_weight != null
                        ? `+${pr.added_weight} kg`
                        : ""}
                </div>
              </Card>
            ))}
          </div>
        </>
      ) : null}

      {/* consistency */}
      <SectionTitle>Consistency</SectionTitle>
      <Card>
        <Consistency days={heatmap} />
        <p className="mt-2 text-[11px] text-muted">
          Rest days don&apos;t break your streak (one rest day is tolerated).
        </p>
      </Card>

      {/* smart recommendations */}
      {data.recommendations.length > 0 ? (
        <>
          <SectionTitle>Insights</SectionTitle>
          <div className="space-y-2">
            {data.recommendations.map((rec, i) => (
              <Card key={i} className="py-3 text-sm text-foreground/90">
                {rec}
              </Card>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
