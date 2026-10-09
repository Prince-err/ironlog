/**
 * Central API client for the Iron Log frontend.
 *
 * ⚠️ DEVELOPMENT-ONLY IDENTITY ==========================================
 * The demo user id below is the development-only identity mechanism
 * (mirrors backend `X-Demo-User-ID`, auto-seeded as id 1). It provides NO
 * security and must be replaced by real auth before production. All
 * requests flow through this single module, so swapping in real auth is a
 * one-file change.
 * =======================================================================
 */

import type {
  AnalyticsSummary,
  CompleteSummary,
  DashboardData,
  ExerciseHistoryData,
  ExerciseSummary,
  HeatmapDay,
  HistoryRow,
  MuscleVolume,
  PreviousPerformance,
  PRGroup,
  Profile,
  SessionSummary,
  SetData,
  TemplateData,
} from "./types";

const BASE = "/api/v1";

/** Typed error so UI code can distinguish API failures from bugs. */
export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  init?: { method?: string; body?: unknown }
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: init?.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User-ID": "1", // development-only identity
    },
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
    cache: "no-store",
  });

  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new ApiError(detail, res.status);
  }
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

async function safeDetail(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
  } catch {
    // non-JSON error body — fall through
  }
  return `Request failed (${res.status})`;
}

// ---------------------------------------------------------------- dashboard

export function fetchDashboard(): Promise<DashboardData> {
  return request<DashboardData>("/dashboard");
}

export function fetchHeatmap(days = 182): Promise<HeatmapDay[]> {
  return request<HeatmapDay[]>(`/heatmap?days=${days}`);
}

// ---------------------------------------------------------------- exercises

export function fetchExercises(params?: {
  group?: string;
  type?: string;
  q?: string;
}): Promise<ExerciseSummary[]> {
  const sp = new URLSearchParams();
  if (params?.group) sp.set("group", params.group);
  if (params?.type) sp.set("type", params.type);
  if (params?.q) sp.set("q", params.q);
  const qs = sp.toString();
  return request<ExerciseSummary[]>(`/exercises${qs ? `?${qs}` : ""}`);
}

export function fetchExerciseHistory(
  exerciseId: number,
  range = "all"
): Promise<ExerciseHistoryData> {
  return request<ExerciseHistoryData>(
    `/exercises/${exerciseId}/history?range=${range}`
  );
}

export function fetchPreviousPerformance(
  exerciseId: number
): Promise<PreviousPerformance | null> {
  return request<PreviousPerformance | null>(`/exercises/${exerciseId}/previous`);
}

export function fetchMuscleGroups(): Promise<
  { id: number; slug: string; name: string }[]
> {
  return request("/muscle-groups");
}

export function createCustomExercise(payload: {
  name: string;
  exercise_type: string;
  resistance: string;
  primary_muscle_id?: number | null;
  dumbbell_pair?: boolean;
}): Promise<{ id: number; name: string }> {
  return request("/exercises", { method: "POST", body: payload });
}

// ----------------------------------------------------------------- sessions

export function fetchActiveSession(): Promise<SessionSummary | null> {
  return request<SessionSummary | null>("/sessions/active");
}

export function startSession(payload: {
  template_id?: number | null;
  name?: string | null;
  exercise_ids?: number[] | null;
}): Promise<SessionSummary> {
  return request("/sessions/start", { method: "POST", body: payload });
}

export function fetchSession(sessionId: number): Promise<SessionSummary> {
  return request<SessionSummary>(`/sessions/${sessionId}`);
}

export function addExercise(sessionId: number, exerciseId: number) {
  return request<{ workout_exercise_id: number }>(
    `/sessions/${sessionId}/exercises`,
    { method: "POST", body: { exercise_id: exerciseId } }
  );
}

export function removeExercise(
  sessionId: number,
  workoutExerciseId: number
): Promise<void> {
  return request(`/sessions/${sessionId}/exercises/${workoutExerciseId}`, {
    method: "DELETE",
  });
}

export function logSet(
  workoutExerciseId: number,
  payload: Partial<SetData>
): Promise<SetData> {
  return request(`/workout-exercises/${workoutExerciseId}/sets`, {
    method: "POST",
    body: payload,
  });
}

export function deleteSet(setId: number): Promise<void> {
  return request(`/sets/${setId}`, { method: "DELETE" });
}

export function completeSession(sessionId: number): Promise<CompleteSummary> {
  return request(`/sessions/${sessionId}/complete`, { method: "POST" });
}

// ----------------------------------------------------------------- history

export function fetchHistory(limit = 30): Promise<HistoryRow[]> {
  return request<HistoryRow[]>(`/history?limit=${limit}`);
}

// ----------------------------------------------------------------- PRs

export function fetchPRs(): Promise<PRGroup[]> {
  return request<PRGroup[]>("/prs");
}

// ----------------------------------------------------------------- templates

export function fetchTemplates(): Promise<TemplateData[]> {
  return request<TemplateData[]>("/templates");
}

export function fetchTemplatePrevious(
  templateId: number
): Promise<{
  session_id: number;
  date: string;
  name: string | null;
  exercises: {
    exercise_id: number;
    name: string;
    sets: SetData[];
  }[];
} | null> {
  return request(`/templates/${templateId}/previous`);
}

// ----------------------------------------------------------------- analytics

export function fetchAnalyticsSummary(range = "30d"): Promise<AnalyticsSummary> {
  return request<AnalyticsSummary>(`/analytics/summary?range=${range}`);
}

export function fetchMuscleVolumes(range = "30d"): Promise<MuscleVolume[]> {
  return request<MuscleVolume[]>(`/analytics/muscle-groups?range=${range}`);
}

export function fetchRecommendations(): Promise<{ recommendations: string[] }> {
  return request("/analytics/recommendations");
}

// ------------------------------------------------------------------ profile

export function fetchProfile(): Promise<Profile> {
  return request<Profile>("/me");
}

export function updateProfile(payload: {
  unit?: "kg" | "lb";
  name?: string;
  bodyweight_kg?: number;
  default_rest_seconds?: number;
}): Promise<Profile> {
  return request("/me", { method: "PUT", body: payload });
}
