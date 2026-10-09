"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { ExerciseSummary } from "@/lib/types";
import { fetchExercises } from "@/lib/api";
import { AddExerciseForm } from "@/components/exercises/AddExerciseForm";
import { Card, ErrorState, Skeleton } from "@/components/ui/primitives";

export default function ExerciseIndexPage() {
  const [exercises, setExercises] = useState<ExerciseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  const load = () => {
    fetchExercises()
      .then(setExercises)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load exercises")
      );
  };

  useEffect(load, []);

  const groups = useMemo(() => {
    const filtered = (exercises ?? []).filter((e) =>
      q ? e.name.toLowerCase().includes(q.toLowerCase()) : true
    );
    const map = new Map<string, ExerciseSummary[]>();
    for (const e of filtered) {
      const g = e.primary_muscle ?? "Other";
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(e);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [exercises, q]);

  return (
    <div className="space-y-3 pt-2">
      <div className="flex items-center gap-2 text-[11px] text-muted">
        <Link href="/history" className="hover:text-foreground">
          ← History
        </Link>
      </div>
      <h1 className="text-2xl font-bold">Exercise History</h1>

      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search exercises…"
        className="w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm outline-none placeholder:text-muted/60 focus:border-accent/50"
      />

      <AddExerciseForm onCreated={load} />

      {error ? <ErrorState message={error} /> : null}
      {!exercises && !error ? <Skeleton className="h-64" /> : null}

      {groups.map(([group, items]) => (
        <div key={group}>
          <h2 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-[0.14em] text-muted">
            {group} · {items.length}
          </h2>
          <div className="space-y-1.5">
            {items.map((e) => (
              <Link key={e.id} href={`/exercises/${e.id}`} className="contents">
                <Card className="flex items-center justify-between py-3 transition hover:border-muted/40">
                  <span className="truncate text-sm font-medium">{e.name}</span>
                  <span className="shrink-0 text-[11px] text-muted">
                    {e.exercise_type.replace(/_/g, " ")}
                  </span>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
