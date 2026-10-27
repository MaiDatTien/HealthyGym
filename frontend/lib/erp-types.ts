/* ==========================================================================
   ERP v3 — Kiểu dữ liệu cho 6 vai trò và 7 phân hệ nghiệp vụ.
   Tách riêng khỏi types.ts (AI/tiến độ) để dễ bảo trì.
   ========================================================================== */

export type Role =
  | "member"
  | "trainer"
  | "receptionist"
  | "facility_manager"
  | "admin"
  | "staff";

/* --- Vòng đời hợp đồng --- */
export interface Contract {
  id: number;
  contract_code: string;
  plan_name: string | null;
  tier: string;
  time_window: string;
  status: string;
  start_date: string;
  end_date: string;
  days_remaining: number;
  final_price: number;
  paid_amount: number;
  payment_status: string;
  prorated_value: number;
  freeze_days_used: number;
  benefits: {
    locker: boolean;
    towel: boolean;
    sauna: boolean;
    guest_passes_month: number;
  };
}

export interface Installment {
  id: number;
  sequence: number;
  amount: number;
  paid_amount: number;
  remaining: number;
  due_date: string;
  status: string;
  days_overdue: number;
  note: string | null;
}

export interface UpgradeQuote {
  current_contract: {
    contract_code: string;
    plan_name: string | null;
    end_date: string;
    days_remaining: number;
    duration_days: number;
    paid_amount: number;
  };
  new_plan: {
    id: number;
    name: string;
    duration_days: number;
    price: number;
    tier: string;
  };
  prorated_credit: number;
  amount_due: number;
  explanation: string;
  savings_note: string;
}

/* --- Gói PT --- */
export interface PTPackageItem {
  id: number;
  name: string;
  sessions: number;
  price: number;
  price_per_session: number;
  validity_days: number;
  tier: string;
  includes_inbody: boolean;
  includes_nutrition: boolean;
  description: string | null;
}

export interface MyPTPackage {
  id: number;
  package_name: string | null;
  trainer_name: string | null;
  sessions_total: number;
  sessions_used: number;
  sessions_remaining: number;
  usage_percent: number;
  start_date: string;
  expiry_date: string;
  days_remaining: number;
  status: string;
  warning: string | null;
}

export interface BurnPendingItem {
  booking_id: number;
  member_name: string | null;
  trainer_marked_at: string | null;
  member_checked_in: boolean;
  member_confirmed: boolean;
  status: string;
}

/* --- GroupX --- */
export interface ClassScheduleItem {
  id: number;
  class_name: string | null;
  category: string | null;
  description: string | null;
  studio: string;
  start_time: string;
  end_time: string;
  difficulty: string;
  capacity: number;
  enrolled_count: number;
  available_spots: number;
  fill_percent: number;
  is_full: boolean;
  waitlist_count: number;
  trainer_name: string;
  is_substituted: boolean;
  requires_spot_selection: boolean;
  spot_layout: string;
}

export interface ClassSpotMap {
  zone: string;
  spots: { id: number; spot_code: string; is_available: boolean }[];
}

export interface ClassScheduleDetail {
  id: number;
  class_name: string | null;
  studio: string;
  start_time: string;
  end_time: string;
  difficulty: string;
  capacity: number;
  enrolled_count: number;
  available_spots: number;
  trainer_name: string;
  trainer_specialty: string | null;
  requires_spot_selection: boolean;
  spot_layout: string;
  spot_map: ClassSpotMap[];
  note: string | null;
}

export interface MyClassBooking {
  booking_id: number;
  class_name: string | null;
  category: string | null;
  start_time: string | null;
  end_time: string | null;
  studio: string | null;
  status: string;
  spot_code: string | null;
  promoted_from_waitlist: boolean;
  checked_in_at: string | null;
  rating: number | null;
}

export interface PenaltyInfo {
  is_blocked: boolean;
  blocked_until: string | null;
  reason: string | null;
  no_show_count_this_month: number;
  no_show_limit: number;
  remaining_before_block: number;
  warning: string | null;
  advice: string;
}

