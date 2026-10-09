"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { nearestIndex, type WheelOption } from "@/lib/wheel";
import { Button } from "@/components/ui/primitives";

const ITEM_H = 44; // px per wheel row
const VISIBLE = 5; // rows visible (including center)

/**
 * Configurable wheel picker, presented as a bottom sheet (spec §11, §14).
 *
 * Interaction: swipe/scroll to move, values snap to the center; tap a value
 * to select it; ArrowUp/ArrowDown step; Enter = Done; Escape closes.
 * Works with touch swipe, mouse wheel, trackpad and mouse dragging.
 *
 * One configurable component serves weight (step + unit), reps, sets and
 * duration via `options`/`unit` props — no duplicated per-type pickers.
 */
export function WheelPickerSheet({
  open,
  title,
  options,
  value,
  onChange,
  onClose,
  unit,
}: {
  open: boolean;
  title: string;
  options: WheelOption[];
  value: number | null;
  onChange: (v: number) => void;
  onClose: () => void;
  unit?: string;
}) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [centered, setCentered] = useState(() =>
    value != null ? nearestIndex(options, value) : 0
  );
  const [dragging, setDragging] = useState(false);
  const programmatic = useRef(false);
  const settleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dragRef = useRef<{ startY: number; startTop: number } | null>(null);

  // Re-center on open / external value change — render-time adjustment
  // (React's recommended alternative to setState-inside-effect).
  const syncKey = `${open}:${value ?? ""}:${options.length}`;
  const [prevSync, setPrevSync] = useState(syncKey);
  if (prevSync !== syncKey) {
    setPrevSync(syncKey);
    setCentered(value != null ? nearestIndex(options, value) : 0);
  }
  const idxRef = useRef(centered);

  // Keep idxRef fresh (runs before the positioning effect below).
  useEffect(() => {
    idxRef.current = centered;
  }, [centered]);

  // Position the scroll column whenever the sheet opens (DOM only).
  useEffect(() => {
    if (!open) return;
    const el = scrollRef.current;
    if (el) {
      programmatic.current = true;
      el.scrollTop = idxRef.current * ITEM_H;
      requestAnimationFrame(() => {
        programmatic.current = false;
      });
    }
  }, [open]);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el || programmatic.current) return;
    const idx = Math.max(
      0,
      Math.min(options.length - 1, Math.round(el.scrollTop / ITEM_H))
    );
    setCentered(idx);
    // after momentum ends, glide exactly onto the row
    if (settleTimer.current) clearTimeout(settleTimer.current);
    settleTimer.current = setTimeout(() => {
      programmatic.current = true;
      el.scrollTo({ top: idx * ITEM_H, behavior: "smooth" });
      requestAnimationFrame(() => {
        programmatic.current = false;
      });
    }, 130);
  }, [options.length]);

  const scrollToIndex = useCallback((idx: number, smooth = true) => {
    const el = scrollRef.current;
    setCentered(idx);
    if (el) {
      programmatic.current = true;
      el.scrollTo({ top: idx * ITEM_H, behavior: smooth ? "smooth" : "auto" });
      requestAnimationFrame(() => {
        programmatic.current = false;
      });
    }
  }, []);

  const commitAndClose = useCallback(() => {
    const opt = options[centered];
    if (opt) onChange(opt.value);
    onClose();
  }, [options, centered, onChange, onClose]);

  // keyboard: arrows step, Enter confirms, Escape cancels
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowUp" || e.key === "ArrowDown") {
        e.preventDefault();
        setCentered((c) => {
          const next = Math.max(
            0,
            Math.min(options.length - 1, c + (e.key === "ArrowUp" ? -1 : 1))
          );
          scrollToIndex(next);
          return next;
        });
      } else if (e.key === "Enter") {
        e.preventDefault();
        commitAndClose();
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, options.length, commitAndClose, onClose, scrollToIndex]);

  // mouse drag (desktop parity with touch swipe)
  function onMouseDown(e: React.MouseEvent) {
    const el = scrollRef.current;
    if (!el) return;
    dragRef.current = { startY: e.clientY, startTop: el.scrollTop };
    setDragging(true);
  }

  useEffect(() => {
    if (!dragging) return;
    function onMove(e: MouseEvent) {
      const el = scrollRef.current;
      const d = dragRef.current;
      if (!el || !d) return;
      el.scrollTop = d.startTop - (e.clientY - d.startY);
    }
    function onUp() {
      setDragging(false);
      dragRef.current = null;
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragging]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      {/* backdrop */}
      <button
        aria-label="Close picker"
        tabIndex={-1}
        className="absolute inset-0 bg-black/60 backdrop-blur-[2px] animate-fade-in"
        onClick={onClose}
      />

      <div className="animate-sheet-up relative w-full max-w-lg rounded-t-3xl border-t border-border bg-surface px-4 pt-2 pb-[max(env(safe-area-inset-bottom),1rem)]">
        <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-border" />
        <div className="mb-1 text-center text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          {title}
        </div>

        <div className="relative">
          {/* center selection band */}
          <div
            aria-hidden
            className="pointer-events-none absolute left-0 right-0 top-1/2 -translate-y-1/2 rounded-xl border border-accent/30 bg-accent/5"
            style={{ height: ITEM_H }}
          />

          <div
            ref={scrollRef}
            role="listbox"
            aria-label={title}
            tabIndex={0}
            className="no-scrollbar relative cursor-grab overflow-y-auto overscroll-contain focus:outline-none"
            style={{ height: VISIBLE * ITEM_H, scrollSnapType: "y mandatory" }}
            onScroll={handleScroll}
            onMouseDown={onMouseDown}
          >
            {Array.from({ length: (VISIBLE - 1) / 2 }).map((_, i) => (
              <div key={`pt-${i}`} aria-hidden style={{ height: ITEM_H }} />
            ))}

            {options.map((opt, i) => {
              const dist = Math.abs(i - centered);
              const isCenter = dist === 0;
              return (
                <div
                  key={opt.value}
                  role="option"
                  aria-selected={isCenter}
                  style={{ height: ITEM_H, scrollSnapAlign: "center" }}
                  onClick={() => {
                    scrollToIndex(i);
                    onChange(opt.value);
                  }}
                  className={`tabular flex select-none items-center justify-center transition-all duration-150 ${
                    dragging ? "cursor-grabbing" : "cursor-pointer"
                  }`}
                >
                  <span
                    className={
                      isCenter
                        ? "text-4xl font-bold text-accent"
                        : dist === 1
                          ? "text-xl font-semibold text-foreground/55"
                          : dist === 2
                            ? "text-lg text-muted/45"
                            : "text-base text-muted/25"
                    }
                  >
                    {opt.label}
                  </span>
                  {isCenter && unit ? (
                    <span className="ml-2 text-lg font-semibold text-foreground/80">
                      {unit}
                    </span>
                  ) : null}
                </div>
              );
            })}

            {Array.from({ length: (VISIBLE - 1) / 2 }).map((_, i) => (
              <div key={`pb-${i}`} aria-hidden style={{ height: ITEM_H }} />
            ))}
          </div>
        </div>

        <Button full className="mt-3 py-3 text-base" onClick={commitAndClose}>
          Done
        </Button>
      </div>
    </div>
  );
}
