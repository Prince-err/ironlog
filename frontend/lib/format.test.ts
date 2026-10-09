import { describe, expect, it } from "vitest";
import {
  formatDuration,
  formatLoad,
  formatPRValue,
  formatSetCompact,
  formatTimer,
  formatVolume,
  kgToDisplay,
  displayToKg,
} from "./format";

describe("formatLoad", () => {
  it("shows per-dumbbell weights distinctly (spec §3 Type B)", () => {
    expect(formatLoad({ weight: 20, per_dumbbell: true })).toContain("× 2 DB");
  });

  it("shows barbell weight as total", () => {
    expect(formatLoad({ weight: 80 })).toBe("80 kg");
  });

  it("shows added weight with + prefix", () => {
    expect(formatLoad({ added_weight: 10 })).toBe("+10 kg");
  });

  it("shows duration in seconds", () => {
    expect(formatLoad({ duration: 45 })).toBe("45s");
  });
});

describe("formatSetCompact", () => {
  it("formats weight × reps", () => {
    expect(
      formatSetCompact({ weight: 80, reps: 8, duration: null, bodyweight: null, added_weight: null })
    ).toContain("80 kg × 8");
  });
});

describe("volume formatting", () => {
  it("abbreviates thousands", () => {
    expect(formatVolume(12450)).toContain("k kg");
  });
});

describe("timers", () => {
  it("formats mm:ss", () => {
    expect(formatTimer(90)).toBe("1:30");
  });
  it("formats duration minutes", () => {
    expect(formatDuration(67)).toBe("1h 07m");
  });
});

describe("unit conversion (spec §20)", () => {
  it("kg -> lb", () => {
    expect(kgToDisplay(80, "lb")).toBeCloseTo(176.37, 1);
  });
  it("kg stays kg", () => {
    expect(kgToDisplay(80, "kg")).toBe(80);
  });
  it("lb -> kg roundtrip", () => {
    expect(displayToKg(kgToDisplay(80, "lb"), "lb")).toBeCloseTo(80, 0);
  });
});

describe("PR labels", () => {
  it("labels estimated 1RM as estimate (spec §25)", () => {
    expect(formatPRValue({ category: "best_1rm", value: 116.7, weight: 100, reps: 5, added_weight: null, duration: null })).toContain("est");
  });
  it("labels highest added weight with +", () => {
    expect(formatPRValue({ category: "highest_added_weight", value: 10, weight: null, reps: 8, added_weight: 10, duration: null })).toBe("+10 kg");
  });
});
