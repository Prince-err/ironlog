"use client";

import { useEffect, useState } from "react";
import {
  createCustomExercise,
  fetchMuscleGroups,
} from "@/lib/api";
import { Button, Card } from "@/components/ui/primitives";

const TYPE_OPTIONS = [
  { value: "free_weight", label: "Free weight", resistance: "external" },
  { value: "machine", label: "Machine", resistance: "external" },
  { value: "cable", label: "Cable", resistance: "external" },
  { value: "bodyweight", label: "Bodyweight", resistance: "bodyweight" },
  { value: "bodyweight", label: "Bodyweight + added weight", resistance: "bodyweight_weighted" },
  { value: "duration", label: "Duration (timed)", resistance: "duration" },
];

/** Admin-style form for adding a custom exercise to the library. */
export function AddExerciseForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [muscles, setMuscles] = useState<{ id: number; name: string }[]>([]);
  const [name, setName] = useState("");
  const [selIdx, setSelIdx] = useState(0);
  const [muscleId, setMuscleId] = useState<number | null>(null);
  const [perDumbbell, setPerDumbbell] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ tone: "ok" | "err"; text: string } | null>(null);

  const needsPerDumbbell = TYPE_OPTIONS[selIdx].resistance === "external";

  useEffect(() => {
    if (!open || muscles.length > 0) return;
    fetchMuscleGroups()
      .then((rows) => {
        setMuscles(rows);
        setMuscleId(rows[0]?.id ?? null);
      })
      .catch(() => setMsg({ tone: "err", text: "Failed to load muscle groups" }));
  }, [open, muscles.length]);

  async function submit() {
    if (!name.trim()) return;
    setBusy(true);
    setMsg(null);
    try {
      const opt = TYPE_OPTIONS[selIdx];
      const created = await createCustomExercise({
        name: name.trim(),
        exercise_type: opt.value,
        resistance: opt.resistance,
        primary_muscle_id: muscleId,
        dumbbell_pair: perDumbbell,
      });
      setMsg({ tone: "ok", text: `Added “${created.name}” to your library.` });
      setName("");
      setPerDumbbell(false);
      onCreated();
    } catch (e) {
      setMsg({
        tone: "err",
        text: e instanceof Error ? e.message : "Failed to add exercise",
      });
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-border py-3 text-sm font-semibold text-muted transition hover:border-accent/50 hover:text-accent"
      >
        <span className="text-lg leading-none">+</span> Add exercise
      </button>
      );
  }

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-bold">New exercise</div>
        <button
          onClick={() => setOpen(false)}
          className="text-xs text-muted hover:text-foreground"
        >
          Cancel
        </button>
      </div>

      <label className="block">
        <span className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted">
          Name
        </span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Smith Machine Row"
          className="w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm outline-none placeholder:text-muted/60 focus:border-accent/50"
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted">
          Type
        </span>
        <select
          value={selIdx}
          onChange={(e) => setSelIdx(Number(e.target.value))}
          className="w-full appearance-none rounded-xl border border-border bg-surface px-3 py-2.5 text-sm outline-none focus:border-accent/50"
        >
          {TYPE_OPTIONS.map((o, i) => (
            <option key={i} value={i} className="bg-surface">
              {o.label}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted">
          Primary muscle
        </span>
        <select
          value={muscleId ?? ""}
          onChange={(e) => setMuscleId(Number(e.target.value))}
          className="w-full appearance-none rounded-xl border border-border bg-surface px-3 py-2.5 text-sm outline-none focus:border-accent/50"
        >
          {muscles.map((m) => (
            <option key={m.id} value={m.id} className="bg-surface">
              {m.name}
            </option>
          ))}
        </select>
      </label>

      {needsPerDumbbell ? (
        <label className="flex cursor-pointer items-center gap-2.5 text-sm">
          <input
            type="checkbox"
            checked={perDumbbell}
            onChange={(e) => setPerDumbbell(e.target.checked)}
            className="h-4 w-4 accent-[var(--accent)]"
          />
          Weight is per dumbbell (×2 total load)
        </label>
      ) : null}

      {msg ? (
        <p
          className={`text-xs ${msg.tone === "ok" ? "text-success" : "text-danger"}`}
        >
          {msg.text}
        </p>
      ) : null}

      <Button full onClick={submit} disabled={busy || !name.trim()}>
        {busy ? "Adding…" : "Add exercise"}
      </Button>
    </Card>
  );
}
