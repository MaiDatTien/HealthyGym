/* Kiểu dữ liệu dùng chung cho phân hệ AI Smart Coach & Tiến độ. */

export type Gender = "male" | "female";

export interface Diagnosis {
  height_cm: number;
  weight_kg: number;
  body_fat_percentage: number;
  body_fat_source?: string;
  age?: number | null;
  gender: string;
  bmi: number;
  bmi_category: string;
  lean_body_mass_kg: number;
  fat_mass_kg: number;
  bmr_kcal: number;
  tdee_kcal: number;
  activity_multiplier: number;
  activity_label: string;
  body_fat_category: string;
  body_fat_category_vi: string;
  ffmi: number;
  ffmi_normalized: number;
  ffmi_interpretation: string;
  muscle_quality: string;
  body_type: string;
  body_type_classification: string;
  ai_assessment_summary: string;
  estimated_weeks_to_goal: number;
  estimated_months_to_goal?: number;
  target_body_fat_percentage: number;
  fat_to_lose_kg: number;
  muscle_to_gain_kg: number;
  weekly_fat_loss_target_kg: number;
  safety_warnings: string[];
}

export interface Macros {
  protein_grams: number;
  carbs_grams: number;
  fat_grams: number;
  protein_kcal: number;
  carbs_kcal: number;
  fat_kcal: number;
  protein_percent: number;
  carbs_percent: number;
  fat_percent: number;
  protein_per_kg: number;
  protein_per_kg_lbm: number;
  total_calories: number;
}

export interface Meal {
  meal_name: string;
  time: string;
  foods: string[];
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  tip?: string;
}

export interface NutritionPlan {
  target_daily_calories: number;
  caloric_adjustment: number;
  tdee_kcal: number;
  bmr_kcal: number;
  caloric_strategy: string;
  macros: Macros;
  macro_guidance: { protein: string; fat: string; carbs: string };
  sample_meals: Meal[];
  meal_substitutions: string[];
  daily_water_liters: number;
  water_plan: {
    base_liters: number;
    training_bonus_liters: number;
    total_liters: number;
    glasses_250ml: number;
    schedule: string[];
  };
  eating_rules: string[];
  foods_to_prioritize: string[];
  foods_to_limit: string[];
}

export interface Exercise {
  name: string;
  target_muscle: string;
  movement: string;
  type: string;
  sets: number;
  reps: string;
  rest_seconds: number;
  rpe: string;
  notes: string;
}

export interface Session {
  day: string;
  focus: string;
  warmup: string;
  exercises: Exercise[];
  cooldown: string;
  estimated_minutes: number;
}

export interface WorkoutPlan {
  split_type: string;
  split_rationale: string;
  training_days_per_week: number;
  session_minutes: number;
  training_location: string;
  progression_rule: string;
  rep_guidance: string;
  rest_guidance: string;
  target_rpe: string;
  volume_note: string;
  sessions: Session[];
  cardio: {
    type: string;
    weekly_sessions: number;
    details: string[];
    low_impact_note: string;
  };
  exercise_substitutions: string[];
  extra_notes: string[];
  weekly_structure: string;
}

export interface Supplement {
  name: string;
  dose: string;
  when: string;
  why: string;
  priority: string;
}

export interface RecoveryPlan {
  recommended_sleep_hours: string;
  ideal_bedtime: string;
  wake_time: string;
  sleep_protocol: string[];
  rest_days: string[];
  training_days: string[];
  active_recovery_tips: string[];
  neat_target_steps: number;
  supplements: Supplement[];
  overtraining_warning_signs: string[];
  stress_management: string[];
}

export interface FullPlan {
  plan_id?: number;
  metric_id?: number;
  goal: string;
  goal_label: string;
  created_at?: string;
  member_diagnosis: Diagnosis;
  nutrition_plan: NutritionPlan;
  workout_schedule: WorkoutPlan;
  recovery_protocol: RecoveryPlan;
  summary_text: string;
  disclaimer: string;
  safety_warnings?: string[];
  saved_to_profile?: boolean;
}

export interface OnboardingStep {
  step: number;
  field: string;
  question: string;
  hint?: string;
  input_type: "choice" | "number" | "hybrid" | "multi";
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
}

export interface OnboardingFlow {
  total_steps: number;
  required_fields: string[];
  steps: OnboardingStep[];
}

export interface TrainerSlotItem {
  id: number;
  trainer_id: number;
  trainer_name: string;
  trainer_specialty: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  is_booked: boolean;
  session_date: string;
  time_label: string;
}

export interface ProgressCharts {
  labels: string[];
  series: {
    weight_kg: (number | null)[];
    body_fat_percentage: (number | null)[];
    muscle_mass_kg: (number | null)[];
    lean_body_mass_kg: (number | null)[];
    fat_mass_kg: (number | null)[];
    bmi: (number | null)[];
  };
  delta: {
    weight_kg?: number;
    body_fat_percentage?: number;
    muscle_mass_kg?: number;
    fat_mass_kg?: number;
  };
  total_records: number;
  motivation: string;
  target: {
    plan_id: number;
    target_body_fat_percentage: number;
    fat_to_lose_kg: number;
    target_daily_calories: number;
    protein_grams: number;
    estimated_weeks_to_goal: number;
  } | null;
}

export interface ProgressSummary {
  latest_metric: {
    measured_at: string;
    weight_kg: number;
    body_fat_percentage: number;
    muscle_mass_kg: number;
    bmi: number;
    tdee_kcal: number;
    body_type: string;
  } | null;
  start_metric: { measured_at: string; weight_kg: number; body_fat_percentage: number } | null;
  total_change: { weight_kg: number; body_fat_percentage: number };
  last_30_days: {
    checkin_days: number;
    avg_calories_in: number;
    avg_protein_g: number;
    avg_water_liters: number;
    avg_sleep_hours: number;
    avg_steps: number;
    workout_sessions_logged: number;
    total_workout_minutes: number;
  };
  active_target: {
    target_daily_calories: number;
    protein_grams: number;
    daily_water_liters: number;
    training_days_per_week: number;
  } | null;
}

export interface WorkoutLogEntry {
  id: number;
  log_date: string;
  session_focus: string | null;
  exercise_name: string;
  target_muscle: string | null;
  sets: number | null;
  reps: number | null;
  weight_kg: number | null;
  rpe: number | null;
  duration_minutes: number | null;
  volume_kg: number;
  notes: string | null;
}

/* --- Nhãn hiển thị tiếng Việt --- */
export const BODY_TYPE_LABELS: Record<string, string> = {
  skinny_fat: "Skinny Fat",
  obese: "Béo phì",
  overweight: "Thừa cân",
  athletic: "Vận động viên",
  lean: "Gọn gàng",
  skinny: "Gầy",
  average: "Trung bình",
};

export const GOAL_LABELS_SHORT: Record<string, string> = {
  cutting: "Giảm mỡ",
  bulking: "Tăng cơ",
  recomp: "Tái cấu trúc",
  endurance: "Sức bền",
};