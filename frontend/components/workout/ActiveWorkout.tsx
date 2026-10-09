"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  CompleteSummary,
  ExerciseSummary,
  PreviousPerformance,
  SessionSummary,
} from "@/lib/types";
import {
  addExercise,
  completeSession,
  deleteSet,
  fetchExercises,
  fetchPreviousPerformance,
  fetchProfile,
  logSet,
  removeExercise,
} from "@/lib/api";
import { formatDuration, formatVolume } from "@/lib/format";
import { Button, EmptyState, ErrorState, Skeleton } from "@/components/ui/primitives";
import { SetLogger } from "./SetLogger";
import { WorkoutComplete } from "./WorkoutComplete";
import { ExercisePickerModal } from "./ExercisePickerModal";

export function ActiveWorkout({ initial }: { initial: SessionSummary }) {
  const [session, setSession] = useState(initial);
  const [exercises, setExercises] = useState<Record<number, ExerciseSummary>>({});
  const [previous, setPrevious] = useState<Record<number, PreviousPerformance | null>>({});
  const [pickerOpen, setPickerOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<CompleteSummary | null>(null);
  const [elapsed, setElapsed] = useState("");
  const [bodyweightKg, setBodyweightKg] = useState<number | null>(null);

  // profile bodyweight (shown alongside added-weight entry)
  useEffect(() => {
    let cancelled = false;
    fetchProfile()
      .then((p) => {
        if (!cancelled) setBodyweightKg(p.bodyweight_kg ?? null);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // resolve exercise metadata
  useEffect(() => {
    let cancelled = false;
    fetchExercises().then((all) => {
      if (cancelled) return;
      const map: Record<number, ExerciseSummary> = {};
      for (const e of all) map[e.id] = e;
      setExercises(map);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // resolve "previous performance" per exercise (cache per exercise id)
  useEffect(() => {
    const missing = session.exercises
      .map((we) => we.exercise_id)
      .filter((id) => !(id in previous));
    if (missing.length === 0) return;
    let cancelled = false;
    (async () => {
      await Promise.resolve();
      if (cancelled) return;
      // mark as loading first
      setPrevious((p) => {
        const next = { ...p };
        for (const id of missing) if (!(id in next)) next[id] = null;
        return next;
      });
      await Promise.all(
        missing.map((id) =>
          fetchPreviousPerformance(id)
            .then((perf) => {
              if (!cancelled)
                setPrevious((prev) => ({ ...prev, [id]: perf }));
            })
            .catch(() => {
              if (!cancelled)
                setPrevious((prev) => ({ ...prev, [id]: null }));
            })
        )
      );
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  // elapsed timer
  useEffect(() => {
    const started = new Date(session.started_at).getTime();
    const tick = () => {
      const mins = (Date.now() - started) / 60000;
      setElapsed(formatDuration(Math.max(0, mins)));
    };
    const t = setInterval(tick, 30000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.started_at]);

  const totalSets = useMemo(
    () => session.exercises.reduce((n, we) => n + we.sets.length, 0),
    [session]
  );

  const refreshSession = useCallback(async () => {
    // optimistic: re-fetch not implemented per-set; we patch locally
  }, []);

  async function handleLogSet(workoutExerciseId: number, payload: Parameters<typeof logSet>[1]) {
    setError(null);
    try {
      const created = await logSet(workoutExerciseId, payload);
      setSession((s) => ({
        ...s,
        exercises: s.exercises.map((we) =>
          we.workout_exercise_id === workoutExerciseId
            ? {
                ...we,
                sets: [...we.sets, { ...payload, ...created } as typeof we.sets[number]],
              }
            : we
        ),
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to log set");
      throw e;
    }
  }

  async function handleDeleteSet(setId: number) {
    await deleteSet(setId);
    setSession((s) => ({
      ...s,
      exercises: s.exercises.map((we) => ({
        ...we,
        sets: we.sets.filter((st) => st.id !== setId),
      })),
    }));
  }

  async function handleAddExercise(exerciseId: number) {
    const res = await addExercise(session.id, exerciseId);
    setPickerOpen(false);
    // minimal refresh: append skeleton exercise, fetch full session
    const fresh = await import("@/lib/api").then((m) => m.fetchSession(session.id));
    setSession(fresh);
    void res;
  }

  async function handleRemove(workoutExerciseId: number) {
    await removeExercise(session.id, workoutExerciseId);
    setSession((s) => ({
      ...s,
      exercises: s.exercises.filter((we) => we.workout_exercise_id !== workoutExerciseId),
    }));
  }

  async function handleComplete() {
    try {
      const result = await completeSession(session.id);
      setSummary(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to complete workout");
    }
  }

  if (summary) {
    return <WorkoutComplete summary={summary} sessionName={session.name} />;
  }

  return (
    <div className="space-y-3">
      <div className="sticky top-0 z-40 -mx-4 border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
              In progress
            </div>
            <div className="text-lg font-bold">{session.name ?? "Workout"}</div>
          </div>
          <div className="text-right">
            <div className="tabular text-sm font-bold">{elapsed}</div>
            <div className="text-[11px] text-muted">
              {session.exercises.length} ex · {totalSets} sets
            </div>
          </div>
        </div>
      </div>

      {error ? <ErrorState message={error} /> : null}

      {session.exercises.length === 0 ? (
        <EmptyState
          title="No exercises yet"
          hint="Add your first exercise to start logging."
        />
      ) : null}

      {session.exercises.map((we) => {
        const exMeta = exercises[we.exercise_id] ?? null;
        return exercises && exMeta !== undefined ? (
          <SetLogger
            key={we.workout_exercise_id}
            exercise={exMeta}
            sessionExercise={we}
            previous={previous[we.exercise_id] ?? null}
            onLogSet={(payload) => handleLogSet(we.workout_exercise_id, payload)}
            onDeleteSet={handleDeleteSet}
            onRemove={() => handleRemove(we.workout_exercise_id)}
            defaultRest={90}
            bodyweightKg={bodyweightKg}
          />
        ) : (
          <Skeleton key={we.workout_exercise_id} className="h-40" />
        );
      })}

      <div className="grid grid-cols-2 gap-2 pt-2">
        <Button variant="secondary" onClick={() => setPickerOpen(true)}>
          + Add exercise
        </Button>
        <Button onClick={handleComplete} disabled={totalSets === 0}>
          Finish workout
        </Button>
      </div>

      {pickerOpen ? (
        <ExercisePickerModal
          onClose={() => setPickerOpen(false)}
          onSelect={handleAddExercise}
        />
      ) : null}
      {void refreshSession}
    </div>
  );
}
