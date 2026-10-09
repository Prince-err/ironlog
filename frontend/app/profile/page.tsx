"use client";

import { useEffect, useState } from "react";
import type { Profile } from "@/lib/types";
import { fetchProfile, updateProfile } from "@/lib/api";
import { kgToDisplay, trim } from "@/lib/format";
import {
  Button,
  Card,
  ErrorState,
  SectionTitle,
  Skeleton,
} from "@/components/ui/primitives";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [name, setName] = useState("");
  const [bodyweight, setBodyweight] = useState("");

  useEffect(() => {
    fetchProfile()
      .then((p) => {
        setProfile(p);
        setName(p.name);
        setBodyweight(
          p.bodyweight_kg != null ? String(trim(p.bodyweight_kg)) : ""
        );
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load profile")
      );
  }, []);

  async function save(patch: {
    unit?: "kg" | "lb";
    name?: string;
    bodyweight_kg?: number;
    default_rest_seconds?: number;
  }) {
    setSaved(false);
    try {
      const updated = await updateProfile(patch);
      setProfile(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    }
  }

  if (error) return <ErrorState message={error} />;
  if (!profile) return <Skeleton className="mt-4 h-64" />;

  return (
    <div className="space-y-3 pt-2">
      <h1 className="text-2xl font-bold">Profile</h1>

      <Card className="space-y-3">
        <label className="block">
          <span className="text-[11px] font-medium uppercase tracking-wider text-muted">
            Name
          </span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-sm outline-none focus:border-accent/50"
          />
        </label>
        <div className="flex items-center justify-between">
          <span className="text-sm">Units</span>
          <div className="flex gap-1.5">
            {(["kg", "lb"] as const).map((u) => (
              <button
                key={u}
                onClick={() => save({ unit: u })}
                className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                  profile.unit === u
                    ? "border-accent/60 text-accent"
                    : "border-border text-muted hover:text-foreground"
                }`}
              >
                {u}
              </button>
            ))}
          </div>
        </div>
        <p className="text-[11px] text-muted">
          Stored data always stays in kg — the unit choice changes display only.
        </p>
        <Button
          onClick={() => save({ name })}
          className="w-full"
          disabled={name === profile.name}
        >
          {saved ? "Saved ✓" : "Save name"}
        </Button>
      </Card>

      <SectionTitle>Bodyweight</SectionTitle>
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted">Latest</span>
          <span className="tabular text-lg font-bold">
            {profile.bodyweight_kg != null
              ? `${trim(kgToDisplay(profile.bodyweight_kg, profile.unit))} ${profile.unit}`
              : "—"}
          </span>
        </div>
        <label className="block">
          <span className="text-[11px] font-medium uppercase tracking-wider text-muted">
            Update today&apos;s bodyweight (kg)
          </span>
          <input
            inputMode="decimal"
            value={bodyweight}
            onChange={(e) => setBodyweight(e.target.value)}
            placeholder="e.g. 78.4"
            className="tabular mt-1 w-full rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-sm outline-none focus:border-accent/50"
          />
        </label>
        <Button
          full
          onClick={() => {
            const v = parseFloat(bodyweight);
            if (v > 0) save({ bodyweight_kg: v });
          }}
          disabled={!parseFloat(bodyweight)}
        >
          Log bodyweight
        </Button>
        <p className="text-[11px] text-muted">
          Used for bodyweight lifts (pull-ups, dips) so history stays comparable
          as your weight changes.
        </p>
      </Card>

      <SectionTitle>About</SectionTitle>
      <Card className="space-y-1.5 text-xs text-muted">
        <p>
          Iron Log — progressive overload, history, PRs, streaks and missions.
        </p>
        <p>
          Estimated 1RM values are calculated (Epley), not measured. Volume is
          weight × reps — a training-load indicator, not a measure of muscle
          growth.
        </p>
      </Card>
    </div>
  );
}
