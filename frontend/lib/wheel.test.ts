import { describe, expect, it } from "vitest";
import {
  durationOptions,
  formatClock,
  intRange,
  nearestIndex,
  parseClock,
  weightOptions,
  weightStep,
} from "./wheel";

describe("intRange", () => {
  it("builds inclusive integer ranges", () => {
    expect(intRange(0, 5)).toEqual([0, 1, 2, 3, 4, 5]);
    expect(intRange(1, 20)).toHaveLength(20);
    expect(intRange(0, 100)).toHaveLength(101);
  });
});

describe("weightStep", () => {
  it("uses fine steps for small weights and 2.5 for heavy", () => {
    expect(weightStep(0)).toBe(0.5);
    expect(weightStep(49)).toBe(0.5);
    expect(weightStep(50)).toBe(2.5);
  });
});

describe("weightOptions", () => {
  it("produces stepped values with trimmed labels", () => {
    const opts = weightOptions(0, 10, 2.5);
    expect(opts.map((o) => o.value)).toEqual([0, 2.5, 5, 7.5, 10]);
    expect(opts[1].label).toBe("2.5");
  });

  it("caps the number of options around 300", () => {
    const opts = weightOptions(0, 1000, 0.5);
    expect(opts.length).toBeLessThanOrEqual(300);
    const last = opts[opts.length - 1].value;
    expect((last - 0) % 0.5).toBeCloseTo(0, 10);
  });
});

describe("durationOptions", () => {
  it("includes the spec'd rest times", () => {
    const labels = durationOptions().map((o) => o.label);
    for (const want of ["0:15", "0:30", "0:45", "1:00", "1:30", "2:00", "2:30", "3:00", "3:30", "4:00", "5:00"]) {
      expect(labels).toContain(want);
    }
  });
});

describe("formatClock / parseClock", () => {
  it("formats seconds as m:ss", () => {
    expect(formatClock(95)).toBe("1:35");
    expect(formatClock(45)).toBe("0:45");
    expect(formatClock(600)).toBe("10:00");
  });

  it("parses m:ss and raw seconds", () => {
    expect(parseClock("1:30")).toBe(90);
    expect(parseClock("90")).toBe(90);
    expect(parseClock("")).toBeNull();
    expect(parseClock("x")).toBeNull();
  });
});

describe("nearestIndex", () => {
  it("snaps arbitrary values to the closest option", () => {
    const opts = weightOptions(50, 100, 2.5);
    expect(opts[nearestIndex(opts, 62.3)].value).toBe(62.5);
    expect(opts[nearestIndex(opts, 62.5)].value).toBe(62.5);
    expect(opts[nearestIndex(opts, 55)].value).toBe(55);
  });

  it("clamps below the first option", () => {
    const reps = intRange(0, 100).map((v) => ({ value: v, label: String(v) }));
    expect(nearestIndex(reps, -5)).toBe(0);
    expect(nearestIndex(reps, 500)).toBe(100);
  });
});
