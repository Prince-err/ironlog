"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { SessionSummary, TemplateData } from "@/lib/types";
import {
  fetchActiveSession,
  fetchTemplatePrevious,
  fetchTemplates,
  startSession,
} from "@/lib/api";
import { formatSetCompact, relativeDay } from "@/lib/format";
import { Badge, Button, Card, EmptyState, ErrorState, SectionTitle } from "@/components/ui/primitives";

/** Workout tab root: resume active, start previous, template or blank. */
export function StartWorkout() {
  const [templates, setTemplates] = useState<TemplateData[]>([]);
  const [active, setActive] = useState<SessionSummary | null>(null);
  const [snapshots, setSnapshots] = useState<Record<number, Awaited<ReturnType<typeof fetchTemplatePrevious>>>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | "blank" | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [tpls, activeSession] = await Promise.all([
        fetchTemplates(),
        fetchActiveSession(),
      ]);
      setTemplates(tpls);
      setActive(activeSession);
      // load "repeat last" snapshots for each template
      const snaps: typeof snapshots = {};
      await Promise.all(
        tpls.map(async (t) => {
          snaps[t.id] = await fetchTemplatePrevious(t.id).catch(() => null);
        })
      );
      setSnapshots(snaps);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await Promise.resolve();
      if (!cancelled) await load();
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const router = useRouter();

  async function start(opts: { template_id?: number }) {
    setBusy(opts.template_id ?? "blank");
    setError(null);
    try {
      const s = await startSession({
        template_id: opts.template_id ?? null,
        name: null,
      });
      router.push(`/workout/${s.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start");
      setBusy(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="card h-24 animate-pulse" />
        <div className="card h-40 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {error ? <ErrorState message={error} /> : null}

      {active ? (
        <Card className="animate-fade-up border-accent/40">
          <div className="flex items-center justify-between gap-3">
            <div>
              <Badge tone="accent">In progress</Badge>
              <div className="mt-1.5 text-lg font-bold">
                {active.name ?? "Workout"}
              </div>
              <div className="text-xs text-muted">
                {active.exercises.length} exercises ·{" "}
                {active.exercises.reduce((n, we) => n + we.sets.length, 0)} sets
                logged
              </div>
            </div>
            <Button onClick={() => router.push(`/workout/${active.id}`)}>
              Resume
            </Button>
          </div>
        </Card>
      ) : null}

      <SectionTitle>Start your workout</SectionTitle>

      {templates.length === 0 ? (
        <EmptyState
          title="No templates yet"
          hint="Create a routine in the Templates tab, or start a blank workout."
        />
      ) : null}

      {templates.map((t) => {
        const snap = snapshots[t.id];
        return (
          <Card key={t.id} className="animate-fade-up">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-base font-bold">{t.name}</div>
                <div className="mt-0.5 text-xs text-muted">
                  {t.exercises.length} exercises
                  {t.exercises[0]?.rest_seconds
                    ? ` · rest ${Math.round(t.exercises[0].rest_seconds / 60)}m`
                    : ""}
                </div>
              </div>
              <div className="flex shrink-0 flex-col gap-1.5">
                <Button onClick={() => start({ template_id: t.id })} disabled={busy !== null}>
                  {busy === t.id ? "…" : "Start"}
                </Button>
                {snap ? (
                  <Button
                    variant="secondary"
                    onClick={() => start({ template_id: t.id })}
                    disabled={busy !== null}
                  >
                    Start previous
                  </Button>
                ) : null}
              </div>
            </div>
            {snap ? (
              <div className="mt-3 rounded-xl border border-border bg-surface-2/50 px-3 py-2.5">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                  Last time · {relativeDay(snap.date)}
                </div>
                <div className="mt-1 space-y-0.5">
                  {snap.exercises.slice(0, 4).map((ex) => (
                    <div key={ex.exercise_id} className="tabular flex justify-between text-xs">
                      <span className="truncate text-foreground/90">{ex.name}</span>
                      <span className="text-muted">
                        {ex.sets.map((s) => formatSetCompact(s)).join(", ")}
                      </span>
                    </div>
                  ))}
                  {snap.exercises.length > 4 ? (
                    <div className="text-[11px] text-muted">
                      +{snap.exercises.length - 4} more
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}
          </Card>
        );
      })}

      <Card>
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">Blank workout</div>
            <div className="text-xs text-muted">Pick exercises as you go</div>
          </div>
          <Button
            variant="secondary"
            onClick={() => start({})}
            disabled={busy !== null}
          >
            {busy === "blank" ? "…" : "Start"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
