"use client";

import { useEffect, useMemo, useState } from "react";
import type { ExerciseSummary } from "@/lib/types";
import { createCustomExercise, fetchExercises } from "@/lib/api";
import { Badge, Button } from "@/components/ui/primitives";

const GROUPS = [
  "All",
  "Chest",
  "Back",
  "Shoulders",
  "Biceps",
  "Triceps",
  "Quads",
  "Hamstrings",
  "Glutes",
  "Calves",
  "Core",
  "Forearms",
  "Calisthenics",
];

/**
 * Fast exercise search + add modal. Filters by group and name; supports
 * creating a custom exercise inline (expandable database, spec §2).
 */
export function ExercisePickerModal({
  onClose,
  onSelect,
}: {
  onClose: () => void;
  onSelect: (exerciseId: number) => void;
}) {
  const [all, setAll] = useState<ExerciseSummary[]>([]);
  const [group, setGroup] = useState("All");
  const [q, setQ] = useState("");
  const [showCustom, setShowCustom] = useState(false);
  const [customName, setCustomName] = useState("");
  const [customType, setCustomType] = useState("free_weight");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchExercises().then(setAll).catch(() => setAll([]));
  }, []);

  const filtered = useMemo(() => {
    let out = all;
    if (group !== "All")
      out = out.filter(
        (e) =>
          e.primary_muscle === group ||
          (group === "Legs" &&
            ["Quads", "Hamstrings", "Glutes", "Calves"].includes(
              e.primary_muscle ?? ""
            )) ||
          (group === "Arms" &&
            ["Biceps", "Triceps", "Forearms"].includes(e.primary_muscle ?? ""))
      );
    if (q) out = out.filter((e) => e.name.toLowerCase().includes(q.toLowerCase()));
    return out.slice(0, 80);
  }, [all, group, q]);

  async function createCustom() {
    if (!customName.trim()) return;
    setBusy(true);
    try {
      const created = await createCustomExercise({
        name: customName.trim(),
        exercise_type: customType,
        resistance:
          customType === "bodyweight"
            ? "bodyweight"
            : customType === "duration"
              ? "duration"
              : "external",
      });
      onSelect(created.id);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 sm:items-center"
      onClick={onClose}
      role="dialog"
      aria-modal
    >
      <div
        className="flex max-h-[85vh] w-full max-w-lg animate-fade-up flex-col rounded-t-2xl border border-border bg-surface sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-border p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-bold">Add exercise</h3>
            <button
              onClick={onClose}
              className="text-muted transition hover:text-foreground"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search exercises…"
            className="w-full rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-sm outline-none placeholder:text-muted/60 focus:border-accent/50"
          />
          <div className="mt-2 flex gap-1.5 overflow-x-auto pb-1">
            {GROUPS.map((g) => (
              <button
                key={g}
                onClick={() => setGroup(g)}
                className={`whitespace-nowrap rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${
                  group === g
                    ? "border-accent/60 text-accent"
                    : "border-border text-muted hover:text-foreground"
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {filtered.map((e) => (
            <button
              key={e.id}
              onClick={() => onSelect(e.id)}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left transition hover:bg-surface-2"
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{e.name}</div>
                <div className="text-[11px] text-muted">
                  {e.primary_muscle ?? "—"} · {e.exercise_type.replace(/_/g, " ")}
                </div>
              </div>
              {e.is_custom ? <Badge>custom</Badge> : null}
            </button>
          ))}
          {filtered.length === 0 ? (
            <div className="p-6 text-center text-sm text-muted">
              Nothing found. Add it as a custom exercise below.
            </div>
          ) : null}
        </div>

        <div className="border-t border-border p-3">
          {showCustom ? (
            <div className="space-y-2">
              <input
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder="Custom exercise name"
                className="w-full rounded-xl border border-border bg-surface-2 px-3 py-2 text-sm outline-none focus:border-accent/50"
              />
              <div className="flex gap-1.5">
                {["free_weight", "machine", "cable", "bodyweight", "duration"].map(
                  (t) => (
                    <button
                      key={t}
                      onClick={() => setCustomType(t)}
                      className={`rounded-lg border px-2 py-1 text-[11px] ${
                        customType === t
                          ? "border-accent/60 text-accent"
                          : "border-border text-muted"
                      }`}
                    >
                      {t.replace(/_/g, " ")}
                    </button>
                  )
                )}
              </div>
              <Button full onClick={createCustom} disabled={busy}>
                Create & add
              </Button>
            </div>
          ) : (
            <Button variant="ghost" full onClick={() => setShowCustom(true)}>
              + Create custom exercise
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
