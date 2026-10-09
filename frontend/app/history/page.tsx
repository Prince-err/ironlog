"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { HistoryRow } from "@/lib/types";
import { fetchHistory } from "@/lib/api";
import { formatVolume, relativeDay } from "@/lib/format";
import {
  Card,
  ErrorState,
  SectionTitle,
  Skeleton,
} from "@/components/ui/primitives";

export default function HistoryPage() {
  const [rows, setRows] = useState<HistoryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHistory(60)
      .then(setRows)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load history")
      );
  }, []);

  return (
    <div className="space-y-3 pt-2">
      <h1 className="text-2xl font-bold">History</h1>

      <div className="grid grid-cols-3 gap-2">
        <TabLink href="/history" label="Workouts" active />
        <TabLink href="/history/exercises" label="Exercises" />
        <TabLink href="/history/prs" label="PRs" />
      </div>

      {error ? <ErrorState message={error} /> : null}
      {!rows && !error ? (
        <Skeleton className="h-64" />
      ) : (
        <>
          <SectionTitle>Completed workouts</SectionTitle>
          <div className="space-y-2">
            {(rows ?? []).map((row) => (
              <Link key={row.id} href={`/history/session/${row.id}`} className="contents">
                <Card className="transition hover:border-muted/40">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold">
                        {row.name ?? "Workout"}
                      </div>
                      <div className="text-[11px] text-muted">
                        {relativeDay(row.date)} · {row.exercises} exercises ·{" "}
                        {row.sets} sets
                      </div>
                    </div>
                    <div className="tabular shrink-0 text-sm font-semibold text-accent">
                      {formatVolume(row.volume)}
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
            {rows && rows.length === 0 ? (
              <Card className="py-6 text-center text-sm text-muted">
                No workouts yet. Your first session will appear here.
              </Card>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}

function TabLink({
  href,
  label,
  active,
}: {
  href: string;
  label: string;
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`rounded-xl border px-3 py-2 text-center text-xs font-semibold transition ${
        active
          ? "border-accent/60 text-accent"
          : "border-border text-muted hover:text-foreground"
      }`}
    >
      {label}
    </Link>
  );
}
