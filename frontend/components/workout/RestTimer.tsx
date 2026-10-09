"use client";

import { useEffect, useRef, useState } from "react";
import { formatTimer } from "@/lib/format";
import { durationOptions } from "@/lib/wheel";
import { Button } from "@/components/ui/primitives";
import { WheelPickerSheet } from "@/components/ui/WheelPickerSheet";

/**
 * Rest timer (spec §4): countdown with pause/resume and ±15s nudges.
 * Vibrates on completion where supported.
 */
export function RestTimer({ defaultSeconds = 90 }: { defaultSeconds?: number }) {
  const [total, setTotal] = useState(defaultSeconds);
  const [remaining, setRemaining] = useState(defaultSeconds);
  const [running, setRunning] = useState(false);
  const [restPickerOpen, setRestPickerOpen] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const restOpts = durationOptions();

  useEffect(() => {
    if (running && remaining > 0) {
      intervalRef.current = setInterval(() => {
        setRemaining((r) => {
          if (r <= 1) {
            setRunning(false);
            if (typeof navigator !== "undefined" && "vibrate" in navigator) {
              navigator.vibrate?.([120, 60, 120]);
            }
            return 0;
          }
          return r - 1;
        });
      }, 1000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [running, remaining]);

  const pct = total > 0 ? 1 - remaining / total : 0;
  const R = 26;
  const C = 2 * Math.PI * R;

  return (
    <div className="card flex items-center gap-4 p-4">
      <div className="relative h-16 w-16 shrink-0">
        <svg viewBox="0 0 64 64" className="h-full w-full -rotate-90">
          <circle cx="32" cy="32" r={R} fill="none" stroke="var(--surface-2)" strokeWidth="6" />
          <circle
            cx="32"
            cy="32"
            r={R}
            fill="none"
            stroke={remaining === 0 ? "var(--success)" : "var(--accent)"}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={C}
            strokeDashoffset={C * (1 - pct)}
            className="transition-all duration-500"
          />
        </svg>
        <span className="tabular absolute inset-0 flex items-center justify-center text-sm font-bold">
          {formatTimer(remaining)}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2">
        <div className="flex items-center gap-2">
          <Button
            variant={running ? "secondary" : "primary"}
            className="flex-1 py-2"
            onClick={() => {
              if (remaining === 0) setRemaining(total);
              setRunning((r) => !r);
            }}
          >
            {remaining === 0 ? "Restart" : running ? "Pause" : "Start rest"}
          </Button>
          <Button
            variant="ghost"
            className="px-2 py-2"
            onClick={() => {
              setTotal((t) => Math.max(15, t + 15));
              setRemaining((r) => r + 15);
            }}
            aria-label="Add 15 seconds"
          >
            +15s
          </Button>
          <Button
            variant="ghost"
            className="px-2 py-2"
            onClick={() => {
              setTotal((t) => Math.max(15, t - 15));
              setRemaining((r) => Math.max(0, r - 15));
            }}
            aria-label="Subtract 15 seconds"
          >
            −15s
          </Button>
        </div>
        <div className="flex items-center gap-1.5">
          {[60, 90, 120, 180].map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setTotal(s);
                setRemaining(s);
                setRunning(false);
              }}
              className={`rounded-lg border px-2 py-1 text-[11px] font-medium transition ${
                total === s
                  ? "border-accent/50 text-accent"
                  : "border-border text-muted hover:text-foreground"
              }`}
            >
              {s / 60}m
            </button>
          ))}
          <button
            type="button"
            onClick={() => setRestPickerOpen(true)}
            className="tabular ml-auto rounded-lg border border-border px-2 py-1 text-[11px] font-semibold text-muted transition hover:border-accent/50 hover:text-accent"
            aria-label={`Rest time ${formatTimer(total)}. Tap to pick exact time.`}
          >
            {formatTimer(total)}
          </button>
        </div>

        <WheelPickerSheet
          open={restPickerOpen}
          title="Rest time"
          options={restOpts}
          value={total}
          onChange={(v) => {
            setTotal(v);
            setRemaining(v);
            setRunning(false);
            setRestPickerOpen(false);
          }}
          onClose={() => setRestPickerOpen(false)}
        />
      </div>
    </div>
  );
}
