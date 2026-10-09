/** Formatting + unit conversion helpers (spec §20). */

import type { SetData } from "./types";

export function formatLoad(s: {
  weight?: number | null;
  per_dumbbell?: boolean | null;
  duration?: number | null;
  bodyweight?: number | null;
  added_weight?: number | null;
}): string {
  if (s.duration != null) return `${trim(s.duration)}s`;
  if (s.weight != null) {
    return s.per_dumbbell
      ? `${trim(s.weight)} kg × 2 DB`
      : `${trim(s.weight)} kg`;
  }
  if (s.added_weight != null) return `+${trim(s.added_weight)} kg`;
  if (s.bodyweight != null) return "BW";
  return "—";
}

export function formatSetCompact(s: SetData): string {
  if (s.duration != null) return `${trim(s.duration)}s`;
  const load = formatLoad(s);
  if (s.reps != null) return `${load} × ${s.reps}`;
  return load;
}

export function trim(n: number): string {
  return Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100);
}

export function formatVolume(kg: number): string {
  if (kg >= 1000) return `${(kg / 1000).toFixed(kg >= 10000 ? 0 : 1)}k kg`;
  return `${Math.round(kg)} kg`;
}

export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  if (h > 0) return `${h}h ${m.toString().padStart(2, "0")}m`;
  return `${m}m`;
}

export function formatTimer(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function formatDay(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatDayFull(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function relativeDay(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  const diff = Math.round((today.getTime() - d.getTime()) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  if (diff < 7) return `${diff} days ago`;
  return formatDay(iso);
}

/** kg -> lb and back, for display only; stored data stays in kg. */
export function kgToDisplay(kg: number, unit: "kg" | "lb"): number {
  return unit === "kg" ? kg : Math.round(kg * 2.20462 * 100) / 100;
}

export function displayToKg(v: number, unit: "kg" | "lb"): number {
  return unit === "kg" ? v : Math.round((v / 2.20462) * 100) / 100;
}

export const PR_CATEGORY_LABELS: Record<string, string> = {
  heaviest_weight: "Heaviest Weight",
  most_reps: "Most Reps",
  best_1rm: "Best Est. 1RM",
  best_volume_set: "Best Volume Set",
  longest_duration: "Longest Hold",
  most_reps_bodyweight: "Most Reps (BW)",
  most_reps_weighted: "Most Reps (Weighted)",
  highest_added_weight: "Highest Added Weight",
};

export function formatPRValue(rec: {
  category: string;
  value?: number | null;
  weight: number | null;
  reps: number | null;
  added_weight: number | null;
  duration: number | null;
}): string {
  switch (rec.category) {
    case "heaviest_weight":
      return `${trim(rec.weight ?? 0)} kg`;
    case "most_reps":
      return `${rec.reps} reps @ ${trim(rec.weight ?? 0)} kg`;
    case "best_1rm":
      return `~${trim(rec.value ?? 0)} kg (est.)`;
    case "best_volume_set":
      return `${trim(rec.value ?? 0)} kg vol.`;
    case "longest_duration":
      return `${trim(rec.duration ?? 0)}s`;
    case "most_reps_bodyweight":
      return `${rec.reps} reps (BW)`;
    case "most_reps_weighted":
      return `${rec.reps} reps @ +${trim(rec.added_weight ?? 0)} kg`;
    case "highest_added_weight":
      return `+${trim(rec.added_weight ?? 0)} kg`;
    default:
      return trim(rec.value ?? 0);
  }
}
