/** Shared helpers for the wheel-picker system (spec: wheel input §1–§4). */

import { trim } from "./format";

/**
 * A discrete wheel option. `value` is what gets stored/submitted;
 * `label` is what's shown (e.g. "2:30" for durations).
 */
export interface WheelOption {
  value: number;
  label: string;
}

/** Inclusive list of integers min..max (reps 0–100, sets 1–20). */
export function intRange(min: number, max: number): number[] {
  const out: number[] = [];
  for (let v = min; v <= max; v++) out.push(v);
  return out;
}

/**
 * Weight steps per the spec: fine 0.5 increments for lighter loads,
 * 2.5 for heavier ones. Step respects a maximum option count so the
 * wheel DOM stays small even for heavy ranges (0–500).
 */
export function weightStep(min: number): number {
  return min >= 50 ? 2.5 : 0.5;
}

/**
 * Build the option list for a weight wheel: min..max on a fixed step,
 * with a hard cap of ~300 options (extends max as needed so the cap
 * always lands on a multiple of step).
 */
export function weightOptions(
  min: number,
  max: number,
  step: number
): WheelOption[] {
  const out: WheelOption[] = [];
  const count = Math.floor((max - min) / step);
  const capped = Math.min(count, 299);
  for (let i = 0; i <= capped; i++) {
    const v = Math.round((min + i * step) * 100) / 100;
    out.push({ value: v, label: trim(v) });
  }
  return out;
}

/** Duration options at 15s steps up to 5 min (spec §4), plus 6:00 for long rests. */
export function durationOptions(): WheelOption[] {
  const secs = [
    15, 30, 45, 60, 75, 90, 105, 120, 150, 180, 210, 240, 300, 330, 360,
  ];
  return secs.map((s) => ({ value: s, label: formatClock(s) }));
}

/** 95 -> "1:35" */
export function formatClock(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = Math.round(totalSeconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Parse "1:30" or "90" (seconds) into 90. Returns null when invalid. */
export function parseClock(input: string): number | null {
  const t = input.trim();
  if (!t) return null;
  if (t.includes(":")) {
    const [m, s] = t.split(":");
    const mm = parseInt(m, 10);
    const ss = parseInt(s, 10);
    if (Number.isNaN(mm) || Number.isNaN(ss)) return null;
    return mm * 60 + ss;
  }
  const n = Number(t);
  return Number.isFinite(n) ? Math.round(n) : null;
}

/**
 * Nearest option index for an arbitrary value (e.g. a recommendation of
 * 62.5 kg when the wheel step is 0.5, or 62.3 with step 2.5 → snaps to 62.5).
 */
export function nearestIndex(options: WheelOption[], value: number): number {
  let best = 0;
  let bestDist = Infinity;
  for (let i = 0; i < options.length; i++) {
    const d = Math.abs(options[i].value - value);
    if (d < bestDist) {
      best = i;
      bestDist = d;
    }
  }
  return best;
}
