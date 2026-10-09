"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import type { SessionSummary } from "@/lib/types";
import { fetchSession } from "@/lib/api";
import { formatSetCompact, formatVolume } from "@/lib/format";
import {
  Card,
  ErrorState,
  SectionTitle,
  Skeleton,
  Stat,
} from "@/components/ui/primitives";

export default function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [session, setSession] = useState<SessionSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSession(Number(id))
      .then(setSession)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load session")
      );
  }, [id]);

  if (error) return <ErrorState message={error} />;
  if (!session) return <Skeleton className="mt-4 h-64" />;

  const totalSets = session.exercises.reduce((n, we) => n + we.sets.length, 0);
  const minutes = session.completed_at
    ? Math.round(
        (new Date(session.completed_at).getTime() -
          new Date(session.started_at).getTime()) /
          60000
      )
    : null;

  return (
    <div className="space-y-3 pt-2">
      <div className="flex items-center gap-2 text-[11px] text-muted">
        <Link href="/history" className="hover:text-foreground">
          ← History
        </Link>
      </div>
      <h1 className="text-2xl font-bold">{session.name ?? "Workout"}</h1>

      <div className="grid grid-cols-3 gap-2">
        <Stat label="Exercises" value={session.exercises.length} />
        <Stat label="Sets" value={totalSets} />
        <Stat label="Volume" value={formatVolume(session.volume)} accent />
      </div>
      {minutes != null && minutes > 0 ? (
        <p className="px-1 text-xs text-muted">Duration: ~{minutes} min</p>
      ) : null}

      <SectionTitle>Exercises</SectionTitle>
      <div className="space-y-2">
        {session.exercises.map((we) => (
          <details key={we.workout_exercise_id} className="card overflow-hidden p-0">
            <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3">
              <span className="text-sm font-semibold">{we.name}</span>
              <span className="tabular text-xs text-muted">
                {we.sets.length} sets
              </span>
            </summary>
            <div className="border-t border-border px-4 py-3">
              <div className="tabular space-y-1.5">
                {we.sets.map((s, i) => (
                  <div key={i} className="flex justify-between text-sm">
                    <span className="text-muted">Set {i + 1}</span>
                    <span className="font-semibold">{formatSetCompact(s)}</span>
                  </div>
                ))}
                {we.sets.length === 0 ? (
                  <p className="text-xs text-muted">No sets logged.</p>
                ) : null}
              </div>
              {we.notes ? (
                <p className="mt-2 text-xs text-muted">📝 {we.notes}</p>
              ) : null}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
