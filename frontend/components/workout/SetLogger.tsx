"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  ExerciseSummary,
  OverloadRecommendation,
  PreviousPerformance,
  SessionExercise,
  SetData,
} from "@/lib/types";
import { formatSetCompact, formatTimer, trim } from "@/lib/format";
import {
  durationOptions,
  intRange,
  weightOptions,
  type WheelOption,
} from "@/lib/wheel";
import { Badge, ProgressBar } from "@/components/ui/primitives";
import { WheelPickerSheet } from "@/components/ui/WheelPickerSheet";
import { RestTimer } from "./RestTimer";

type PickerField = "weight" | "reps" | "duration" | "added" | "sets";

/**
 * Exercise logger card (spec §4): "Last time" reference, wheel-picker set
 * entry (weight/reps/duration), rest timer and the live progressive-overload
 * suggestion (spec §5). Wheels are the primary input; keyboard fallback
 * remains inside the picker (arrow keys).
 */
export function SetLogger({
  exercise,
  sessionExercise,
  previous,
  onLogSet,
  onDeleteSet,
  onRemove,
  defaultRest,
  bodyweightKg,
}: {
  exercise: ExerciseSummary | null;
  sessionExercise: SessionExercise;
  previous: PreviousPerformance | null;
  onLogSet: (payload: Partial<SetData>) => Promise<void>;
  onDeleteSet: (setId: number) => Promise<void>;
  onRemove: () => void;
  defaultRest: number;
  bodyweightKg?: number | null;
}) {
  const kind = sessionExercise.resistance;
  const isDuration = kind === "duration";
  const isBodyweight = kind === "bodyweight";
  const isWeightedBodyweight = kind === "bodyweight_weighted";

  // ---- last logged + recommendation (prefill only; never auto-completes) --
  const lastSet = sessionExercise.sets[sessionExercise.sets.length - 1];
  const lastWeight = lastSet?.weight ?? null;
  const lastReps = lastSet?.reps ?? null;
  const lastDuration = lastSet?.duration ?? null;
  const lastAdded = lastSet?.added_weight ?? null;

  const recTarget = previous?.recommendation?.target?.[0] ?? null;
  const nothingLogged = sessionExercise.sets.length === 0;

  const [weight, setWeight] = useState<number | null>(() => {
    if (lastWeight != null) return lastWeight;
    if (nothingLogged && recTarget?.weight != null) return recTarget.weight;
    return null;
  });
  const [reps, setReps] = useState<number | null>(() => {
    if (lastReps != null) return lastReps;
    if (nothingLogged && recTarget?.reps != null) return recTarget.reps;
    return null;
  });
  const [duration, setDuration] = useState<number | null>(() => {
    if (lastDuration != null) return lastDuration;
    if (nothingLogged && recTarget?.duration != null) return recTarget.duration;
    return null;
  });
  const [addedWeight, setAddedWeight] = useState<number | null>(() => {
    if (lastAdded != null) return lastAdded;
    if (nothingLogged && recTarget?.added_weight != null)
      return recTarget.added_weight;
    return null;
  });
  const [setsTarget, setSetsTarget] = useState<number>(
    () => previous?.sets?.length ?? 3
  );
  const [picker, setPicker] = useState<PickerField | null>(null);
  const [perDumbbell, setPerDumbbell] = useState(false);
  const [resistanceChoice, setResistanceChoice] = useState<"bw" | "bw_weighted">(
    isWeightedBodyweight ? "bw_weighted" : "bw"
  );
  const [machineType, setMachineType] = useState<
    "plate_loaded" | "weight_stack" | ""
  >("");
  const [machineName, setMachineName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [restRunning, setRestRunning] = useState(false);

  const isDumbbellExercise = exercise?.dumbbell_pair ?? /dumbbell/i.test(
    sessionExercise.name
  );

  // ---- wheel option sets --------------------------------------------------
  const weightStep = isDumbbellExercise ? 0.5 : 2.5; // spec §2: fine for DBs
  const weightOpts = useMemo(
    () => weightOptions(0, 300, weightStep),
    [weightStep]
  );
  const repsOpts = useMemo(
    () => intRange(0, 100).map((v) => ({ value: v, label: String(v) })),
    []
  );
  const setsOpts = useMemo(
    () => intRange(1, 20).map((v) => ({ value: v, label: String(v) })),
    []
  );
  const durOpts = useMemo(() => durationOptions(), []);

  const sheetCfg: Record<
    PickerField,
    { title: string; options: WheelOption[]; unit?: string }
  > = {
    weight: {
      title: sessionExercise.name,
      options: weightOpts,
      unit: "kg",
    },
    reps: { title: "Reps", options: repsOpts },
    duration: { title: "Hold duration", options: durOpts },
    added: { title: "Added weight", options: weightOpts, unit: "kg" },
    sets: { title: "Target sets", options: setsOpts },
  };

  const pickerValue: number | null =
    picker === "weight"
      ? weight
      : picker === "reps"
        ? reps
        : picker === "duration"
          ? duration
          : picker === "added"
            ? addedWeight
            : picker === "sets"
              ? setsTarget
              : null;

  function applyPickerValue(v: number) {
    if (picker === "weight") setWeight(v);
    else if (picker === "reps") setReps(v);
    else if (picker === "duration") setDuration(v);
    else if (picker === "added") setAddedWeight(v);
    else if (picker === "sets") setSetsTarget(v);
  }

  async function submit() {
    setError(null);
    const payload: Partial<SetData> = {};
    if (isDuration) {
      if (!duration || duration <= 0)
        return setError("Pick a hold duration.");
      payload.duration = duration;
    } else {
      if (reps == null || reps < 0) return setError("Pick the reps.");
      payload.reps = reps;
      if (isBodyweight || isWeightedBodyweight) {
        payload.bodyweight = null; // backend resolves from latest bodyweight log
        if (resistanceChoice === "bw_weighted") {
          if (!addedWeight || addedWeight <= 0)
            return setError("Pick added weight, or switch to Bodyweight.");
          payload.added_weight = addedWeight;
        }
      } else {
        if (!weight || weight <= 0) return setError("Pick the weight.");
        payload.weight = weight;
        payload.per_dumbbell = isDumbbellExercise ? perDumbbell : null;
        if (machineType) payload.machine_type = machineType;
        if (machineName) payload.machine_name = machineName;
      }
    }
    setSaving(true);
    try {
      await onLogSet(payload);
      // values persist for fast same-weight next sets (tap Log again)
      setRestRunning(true); // rest timer starts after each set (spec §8)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to log set");
    } finally {
      setSaving(false);
    }
  }

  const rec: OverloadRecommendation | null = previous?.recommendation ?? null;
  const lastTimeLabel = useMemo(() => {
    if (!previous?.sets?.length) return null;
    return previous.sets.map((s) => formatSetCompact(s)).join("   ·   ");
  }, [previous]);

  const totalResistance =
    isWeightedBodyweight &&
    resistanceChoice === "bw_weighted" &&
    addedWeight != null
      ? (bodyweightKg ?? 0) + addedWeight
      : null;

  return (
    <div className="card animate-fade-up overflow-hidden">
      {/* header */}
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-bold">{sessionExercise.name}</div>
          <div className="text-[11px] text-muted">
            {sessionExercise.primary_muscle ?? ""}{" "}
            {isDumbbellExercise ? "· per-dumbbell entry" : ""}
          </div>
        </div>
        {/* target sets wheel trigger + remove (spec §3) */}
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            onClick={() => setPicker("sets")}
            className="tabular rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs font-semibold text-muted transition hover:text-foreground"
            aria-label={`Target sets: ${setsTarget}. Tap to change.`}
          >
            Set {sessionExercise.sets.length + 1}
            <span className="text-muted/70"> / {setsTarget}</span>
          </button>
          <button
            type="button"
            onClick={onRemove}
            className="rounded-lg px-2 py-1.5 text-xs text-muted transition hover:bg-surface-2 hover:text-danger"
            aria-label={`Remove ${sessionExercise.name}`}
          >
            Remove
          </button>
        </div>
      </div>

      <div className="space-y-3 p-4">
        {/* previous performance banner (spec §4, §9) */}
        {lastTimeLabel ? (
          <div className="rounded-xl border border-border bg-surface-2/60 px-3 py-2.5">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
              Last time ({previous!.session_date})
            </div>
            <div className="tabular mt-1 text-sm font-semibold text-foreground">
              {lastTimeLabel}
            </div>
          </div>
        ) : null}

        {/* progressive overload suggestion (spec §5, §10) */}
        {rec ? (
          <div className="rounded-xl border border-accent/25 bg-accent/5 px-3 py-2.5">
            <div className="flex items-center gap-2">
              <Badge tone="accent">Next target</Badge>
              <span className="text-[11px] text-muted">
                {rec.action.replace(/_/g, " ")}
              </span>
            </div>
            <div className="mt-1 text-sm font-semibold">{rec.headline}</div>
            <div className="mt-0.5 text-xs text-muted">{rec.detail}</div>
          </div>
        ) : null}

        {/* logged sets */}
        {sessionExercise.sets.length > 0 ? (
          <div className="space-y-1.5">
            {sessionExercise.sets.map((s, i) => (
              <div
                key={s.id ?? i}
                className="flex items-center justify-between rounded-lg bg-surface-2/50 px-3 py-2"
              >
                <span className="text-xs text-muted">Set {i + 1}</span>
                <span className="tabular text-sm font-bold">
                  {formatSetCompact(s)}
                  {s.reps != null && !isDuration ? ` × ${s.reps}` : ""}
                </span>
                {s.id ? (
                  <button
                    type="button"
                    onClick={() => onDeleteSet(s.id!)}
                    className="text-xs text-muted transition hover:text-danger"
                    aria-label="Delete set"
                  >
                    ✕
                  </button>
                ) : (
                  <span />
                )}
              </div>
            ))}
            {/* set progress vs target/previous count */}
            <div className="pt-1">
              <div className="mb-1 text-[11px] text-muted">
                {sessionExercise.sets.length} /{" "}
                {previous?.sets?.length
                  ? `${previous.sets.length} of last session's sets`
                  : `${setsTarget} planned`}
              </div>
              <ProgressBar
                value={sessionExercise.sets.length}
                max={previous?.sets?.length ?? setsTarget}
              />
            </div>
          </div>
        ) : null}

        {/* inputs — bodyweight resistance choice (spec §3 / §5) */}
        {isBodyweight || isWeightedBodyweight ? (
          <div className="flex gap-1.5">
            {(["bw", "bw_weighted"] as const).map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => setResistanceChoice(opt)}
                className={`flex-1 rounded-lg border px-2 py-1.5 text-xs font-medium transition ${
                  resistanceChoice === opt
                    ? "border-accent/60 text-accent"
                    : "border-border text-muted"
                }`}
              >
                {opt === "bw" ? "Bodyweight" : "BW + Added Weight"}
              </button>
            ))}
          </div>
        ) : null}

        <div className="grid grid-cols-2 gap-2">
          {/* weight / added weight / duration field */}
          {!isDuration && !isBodyweight && resistanceChoice === "bw" ? (
            <WheelField
              label={isDumbbellExercise ? "Weight / DB" : "Weight"}
              display={weight != null ? `${trim(weight)} kg` : "Pick"}
              sub={
                isDumbbellExercise && weight != null && perDumbbell
                  ? `${trim(weight)} kg × 2 hands = ${trim(weight * 2)} kg`
                  : undefined
              }
              onClick={() => setPicker("weight")}
              accent
            />
          ) : null}
          {resistanceChoice === "bw_weighted" ? (
            <WheelField
              label="Added weight"
              display={addedWeight != null ? `${trim(addedWeight)} kg` : "Pick"}
              sub={
                totalResistance != null && bodyweightKg != null
                  ? `Total ${trim(totalResistance)} kg (BW ${trim(bodyweightKg)} + added)`
                  : bodyweightKg != null
                    ? `BW ${trim(bodyweightKg)} kg`
                    : undefined
              }
              onClick={() => setPicker("added")}
            />
          ) : null}
          {isDuration ? (
            <WheelField
              label="Duration"
              display={duration != null ? formatTimer(duration) : "Pick"}
              onClick={() => setPicker("duration")}
              accent
            />
          ) : null}

          {/* reps field (hidden for pure-duration exercises) */}
          {!isDuration ? (
            <WheelField
              label="Reps"
              display={reps != null ? String(reps) : "Pick"}
              onClick={() => setPicker("reps")}
            />
          ) : null}
        </div>

        <button
          type="button"
          onClick={submit}
          disabled={saving}
          className="w-full rounded-xl bg-accent py-3 text-base font-bold text-accent-foreground transition hover:brightness-110 active:brightness-95 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Log this set"
        >
          {saving ? "Logging…" : "Complete Set"}
        </button>

        {/* machine questions (spec §3 Type C / D) */}
        {!isDuration && !isBodyweight && resistanceChoice === "bw" &&
        (sessionExercise.exercise_type === "machine" ||
          sessionExercise.exercise_type === "cable") ? (
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex gap-1.5">
              {(["plate_loaded", "weight_stack"] as const).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() =>
                    setMachineType((t) => (t === opt ? "" : opt))
                  }
                  className={`rounded-lg border px-2 py-1 text-[11px] font-medium transition ${
                    machineType === opt
                      ? "border-accent/60 text-accent"
                      : "border-border text-muted"
                  }`}
                >
                  {opt === "plate_loaded" ? "Plate loaded" : "Weight stack"}
                </button>
              ))}
            </div>
            <input
              value={machineName}
              onChange={(e) => setMachineName(e.target.value)}
              placeholder="Machine name (e.g. Life Fitness Leg Press)"
              className="min-w-0 flex-1 rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs outline-none placeholder:text-muted/60 focus:border-accent/50"
            />
          </div>
        ) : null}

        {/* per-dumbbell choice (spec §3 Type B / §6) */}
        {isDumbbellExercise && !isDuration && !isBodyweight ? (
          <div className="flex items-center gap-2 text-xs text-muted">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={perDumbbell}
                onChange={(e) => setPerDumbbell(e.target.checked)}
                className="accent-[var(--accent)]"
              />
              Weight is per dumbbell (total load = ×2)
            </label>
          </div>
        ) : null}

        {error ? <p className="text-xs text-danger">{error}</p> : null}

        {restRunning ? (
          <RestTimer defaultSeconds={defaultRest} />
        ) : (
          <details className="text-xs text-muted">
            <summary className="cursor-pointer select-none hover:text-foreground">
              Rest timer
            </summary>
          </details>
        )}
      </div>

      {/* the single reusable wheel sheet (spec §14) */}
      <WheelPickerSheet
        open={picker !== null}
        title={picker ? sheetCfg[picker].title : ""}
        options={picker ? sheetCfg[picker].options : []}
        value={pickerValue}
        unit={picker ? sheetCfg[picker].unit : undefined}
        onChange={applyPickerValue}
        onClose={() => setPicker(null)}
      />
    </div>
  );
}

/** Tappable field that opens a wheel picker (replaces number typing). */
function WheelField({
  label,
  display,
  sub,
  onClick,
  accent,
}: {
  label: string;
  display: string;
  sub?: string;
  onClick: () => void;
  accent?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex min-w-0 flex-col items-start gap-0.5 rounded-xl border px-3 py-2.5 text-left transition active:brightness-95 ${
        accent
          ? "border-accent/40 bg-accent/5 hover:border-accent/60"
          : "border-border bg-surface-2 hover:border-muted/40"
      }`}
      aria-label={`${label}: ${display}. Tap to open picker.`}
    >
      <span className="text-[11px] font-medium uppercase tracking-wider text-muted">
        {label}
      </span>
      <span
        className={`tabular text-2xl font-bold leading-tight ${
          accent ? "text-accent" : "text-foreground"
        }`}
      >
        {display}
      </span>
      {sub ? (
        <span className="text-[10px] text-muted">{sub}</span>
      ) : null}
    </button>
  );
}
