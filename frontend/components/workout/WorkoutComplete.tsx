"use client";

import Link from "next/link";
import type { CompleteSummary } from "@/lib/types";
import { formatDuration, formatPRValue, formatVolume } from "@/lib/format";
import { Button, Card, SectionTitle, Stat } from "@/components/ui/primitives";

/** Post-workout summary (spec §15): WORKOUT COMPLETE + achievements. */
export function WorkoutComplete({
  summary,
  sessionName,
}: {
  summary: CompleteSummary;
  sessionName: string | null;
}) {
  const delta = summary.volume_delta;
  const deltaLabel =
    delta === 0
      ? "same as last time"
      : `${delta > 0 ? "+" : ""}${formatVolume(Math.abs(delta))} ${
          delta > 0 ? "vs last time" : "vs last time"
        }`;

  return (
    <div className="animate-fade-up space-y-4">
      <div className="pt-6 text-center">
        <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent">
          Workout complete
        </div>
        <h1 className="mt-1 text-2xl font-bold">
          {sessionName ?? "Session"} done. 💪
        </h1>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Stat label="Duration" value={formatDuration(summary.duration_minutes)} />
        <Stat label="Volume" value={formatVolume(summary.volume)} accent />
        <Stat label="Exercises" value={summary.exercises} />
        <Stat label="Sets" value={summary.sets} />
      </div>

      <Card>
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted">Previous volume</span>
          <span className="tabular font-semibold">
            {formatVolume(summary.previous_volume)}
          </span>
        </div>
        <div className="mt-1.5 flex items-center justify-between text-sm">
          <span className="text-muted">Difference</span>
          <span
            className={`tabular font-semibold ${
              delta > 0 ? "text-success" : delta < 0 ? "text-danger" : ""
            }`}
          >
            {delta > 0 ? "+" : ""}
            {formatVolume(delta)}
          </span>
        </div>
        <div className="mt-1.5 flex items-center justify-between text-sm">
          <span className="text-muted">Streak</span>
          <span className="font-semibold">
            🔥 {summary.streak.current_streak} days
          </span>
        </div>
        <div className="mt-1.5 flex items-center justify-between text-sm">
          <span className="text-muted">Mission</span>
          <span className="font-semibold text-success">COMPLETED</span>
        </div>
        <p className="mt-2 text-[11px] text-muted">{deltaLabel}</p>
      </Card>

      {summary.new_prs.length > 0 ? (
        <>
          <SectionTitle>
            New PRs ({summary.pr_count})
          </SectionTitle>
          <div className="space-y-2">
            {summary.new_prs.slice(0, 6).map((pr, i) => (
              <Card key={i} className="animate-pop border-accent/30 bg-accent/5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-accent">
                      NEW PR
                    </div>
                    <div className="text-sm font-bold">{pr.exercise}</div>
                  </div>
                  <div className="tabular text-sm font-bold">
                    {formatPRValue(pr)}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </>
      ) : null}

      <div className="grid grid-cols-2 gap-2 pt-2">
        <Link href="/history" className="contents">
          <Button variant="secondary" full>
            View history
          </Button>
        </Link>
        <Link href="/" className="contents">
          <Button full>Back home</Button>
        </Link>
      </div>
    </div>
  );
}