/* --- Vận hành cổng & tủ đồ --- */
export interface GateScanResult {
  granted: boolean;
  result: string;
  member_name: string;
  member_id?: number;
  tier?: string;
  time_window?: string;
  reason: string | null;
  checks: Record<string, unknown>;
  warnings: string[];
  off_peak_violation: boolean;
  surcharge_amount: number;
  upcoming_pt_session: {
    trainer_name: string | null;
    start_time: string;
    minutes_until: number;
  } | null;
  upcoming_class: {
    class_name: string | null;
    start_time: string;
    minutes_until: number;
  } | null;
  points_awarded: number;
  loyalty_points: number;
  is_trial?: boolean;
  message: string;
}

export interface DynamicQR {
  qr_token: string;
  issued_at: string;
  expires_at: string;
  ttl_seconds: number;
  member_name: string;
  tier: string;
  time_window: string;
  status: string;
  note: string;
}

export interface LockerStatus {
  total: number;
  available: number;
  occupied: number;
  lockers: {
    code: string;
    zone: string;
    kind: string;
    is_available: boolean;
    monthly_fee: number | null;
    holder: string | null;
    assigned_at: string | null;
  }[];
}

/* --- POS & kho --- */
export interface ProductItem {
  id: number;
  sku: string;
  name: string;
  category: string;
  brand: string | null;
  unit: string;
  price: number;
  serving_price: number;
  servings_per_unit: number;
  cost_price?: number;
  stock_quantity: number;
  low_stock_threshold: number;
  is_low_stock: boolean;
  expiry_date: string | null;
  days_to_expiry: number | null;
  expiry_warning: string | null;
  can_sell_by_serving: boolean;
}

export interface PosOrderRow {
  id: number;
  order_code: string;
  customer_name: string | null;
  total_amount: number;
  profit: number;
  payment_method: string;
  cashier: string | null;
  item_count: number;
  created_at: string;
}

/* --- Gamification & CRM --- */
export interface StreakInfo {
  current_week_streak: number;
  longest_week_streak: number;
  current_day_streak: number;
  longest_day_streak: number;
  this_week_visits: number;
  total_checkins: number;
  total_workouts_logged: number;
  streak_broken: boolean;
  next_milestone: { weeks: number; remaining: number; reward_hint: string } | null;
  loyalty_points: number;
  badges_earned: number;
  badges: {
    code: string | null;
    name: string | null;
    category: string | null;
    earned_at: string;
    description: string | null;
  }[];
  motivation: string;
}

export interface LeaderboardRow {
  rank: number;
  medal: string | null;
  member_id: number;
  member_name: string;
  tier: string;
  value: number;
  unit: string;
}

export interface RewardItem {
  id: number;
  name: string;
  description: string | null;
  points_cost: number;
  kind: string;
  value_amount: number;
  stock: number;
  in_stock: boolean;
}

export interface PointsInfo {
  current_points: number;
  total_earned: number;
  points_value_note: string;
  by_source: { kind: string; label: string; points: number }[];
  history: {
    points: number;
    balance_after: number;
    kind: string;
    label: string;
    note: string | null;
    created_at: string;
  }[];
  how_to_earn: string[];
}

export interface ChallengeItem {
  id: number;
  name: string;
  description: string | null;
  kind: string;
  start_date: string;
  end_date: string;
  days_remaining: number;
  max_participants: number;
  participants: number;
  entry_fee: number;
  prize_description: string | null;
  reward_points: number;
  is_open: boolean;
}

export interface RetentionTaskItem {
  id: number;
  member_id: number;
  member_name: string | null;
  member_phone: string | null;
  kind: string;
  priority: string;
  title: string;
  detail: string | null;
  suggested_action: string | null;
  assigned_to: string | null;
  status: string;
  created_at: string;
  outcome: string | null;
}

export interface ChurnReport {
  snapshot_date: string | null;
  total_members: number;
  active_members: number;
  risk_distribution: Record<string, number>;
  at_risk_total: number;
  retention_rate: number;
  churn_rate: number;
  renewed_members: number;
  churned_members: number;
  interpretation: string;
  top_risk_members: {
    member_id: number;
    member_name: string | null;
    phone: string | null;
    days_since_last_visit: number;
    visits_last_30d: number;
    risk_score: number;
    risk_level: string;
    factors: string[];
  }[];
}

