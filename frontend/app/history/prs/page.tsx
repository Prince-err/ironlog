"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { PRGroup } from "@/lib/types";
import { fetchPRs } from "@/lib/api";
import { formatPRValue, PR_CATEGORY_LABELS, relativeDay } from "@/lib/format";
import {
  Badge,
  Card,
  ErrorState,
  Skeleton,
} from "@/components/ui/primitives";

export default function PRsPage() {
  const [groups, setGroups] = useState<PRGroup[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPRs()
      .then(setGroups)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load PRs")
      );
  }, []);

  return (
    <div className="space-y-3 pt-2">
      <div className="flex items-center gap-2 text-[11px] text-muted">
        <Link href="/history" className="hover:text-foreground">
          ← History
        </Link>
      </div>
      <h1 className="text-2xl font-bold">Personal Records</h1>

      {error ? <ErrorState message={error} /> : null}
      {!groups && !error ? <Skeleton className="h-64" /> : null}

      {(groups ?? []).map((g) => (
        <Card key={g.exercise_id}>
          <Link
            href={`/exercises/${g.exercise_id}`}
            className="text-sm font-bold hover:text-accent"
          >
            {g.exercise}
          </Link>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {g.records.map((rec) => (
              <div
                key={rec.category}
                className="rounded-xl border border-border bg-surface-2/50 px-3 py-2"
              >
                <div className="text-[11px] text-muted">
                  {PR_CATEGORY_LABELS[rec.category] ?? rec.category}
                </div>
                <div className="tabular mt-0.5 text-sm font-bold text-accent">
                  {formatPRValue(rec)}
                </div>
                {rec.achieved_at ? (
                  <div className="mt-0.5 text-[10px] text-muted">
                    {relativeDay(rec.achieved_at.slice(0, 10))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </Card>
      ))}

      {groups && groups.length === 0 ? (
        <Card className="py-6 text-center text-sm text-muted">
          Complete your first workout to set PRs.
        </Card>
      ) : null}

      {groups && groups.length > 0 ? (
        <p className="px-1 text-[11px] text-muted">
          <Badge>note</Badge> Estimated 1RM is calculated (Epley), not measured.
        </p>
      ) : null}
    </div>
  );
}
