/** TypeScript mirrors of the Iron Log FastAPI responses. Keep in sync. */

export type ExerciseType =
  | "bodyweight"
  | "free_weight"
  | "machine"
  | "cable"
  | "duration";

export type Resistance =
  | "bodyweight"
  | "bodyweight_weighted"
  | "external"
  | "duration";

export interface ExerciseSummary {
  id: number;
  name: string;
  exercise_type: ExerciseType;
  resistance: Resistance;
  dumbbell_pair: boolean;
  primary_muscle: string | null;
  is_custom: boolean;
  equipment_id: number | null;
}

export interface SetData {
  id?: number;
  set_number?: number;
  weight: number | null;
  per_dumbbell?: boolean | null;
  reps: number | null;
  duration: number | null;
  bodyweight: number | null;
  added_weight: number | null;
  effective_load?: number | null;
  volume?: number | null;
  machine_type?: string | null;
  machine_name?: string | null;
  rest_time?: number | null;
  tempo?: string | null;
  notes?: string | null;
}

export interface SessionExercise {
  workout_exercise_id: number;
  exercise_id: number;
  name: string;
  exercise_type: ExerciseType;
  resistance: Resistance;
  primary_muscle: string | null;
  notes: string | null;
  sets: SetData[];
}

export interface SessionSummary {
  id: number;
  name: string | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  volume: number;
  exercises: SessionExercise[];
}

export interface SetSuggestion {
  weight: number | null;
  reps: number | null;
  duration: number | null;
  bodyweight: number | null;
  added_weight: number | null;
}

export interface OverloadRecommendation {
  action:
    | "increase_weight"
    | "add_reps"
    | "maintain"
    | "deload"
    | "add_duration"
    | "progress_bodyweight";
  headline: string;
  detail: string;
  target: SetSuggestion[];
  confidence: string;
}

export interface PreviousPerformance {
  session_id: number;
  session_date: string;
  sets: SetData[];
  recommendation: OverloadRecommendation | null;
}

export interface StreakInfo {
  current_streak: number;
  longest_streak: number;
  last_workout_date: string | null;
  worked_out_today: boolean;
}

export interface Mission {
  code: string;
  description: string;
  progress: number;
  target: number;
  completed: boolean;
}

export interface NextTarget {
  exercise_id: number;
  exercise: string;
  action: string;
  headline: string;
  weight: number | null;
  reps: number | null;
  added_weight: number | null;
  bodyweight: number | null;
}

export interface RecentPR {
  exercise: string;
  exercise_id: number;
  category: string;
  weight: number | null;
  reps: number | null;
  added_weight: number | null;
  duration: number | null;
  achieved_at: string | null;
}

export interface DashboardData {
  greeting: string;
  date: string;
  streak: StreakInfo;
  todays_workout: {
    session_id: number;
    name: string | null;
    progress_exercises_done: number;
    progress_exercises_total: number;
  } | null;
  mission: Mission | null;
  missions: Mission[];
  next_target: NextTarget | null;
  recent_prs: RecentPR[];
  weekly_sessions: number;
  recommendations: string[];
}

export interface HistoryRow {
  id: number;
  name: string | null;
  date: string;
  exercises: number;
  sets: number;
  volume: number;
}

export interface ExerciseHistoryData {
  exercise: {
    id: number;
    name: string;
    exercise_type: ExerciseType;
    resistance: Resistance;
    dumbbell_pair: boolean;
    form_description: string | null;
    technique_tips: string | null;
    primary_muscle: string | null;
    secondary_muscles: string[];
  };
  bests: {
    heaviest_weight: number | null;
    most_reps: number | null;
    most_reps_weight: number | null;
    best_estimated_1rm: number | null;
    best_volume_set: number | null;
    best_volume_session: number | null;
    longest_duration: number | null;
  };
  totals: { sessions: number; sets: number; total_volume: number };
  sessions: { date: string; sets: SetData[] }[];
  series: SeriesPoint[];
  recommendation: OverloadRecommendation | null;
  prs: {
    category: string;
    value: number;
    weight: number | null;
    reps: number | null;
    added_weight: number | null;
    duration: number | null;
    achieved_at: string | null;
  }[];
}

export interface SeriesPoint {
  date: string;
  top_weight: number | null;
  top_reps: number | null;
  volume: number;
  sets: number;
  estimated_1rm: number | null;
}

export interface TemplateData {
  id: number;
  name: string;
  description: string | null;
  exercises: TemplateExerciseData[];
}

export interface TemplateExerciseData {
  id: number;
  exercise_id: number;
  name: string;
  position: number;
  sets: number;
  rep_range_min: number | null;
  rep_range_max: number | null;
  rest_seconds: number | null;
  notes: string | null;
}

export interface PRGroup {
  exercise_id: number;
  exercise: string;
  records: {
    category: string;
    value: number;
    weight: number | null;
    reps: number | null;
    added_weight: number | null;
    bodyweight: number | null;
    duration: number | null;
    achieved_at: string | null;
  }[];
}

export interface AnalyticsSummary {
  range: string;
  total_volume: number;
  total_reps: number;
  total_sets: number;
  sessions: number;
  avg_session_minutes: number;
}

export interface MuscleVolume {
  muscle_group: string;
  volume: number;
  share: number;
}

export interface HeatmapDay {
  date: string;
  workouts: number;
}

export interface Profile {
  id: number;
  name: string;
  email: string;
  bodyweight_kg: number | null;
  unit: "kg" | "lb";
  default_rest_seconds: number;
}

export interface CompleteSummary {
  session_id: number;
  duration_minutes: number;
  exercises: number;
  sets: number;
  volume: number;
  pr_count: number;
  new_prs: {
    exercise: string;
    category: string;
    weight: number | null;
    reps: number | null;
    added_weight: number | null;
    duration: number | null;
    value: number;
  }[];
  previous_volume: number;
  volume_delta: number;
  streak: StreakInfo;
}