/* --- CRM khách tập thử --- */
export interface LeadItem {
  id: number;
  full_name: string;
  phone: string;
  email: string | null;
  source: string;
  stage: string;
  assigned_to: string | null;
  trial_pass_id: number | null;
  first_visit_at: string | null;
  inbody_done_at: string | null;
  consultation_note: string | null;
  lost_reason: string | null;
  created_at: string;
  days_since_created: number;
}

/* --- Thiết bị --- */
export interface EquipmentItem {
  id: number;
  name: string;
  category: string;
  quantity: number;
  brand: string | null;
  model: string | null;
  branch_id: number | null;
  lifecycle_status: string;
  lifecycle_label: string;
  display_status: string;
  open_maintenance_tickets: number;
  last_maintenance_date: string | null;
  next_maintenance_date: string | null;
  maintenance_cycle_days: number;
  days_to_maintenance: number | null;
  maintenance_due: boolean;
  maintenance_warning: string | null;
  is_usable: boolean;
}

export interface MachineQRInfo {
  machine_code: string;
  display_name: string;
  facility_name: string | null;
  category: string | null;
  brand: string | null;
  model: string | null;
  lifecycle_status: string | null;
  is_usable: boolean;
  status_warning: string | null;
  open_tickets: number;
  video_url: string | null;
  setup_guide: string | null;
  posture_guide: string | null;
  common_mistakes: string | null;
  target_muscles: string | null;
  difficulty: string;
  linked_exercise: string | null;
  ai_tip: string;
  report_hint: string;
}

/* --- AI nâng cao --- */
export interface PARQResult {
  screening_id: number | null;
  saved: boolean;
  risk_level: string;
  parq_positive: boolean;
  needs_medical_clearance: boolean;
  clearance_note: string | null;
  blocked_from_training: boolean;
  contraindications: string[];
  contraindication_labels: string[];
  safe_exercise_notes: string[];
  flags: string[];
  next_step: string;
  applied_hard_rules: string[];
}

export interface InBodyAnalysis {
  record_id: number | null;
  saved: boolean;
  shape: { type: string; description: string; rationale: string };
  visceral_fat: { level: number | null; status: string; is_warning: boolean };
  whr: { value: number | null; status: string | null };
  smm_ratio: { value: number | null; status: string | null };
  segmental_analysis: {
    has_data: boolean;
    arm_difference_kg: number;
    arm_difference_percent: number;
    leg_difference_kg: number;
    leg_difference_percent: number;
    balance_score: number;
    imbalances: {
      type: string;
      severity: string;
      difference_kg?: number;
      difference_percent?: number;
      detail: string;
    }[];
    recommendations: string[];
  };
  priority_actions: string[];
  training_adjustments: string[];
  goal_recommendation: string;
  warnings: string[];
  comparison: {
    previous_measured_at: string;
    delta_muscle_kg: number | null;
    delta_fat_kg: number | null;
    interpretation: string;
  } | null;
  summary: string;
}

export interface WeeklyCheckinResult {
  checkin_id: number;
  week_start: string;
  weight_change_kg: number | null;
  weight_change_percent: number;
  detected_issue: string;
  issue_label: string;
  adjustment: {
    action: string;
    calorie_delta: number;
    new_target_calories: number;
    reason: string;
    detail: string[];
  };
  extra_notes: string[];
  monitoring: string[];
  ai_feedback: string;
  next_checkin_note: string;
  safety_note: string;
}

export interface ExerciseSwapResult {
  original: string;
  original_muscle?: string;
  reason: string;
  reason_label: string;
  message: string;
  substitutes: {
    name: string;
    target_muscle: string;
    type: string;
    movement: string;
    equipment: string[];
    similarity_percent: number;
    notes: string;
    why: string;
  }[];
  safety_note?: string;
  when_to_stop?: string[];
  injury_context?: { active_contraindications: string[]; note: string };
  equipment_context?: { unavailable_equipment_exercises: string[]; note: string };
}

export interface FoodSwapResult {
  original: string;
  original_grams: number;
  original_macros: {
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
  };
  role: string | null;
  role_label: string;
  options: {
    food_key: string;
    name: string;
    grams: number;
    ready_state: string;
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    delta_calories: number;
    delta_protein_g: number;
    match_quality: string;
    note: string;
  }[];
  guidance: string[];
  allergy_context?: { allergies_applied: string[]; note: string };
}

export interface CheatMealPlan {
  excess_calories: number;
  compensation_plan: {
    days: number;
    daily_calorie_reduction: number;
    new_daily_target: number;
    extra_steps_per_day: number;
    extra_steps_note: string;
    steps_days_if_needed: number;
    total_covered_by_diet: number;
    total_covered_by_activity: number;
  };
  weight_impact: { grams: number; explanation: string; reassurance: string };
  floor_warning: string | null;
  tone_message: string;
  do_not: string[];
  do_this: string[];
}

export interface OneRmResult {
  weight_kg: number;
  reps: number;
  estimated_1rm: { epley: number; brzycki: number; recommended: number };
  accuracy_note: string;
  training_zones: Record<
    string,
    {
      zone: string;
      reps: string;
      sets: string;
      rest: string;
      rpe: string;
      percent_1rm: string;
      suggested_weight_low_kg: number;
      suggested_weight_high_kg: number;
    }
  >;
  safety_warning: string;
}

export interface DeloadResult {
  should_deload: boolean;
  weeks_training: number;
  weeks_until_next_deload: number;
  recommendation: string;
  reasons_to_deload: string[];
  signs_you_need_deload_now: string[];
  deload_plan: {
    purpose: string;
    guidance: string[];
    volume_reduction_percent: number;
    intensity_reduction_percent: number;
    expected_outcome: string;
  } | null;
}

export interface OverloadResult {
  exercise_name: string;
  action: string;
  action_label: string;
  current_weight_kg: number | null;
  suggested_weight_kg: number | null;
  increment_kg: number;
  reason: string;
  confidence: string;
  notes: string[];
  progression_principle: string;
}

export interface ChecklistItemRow {
  id: number;
  title: string;
  detail: string | null;
  source: string;
  due_date: string | null;
  is_done: boolean;
  done_at: string | null;
}

export interface CarbCyclingResult {
  enabled: boolean;
  goal: string;
  base_macros: {
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
  };
  days: {
    day_type: string;
    label: string;
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    rationale: string;
  }[];
  weekly_totals: {
    calories: number;
    target_calories: number;
    difference: number;
    difference_percent: number;
    protein_g: number;
  };
  principles: string[];
  suitable_for: string;
}

/* ==========================================================================
   Nhãn hiển thị tiếng Việt
   ========================================================================== */
export const ROLE_LABELS: Record<string, string> = {
  member: "Hội viên",
  trainer: "Huấn luyện viên",
  receptionist: "Lễ tân - Tư vấn",
  staff: "Lễ tân - Tư vấn",
  facility_manager: "Quản lý CSVC",
  admin: "Quản trị viên",
};

export const LEAD_STAGE_LABELS: Record<string, string> = {
  new: "Mới đăng ký",
  scheduled: "Đã hẹn lịch",
  first_visit: "Đã tập buổi 1",
  inbody_consulted: "Đã đo InBody",
  won: "Đã chốt gói",
  lost: "Từ chối",
};

export const LIFECYCLE_LABELS: Record<string, string> = {
  active: "Hoạt động tốt",
  maintenance: "Đang bảo trì",
  out_of_order: "Ngưng sử dụng",
};

export const CONTRACT_STATUS_LABELS: Record<string, string> = {
  active: "Đang hiệu lực",
  frozen: "Đang bảo lưu",
  expired: "Hết hạn",
  cancelled: "Đã hủy",
  transferred: "Đã chuyển nhượng",
  pending: "Chờ kích hoạt",
};

export const ACTION_LABELS: Record<string, string> = {
  increase: "TĂNG TẠ",
  maintain: "GIỮ NGUYÊN",
  decrease: "GIẢM TẠ",
  deload: "GIẢM TẢI",
  calorie_cut: "GIẢM CALO",
  calorie_increase: "TĂNG CALO",
  cardio_add: "TĂNG CARDIO",
  refeed: "REFEED",
  none: "KHÔNG ĐỔI",
};