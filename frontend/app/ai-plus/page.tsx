"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import {
  Chip,
  Delta,
  KV,
  LineChart,
  MacroBar,
  Metric,
  Note,
  ProgressRing,
  SectionTitle,
  Stat,
  Toast,
} from "@/components/ui";
import type {
  CarbCyclingResult,
  CheatMealPlan,
  DeloadResult,
  ExerciseSwapResult,
  FoodSwapResult,
  InBodyAnalysis,
  OneRmResult,
  PARQResult,
  WeeklyCheckinResult,
} from "@/lib/erp-types";

/* ==========================================================================
   AI SMART COACH NÂNG CAO — 5 phân hệ chuyên sâu
     1. Sàng lọc an toàn y tế PAR-Q+ (bắt buộc trước khi lên lịch tập)
     2. Phân tích InBody chuyên sâu (SMM, mỡ nội tạng, dạng C-I-D, mất cân bằng)
     3. Chu kỳ hóa: 1RM, tăng tiến, giảm tải, đổi bài tức thì
     4. Dinh dưỡng nâng cao: đổi món, carb cycling, bù cheat meal
     5. Đánh giá định kỳ hằng tuần & tự động hiệu chỉnh
   ========================================================================== */

type Tab = "parq" | "inbody" | "periodization" | "nutrition" | "weekly";

const PARQ_MAIN = [
  { key: "q_heart_condition", text: "Bác sĩ từng nói bạn có vấn đề về tim và chỉ nên tập dưới sự giám sát y tế?" },
  { key: "q_chest_pain", text: "Bạn có bị đau ngực khi vận động thể lực không?" },
  { key: "q_dizziness", text: "Trong tháng qua, bạn có bị mất thăng bằng do chóng mặt hoặc bất tỉnh không?" },
  { key: "q_chronic_disease", text: "Bạn đang được chẩn đoán bệnh tim, huyết áp cao, tiểu đường hoặc hen suyễn?" },
  { key: "q_bone_joint", text: "Bạn có vấn đề xương khớp (lưng, gối, vai) nặng hơn khi vận động?" },
  { key: "q_medication", text: "Bạn đang dùng thuốc điều trị huyết áp hoặc tim mạch?" },
  { key: "q_other_reason", text: "Có lý do sức khỏe nào khác khiến bạn không nên tập thể lực?" },
];

const PARQ_DETAIL = [
  { key: "has_herniated_disc", text: "Thoát vị đĩa đệm / đau lưng dưới", followUp: "disc_levels", hint: "VD: L4-L5, S1" },
  { key: "has_cervical_degeneration", text: "Thoái hóa đốt sống cổ" },
  { key: "has_acl_tear", text: "Đứt/rách dây chằng chéo (ACL) hoặc chấn thương gối" },
  { key: "has_rotator_cuff", text: "Đau khớp vai / chấn thương Rotator Cuff" },
  { key: "has_heart_disease", text: "Bệnh tim mạch" },
  { key: "has_hypertension", text: "Huyết áp cao" },
  { key: "has_diabetes", text: "Tiểu đường" },
  { key: "has_asthma", text: "Hen suyễn" },
  { key: "is_pregnant", text: "Đang mang thai" },
];

export default function AIPlusPage() {
  const [tab, setTab] = useState<Tab>("parq");
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);

  /* ---------------- PAR-Q ---------------- */
  const [parq, setParq] = useState<Record<string, boolean>>({});
  const [discLevels, setDiscLevels] = useState("");
  const [postpartum, setPostpartum] = useState("");
  const [parqResult, setParqResult] = useState<PARQResult | null>(null);
  const [parqCurrent, setParqCurrent] = useState<any>(null);

  /* ---------------- InBody ---------------- */
  const [inbody, setInbody] = useState<Record<string, string>>({
    height_cm: "",
    weight_kg: "",
    body_fat_percentage: "",
    gender: "male",
    age: "",
    skeletal_muscle_mass_kg: "",
    body_fat_mass_kg: "",
    visceral_fat_level: "",
    waist_cm: "",
    hip_cm: "",
    lean_left_arm: "",
    lean_right_arm: "",
    lean_trunk: "",
    lean_left_leg: "",
    lean_right_leg: "",
  });
  const [inbodyResult, setInbodyResult] = useState<InBodyAnalysis | null>(null);
  const [inbodyHistory, setInbodyHistory] = useState<any>(null);

  /* ---------------- Chu kỳ hóa ---------------- */
  const [oneRm, setOneRm] = useState({ weight_kg: "", reps: "" });
  const [oneRmResult, setOneRmResult] = useState<OneRmResult | null>(null);
  const [deload, setDeload] = useState({ weeks_training: "8", deload_count: "0", training_days_per_week: "4" });
  const [deloadResult, setDeloadResult] = useState<DeloadResult | null>(null);
  const [swap, setSwap] = useState({ exercise_name: "", reason: "equipment_busy" });
  const [swapResult, setSwapResult] = useState<ExerciseSwapResult | null>(null);

  /* ---------------- Dinh dưỡng nâng cao ---------------- */
  const [foods, setFoods] = useState<any[]>([]);
  const [foodSwap, setFoodSwap] = useState({ food_key: "", grams: "150", prioritize: "protein" });
  const [foodSwapResult, setFoodSwapResult] = useState<FoodSwapResult | null>(null);
  const [cheat, setCheat] = useState({ excess_calories: "1500", meal_description: "", days_available: "4" });
  const [cheatResult, setCheatResult] = useState<CheatMealPlan | null>(null);
  const [carb, setCarb] = useState({
    target_calories: "2000",
    protein_g: "150",
    carbs_g: "200",
    fat_g: "60",
    training_days_per_week: "4",
    goal: "recomp",
  });
  const [carbResult, setCarbResult] = useState<CarbCyclingResult | null>(null);

  /* ---------------- Đánh giá tuần ---------------- */
  const [weekForm, setWeekForm] = useState<any>(null);
  const [weekData, setWeekData] = useState<Record<string, string>>({});
  const [weekResult, setWeekResult] = useState<WeeklyCheckinResult | null>(null);
  const [weekHistory, setWeekHistory] = useState<any>(null);

  useEffect(() => {
    const u = localStorage.getItem("hg_user");
    const isLoggedIn = !!u;
    setLoggedIn(isLoggedIn);

    fetchGymData("/ai-plus/parq/questions").catch(() => {});
    fetchGymData("/ai-plus/foods/list").then((r) => setFoods(r.foods ?? [])).catch(() => {});

    if (isLoggedIn) {
      fetchGymData("/ai-plus/parq/my").then(setParqCurrent).catch(() => {});
      fetchGymData("/ai-plus/inbody/history").then(setInbodyHistory).catch(() => {});
      fetchGymData("/ai-plus/weekly-checkin/form").then(setWeekForm).catch(() => {});
      fetchGymData("/ai-plus/weekly-checkin/history?limit=12").then(setWeekHistory).catch(() => {});
    }
  }, []);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const num = (v: string) => (v === "" ? null : Number(v));

  /* ---------------- Handlers ---------------- */
  const submitParq = () =>
    run(async () => {
      const payload: Record<string, any> = { ...parq };
      PARQ_DETAIL.forEach((d) => {
        if (payload[d.key] === undefined) payload[d.key] = false;
      });
      payload.disc_levels = discLevels || null;
      payload.postpartum_months = postpartum ? Number(postpartum) : null;

      const res = await postGymData("/ai-plus/parq/submit", payload);
      setParqResult(res);
      setToast({ kind: "ok", text: res.next_step });
      fetchGymData("/ai-plus/parq/my").then(setParqCurrent).catch(() => {});
    });

  const analyzeInbody = () =>
    run(async () => {
      const keys = Object.keys(inbody);
      const payload: Record<string, any> = { gender: inbody.gender, save_to_profile: true };
      keys.forEach((k) => {
        if (k === "gender") return;
        payload[k] = num(inbody[k]);
      });
      const res = await postGymData("/ai-plus/inbody/analyze", payload);
      setInbodyResult(res);
      setToast({ kind: "ok", text: res.summary });
      fetchGymData("/ai-plus/inbody/history").then(setInbodyHistory).catch(() => {});
    });

  const calcOneRm = () =>
    run(async () => {
      const res = await postGymData("/ai-plus/one-rm", {
        weight_kg: Number(oneRm.weight_kg),
        reps: Number(oneRm.reps),
      });
      setOneRmResult(res);
    });

  const checkDeload = () =>
    run(async () => {
      const res = await postGymData("/ai-plus/deload/check", {
        weeks_training: Number(deload.weeks_training),
        deload_count: Number(deload.deload_count),
        training_days_per_week: Number(deload.training_days_per_week),
      });
      setDeloadResult(res);
    });

  const swapExercise = () =>
    run(async () => {
      const res = await postGymData("/ai-plus/swap-exercise", {
        exercise_name: swap.exercise_name,
        reason: swap.reason,
        branch_id: 1,
      });
      setSwapResult(res);
    });

  const doFoodSwap = () =>
    run(async () => {
      const res = await postGymData("/ai-plus/swap-food", {
        food_key: foodSwap.food_key,
        grams: Number(foodSwap.grams),
        prioritize: foodSwap.prioritize,
      });
      setFoodSwapResult(res);
    });

  const doCheat = () =>
    run(async () => {
      const res = await postGymData("/ai-plus/cheat-meal-recovery", {
        excess_calories: Number(cheat.excess_calories),
        meal_description: cheat.meal_description || null,
        days_available: Number(cheat.days_available),
      });
      setCheatResult(res);
    });

  const doCarb = () =>
    run(async () => {
      const res = await postGymData("/ai-plus/carb-cycling", {
        target_calories: Number(carb.target_calories),
        protein_g: Number(carb.protein_g),
        carbs_g: Number(carb.carbs_g),
        fat_g: Number(carb.fat_g),
        training_days_per_week: Number(carb.training_days_per_week),
        goal: carb.goal,
      });
      setCarbResult(res);
    });

  const submitWeek = () =>
    run(async () => {
      const payload: Record<string, any> = {};
      Object.entries(weekData).forEach(([k, v]) => {
        if (v !== "" && v != null) {
          payload[k] = ["sessions_completed", "sessions_planned", "hunger_level", "sleep_quality",
            "energy_level", "stress_level"].includes(k) ? Number(v) : Number(v);
        }
      });
      payload.sessions_planned = Number(weekForm?.planned_sessions ?? 4);
      const res = await postGymData("/ai-plus/weekly-checkin", payload);
      setWeekResult(res);
      setToast({ kind: "ok", text: res.ai_feedback });
      fetchGymData("/ai-plus/weekly-checkin/history?limit=12").then(setWeekHistory).catch(() => {});
    });

  const riskTone = (r: string) =>
    r === "low" ? "ok" : r === "moderate" ? "warn" : "danger";

  const canSubmitParq = PARQ_MAIN.every((q) => parq[q.key] !== undefined);

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <Chip>AI SMART COACH — CHUYÊN SÂU</Chip>
          <h1>Sàng Lọc Y Tế, InBody &amp; Chu Kỳ Hóa</h1>
          <p>
            Sàng lọc an toàn PAR-Q+ bắt buộc, phân tích phiếu InBody (SMM, mỡ nội tạng, mất cân
            bằng vùng), chu kỳ hóa tăng tiến và dinh dưỡng nâng cao.
          </p>
        </div>
        <div className="hg-flex">
          {parqCurrent?.has_screening && (
            <Chip tone={parqCurrent.is_expired ? "warn" : "ok"}>
              {parqCurrent.is_expired ? "PAR-Q QUÁ HẠN" : "PAR-Q HỢP LỆ"}
            </Chip>
          )}
          {!loggedIn && <Chip tone="warn">CHƯA ĐĂNG NHẬP</Chip>}
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      {!loggedIn && (
        <Note tone="gold">
          Bạn có thể dùng thử mọi công cụ tính toán ở đây. Đăng nhập để lưu kết quả vào hồ sơ, theo
          dõi lịch sử và để AI Coach tự động áp dụng ràng buộc an toàn khi sinh lịch tập.
        </Note>
      )}

      <div className="hg-tabs">
        {[
          { id: "parq", label: "Sàng lọc PAR-Q+" },
          { id: "inbody", label: "Phân tích InBody" },
          { id: "periodization", label: "Chu kỳ hóa" },
          { id: "nutrition", label: "Dinh dưỡng nâng cao" },
          { id: "weekly", label: "Đánh giá hằng tuần" },
        ].map((t) => (
          <button
            key={t.id}
            className={`hg-tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id as Tab)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ================= 1. PAR-Q ================= */}
      {tab === "parq" && (
        <div>
          {parqCurrent?.has_screening && (
            <div className="hg-chart-card">
              <div className="hg-chart-title">Phiếu sàng lọc gần nhất</div>
              <div className="stats-bar">
                <Stat label="Ngày sàng lọc" value={String(parqCurrent.screened_at)} />
                <Stat label="Mức rủi ro" value={parqCurrent.risk_level} gold />
                <Stat
                  label="Cần xác nhận y khoa"
                  value={parqCurrent.needs_medical_clearance ? "CÓ" : "KHÔNG"}
                />
                <Stat label="Số ngày đã qua" value={`${parqCurrent.days_since_screening} ngày`} />
              </div>
              {parqCurrent.renewal_note && <Note tone="warn">{parqCurrent.renewal_note}</Note>}
              {parqCurrent.contraindications?.length > 0 && (
                <Note tone="danger">
                  <strong>Ràng buộc đang áp dụng:</strong> {parqCurrent.contraindications.join(", ")}
                </Note>
              )}
            </div>
          )}

          <SectionTitle>Câu hỏi sàng lọc bắt buộc (PAR-Q+)</SectionTitle>
          <p className="hg-muted" style={{ marginBottom: "14px" }}>
            Bảng câu hỏi này giúp AI thiết kế chương trình tập AN TOÀN cho riêng bạn. Đây là bước
            BẮT BUỘC trước khi nhận lịch tập.
          </p>

          <div className="hg-chart-card">
            {PARQ_MAIN.map((q) => (
              <div key={q.key} className="hg-kv" style={{ alignItems: "center" }}>
                <span style={{ flex: 1, paddingRight: "12px" }}>{q.text}</span>
                <span className="hg-flex" style={{ gap: "4px" }}>
                  <button
                    className={parq[q.key] === false ? "hg-btn-primary hg-btn-sm" : "hg-btn-ghost hg-btn-sm"}
                    onClick={() => setParq({ ...parq, [q.key]: false })}
                  >
                    KHÔNG
                  </button>
                  <button
                    className={
                      parq[q.key] === true ? "hg-btn-gold hg-btn-sm" : "hg-btn-ghost hg-btn-sm"
                    }
                    onClick={() => setParq({ ...parq, [q.key]: true })}
                  >
                    CÓ
                  </button>
                </span>
              </div>
            ))}
          </div>

          <SectionTitle>Chi tiết tình trạng sức khỏe</SectionTitle>
          <p className="hg-muted" style={{ marginBottom: "12px" }}>
            Phần này giúp AI biết CHÍNH XÁC bài tập nào cần loại bỏ. Chỉ tích những mục đúng với bạn.
          </p>
          <div className="hg-chart-card">
            {PARQ_DETAIL.map((d) => (
              <div key={d.key}>
                <div className="hg-kv" style={{ alignItems: "center" }}>
                  <span style={{ flex: 1, paddingRight: "12px" }}>{d.text}</span>
                  <input
                    type="checkbox"
                    style={{ width: 18, height: 18 }}
                    checked={!!parq[d.key]}
                    onChange={(e) => setParq({ ...parq, [d.key]: e.target.checked })}
                  />
                </div>
                {d.followUp && parq[d.key] && (
                  <input
                    className="input-box"
                    placeholder={d.hint}
                    value={discLevels}
                    onChange={(e) => setDiscLevels(e.target.value)}
                  />
                )}
              </div>
            ))}
            <label>Số tháng sau sinh (nếu mới sinh, không bắt buộc)</label>
            <input
              className="input-box"
              type="number"
              min={0}
              max={60}
              value={postpartum}
              onChange={(e) => setPostpartum(e.target.value)}
            />
          </div>

          <button
            className="hg-btn-gold"
            style={{ width: "100%" }}
            onClick={submitParq}
            disabled={busy || !canSubmitParq}
          >
            {busy && <span className="hg-spinner" />}
            {canSubmitParq ? "Nộp phiếu sàng lọc" : "Vui lòng trả lời đủ 7 câu hỏi bắt buộc"}
          </button>

          {parqResult && (
            <div style={{ marginTop: "18px" }}>
              <Note tone={parqResult.blocked_from_training ? "danger" : "ok"}>
                {parqResult.next_step}
              </Note>
              <div className="stats-bar">
                <Stat label="Mức rủi ro" value={parqResult.risk_level} gold />
                <Stat label="PAR-Q dương tính" value={parqResult.parq_positive ? "CÓ" : "KHÔNG"} />
                <Stat
                  label="Cần xác nhận y khoa"
                  value={parqResult.needs_medical_clearance ? "CÓ" : "KHÔNG"}
                />
                <Stat label="Đã lưu hồ sơ" value={parqResult.saved ? "CÓ" : "KHÔNG"} />
              </div>

              {parqResult.clearance_note && <Note tone="warn">{parqResult.clearance_note}</Note>}

              {parqResult.contraindication_labels?.length > 0 && (
                <div className="hg-warning-box">
                  <h4>Ràng buộc an toàn AI sẽ tự động áp dụng</h4>
                  <ul>
                    {parqResult.contraindication_labels.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}

              {parqResult.applied_hard_rules?.length > 0 && (
                <div className="hg-chart-card">
                  <div className="hg-chart-title">Quy tắc cứng đang được áp dụng</div>
                  <ul className="benefit-list">
                    {parqResult.applied_hard_rules.map((r, i) => (
                      <li key={i}>
                        <span style={{ color: "#b01c2e", marginRight: 6, fontWeight: 800 }}>⛔</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {parqResult.safe_exercise_notes?.length > 0 && (
                <div className="hg-chart-card">
                  <div className="hg-chart-title">Khuyến nghị tập luyện an toàn</div>
                  <ul className="benefit-list">
                    {parqResult.safe_exercise_notes.map((s, i) => (
                      <li key={i}>
                        <span style={{ color: "#0f7a52", marginRight: 6, fontWeight: 800 }}>✓</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================= 2. INBODY ================= */}
      {tab === "inbody" && (
        <div>
          <div className="hg-grid-2">
            <div className="hg-chart-card">
              <div className="hg-chart-title">Thông số cơ bản</div>
              <label>Giới tính</label>
              <select
                className="input-box"
                value={inbody.gender}
                onChange={(e) => setInbody({ ...inbody, gender: e.target.value })}
              >
                <option value="male">Nam</option>
                <option value="female">Nữ</option>
              </select>
              {[
                ["height_cm", "Chiều cao (cm)"],
                ["weight_kg", "Cân nặng (kg)"],
                ["body_fat_percentage", "Tỷ lệ mỡ cơ thể (%)"],
                ["age", "Tuổi"],
              ].map(([k, label]) => (
                <div key={k}>
                  <label>{label}</label>
                  <input
                    className="input-box"
                    type="number"
                    value={inbody[k]}
                    onChange={(e) => setInbody({ ...inbody, [k]: e.target.value })}
                  />
                </div>
              ))}
            </div>

            <div className="hg-chart-card">
              <div className="hg-chart-title">Chỉ số InBody chuyên sâu</div>
              {[
                ["skeletal_muscle_mass_kg", "Khối lượng cơ xương SMM (kg)"],
                ["body_fat_mass_kg", "Khối lượng mỡ BFM (kg)"],
                ["visceral_fat_level", "Cấp độ mỡ nội tạng (chuẩn < 10)"],
                ["waist_cm", "Vòng eo (cm)"],
                ["hip_cm", "Vòng hông (cm)"],
              ].map(([k, label]) => (
                <div key={k}>
                  <label>{label}</label>
                  <input
                    className="input-box"
                    type="number"
                    value={inbody[k]}
                    onChange={(e) => setInbody({ ...inbody, [k]: e.target.value })}
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Phân tích cơ – mỡ từng vùng (Segmental)</div>
            <p className="hg-chart-sub">
              Nhập khối lượng cơ nạc từng vùng để AI phát hiện mất cân bằng (VD: tay trái yếu hơn
              tay phải, chân yếu hơn thân trên) và bổ sung bài tập đơn bên.
            </p>
            <div className="hg-grid-2">
              <div>
                <label>Tay trái (kg)</label>
                <input className="input-box" type="number" value={inbody.lean_left_arm}
                  onChange={(e) => setInbody({ ...inbody, lean_left_arm: e.target.value })} />
                <label>Tay phải (kg)</label>
                <input className="input-box" type="number" value={inbody.lean_right_arm}
                  onChange={(e) => setInbody({ ...inbody, lean_right_arm: e.target.value })} />
              </div>
              <div>
                <label>Chân trái (kg)</label>
                <input className="input-box" type="number" value={inbody.lean_left_leg}
                  onChange={(e) => setInbody({ ...inbody, lean_left_leg: e.target.value })} />
                <label>Chân phải (kg)</label>
                <input className="input-box" type="number" value={inbody.lean_right_leg}
                  onChange={(e) => setInbody({ ...inbody, lean_right_leg: e.target.value })} />
              </div>
            </div>
            <label>Thân mình (kg)</label>
            <input className="input-box" type="number" value={inbody.lean_trunk}
              onChange={(e) => setInbody({ ...inbody, lean_trunk: e.target.value })} />
          </div>

          <button
            className="hg-btn-gold"
            style={{ width: "100%" }}
            onClick={analyzeInbody}
            disabled={busy || !inbody.height_cm || !inbody.weight_kg}
          >
            {busy && <span className="hg-spinner" />}
            Phân tích phiếu InBody
          </button>

          {inbodyResult && (
            <div style={{ marginTop: "18px" }}>
              <Note tone="ok">{inbodyResult.summary}</Note>

              <div className="stats-bar">
                <Stat label="Dạng hình thể" value={inbodyResult.shape.type} gold />
                <Stat
                  label="Mỡ nội tạng"
                  value={inbodyResult.visceral_fat.level ?? "—"}
                />
                <Stat label="Tỷ lệ SMM" value={inbodyResult.smm_ratio.value ?? "—"} />
                <Stat label="WHR" value={inbodyResult.whr.value ?? "—"} />
                <Stat
                  label="Điểm cân bằng"
                  value={inbodyResult.segmental_analysis.balance_score}
                />
              </div>

              <div className="hg-verdict">
                <h3>Dạng hình thể: {inbodyResult.shape.type}</h3>
                <p>{inbodyResult.shape.description}</p>
                <p className="hg-muted" style={{ marginTop: "6px", fontStyle: "italic" }}>
                  {inbodyResult.shape.rationale}
                </p>
              </div>

              {inbodyResult.visceral_fat.is_warning && (
                <Note tone="danger">
                  Cấp độ mỡ nội tạng {inbodyResult.visceral_fat.level} đã vượt ngưỡng an toàn (dưới
                  10). Mỡ nội tạng cao liên quan trực tiếp tới nguy cơ tim mạch và tiểu đường —
                  cần ưu tiên giảm ngay bằng thâm hụt calo và cardio đều đặn.
                </Note>
              )}

              {inbodyResult.comparison && (
                <div className="hg-chart-card">
                  <div className="hg-chart-title">So sánh với lần đo trước</div>
                  <div className="hg-kv">
                    <span>Lần đo trước</span>
                    <span className="hg-num-mono">{inbodyResult.comparison.previous_measured_at}</span>
                  </div>
                  <div className="hg-kv">
                    <span>Thay đổi khối lượng cơ</span>
                    <span>
                      {inbodyResult.comparison.delta_muscle_kg != null ? (
                        <Delta value={inbodyResult.comparison.delta_muscle_kg} unit="kg" />
                      ) : (
                        "—"
                      )}
                    </span>
                  </div>
                  <div className="hg-kv">
                    <span>Thay đổi khối lượng mỡ</span>
                    <span>
                      {inbodyResult.comparison.delta_fat_kg != null ? (
                        <Delta value={inbodyResult.comparison.delta_fat_kg} unit="kg" invert />
                      ) : (
                        "—"
                      )}
                    </span>
                  </div>
                  <Note>{inbodyResult.comparison.interpretation}</Note>
                </div>
              )}

              {inbodyResult.segmental_analysis.has_data && (
                <div className="hg-chart-card">
                  <div className="hg-chart-title">Phân tích mất cân bằng vùng</div>
                  <div className="hg-metric-grid">
                    <Metric
                      label="Lệch tay"
                      value={inbodyResult.segmental_analysis.arm_difference_kg}
                      unit="kg"
                      note={`${inbodyResult.segmental_analysis.arm_difference_percent}%`}
                    />
                    <Metric
                      label="Lệch chân"
                      value={inbodyResult.segmental_analysis.leg_difference_kg}
                      unit="kg"
                      note={`${inbodyResult.segmental_analysis.leg_difference_percent}%`}
                      gold
                    />
                  </div>
                  {inbodyResult.segmental_analysis.imbalances.map((ib, i) => (
                    <Note key={i} tone={ib.severity === "high" ? "danger" : "default"}>
                      <strong>[{ib.severity}]</strong> {ib.detail}
                    </Note>
                  ))}
                  {inbodyResult.segmental_analysis.recommendations.length > 0 && (
                    <ul className="benefit-list" style={{ marginTop: "10px" }}>
                      {inbodyResult.segmental_analysis.recommendations.map((r, i) => (
                        <li key={i}>
                          <span style={{ color: "#0b6e8f", marginRight: 6, fontWeight: 800 }}>▸</span>
                          {r}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {inbodyResult.priority_actions.length > 0 && (
                <div className="hg-chart-card">
                  <div className="hg-chart-title">Việc cần ưu tiên làm ngay</div>
                  <ul className="benefit-list">
                    {inbodyResult.priority_actions.map((p, i) => (
                      <li key={i}>
                        <span style={{ color: "#b8860b", marginRight: 6, fontWeight: 800 }}>★</span>
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {inbodyResult.training_adjustments.length > 0 && (
                <div className="hg-chart-card">
                  <div className="hg-chart-title">Điều chỉnh lịch tập</div>
                  <ul className="benefit-list">
                    {inbodyResult.training_adjustments.map((t, i) => (
                      <li key={i}>
                        <span style={{ color: "#0f7a52", marginRight: 6, fontWeight: 800 }}>✓</span>
                        {t}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <Note tone="gold">{inbodyResult.goal_recommendation}</Note>

              {inbodyResult.warnings.map((w, i) => (
                <Note key={i} tone="danger">
                  {w}
                </Note>
              ))}
            </div>
          )}

          {inbodyHistory?.trend && (
            <>
              <SectionTitle>Xu hướng InBody qua các lần đo</SectionTitle>
              <div className="hg-chart-card">
                <div className="hg-chart-title">Khối lượng cơ &amp; mỡ theo thời gian</div>
                <LineChart
                  labels={inbodyHistory.trend.labels}
                  series={[
                    { name: "Cơ xương SMM (kg)", data: inbodyHistory.trend.smm },
                    { name: "Mỡ (kg)", data: inbodyHistory.trend.body_fat_kg },
                  ]}
                  unit="kg"
                />
              </div>
            </>
          )}
        </div>
      )}

      {/* ================= 3. CHU KỲ HÓA ================= */}
      {tab === "periodization" && (
        <div>
          <div className="hg-grid-2">
            <div className="hg-chart-card">
              <div className="hg-chart-title">Tính 1RM &amp; vùng tập luyện</div>
              <p className="hg-chart-sub">
                Công thức Epley &amp; Brzycki. Dùng để xác định mức tạ cho từng vùng reps.
              </p>
              <label>Mức tạ đã nâng được (kg)</label>
              <input className="input-box" type="number" value={oneRm.weight_kg}
                onChange={(e) => setOneRm({ ...oneRm, weight_kg: e.target.value })} />
              <label>Số lần lặp đã thực hiện</label>
              <input className="input-box" type="number" value={oneRm.reps}
                onChange={(e) => setOneRm({ ...oneRm, reps: e.target.value })} />
              <button className="hg-btn-primary" style={{ width: "100%" }} onClick={calcOneRm} disabled={busy}>
                {busy && <span className="hg-spinner" />}
                Tính 1RM
              </button>
            </div>

            <div className="hg-chart-card">
              <div className="hg-chart-title">Kiểm tra giảm tải (Deload)</div>
              <p className="hg-chart-sub">
                Nên giảm tải định kỳ mỗi 6-8 tuần để phục hồi hệ thần kinh trung ương.
              </p>
              <label>Số tuần đã tập liên tục</label>
              <input className="input-box" type="number" value={deload.weeks_training}
                onChange={(e) => setDeload({ ...deload, weeks_training: e.target.value })} />
              <label>Số lần đã giảm tải</label>
              <input className="input-box" type="number" value={deload.deload_count}
                onChange={(e) => setDeload({ ...deload, deload_count: e.target.value })} />
              <label>Số buổi tập mỗi tuần</label>
              <input className="input-box" type="number" value={deload.training_days_per_week}
                onChange={(e) => setDeload({ ...deload, training_days_per_week: e.target.value })} />
              <button className="hg-btn-primary" style={{ width: "100%" }} onClick={checkDeload} disabled={busy}>
                {busy && <span className="hg-spinner" />}
                Kiểm tra
              </button>
            </div>
          </div>

          {oneRmResult && (
            <div style={{ marginTop: "18px" }}>
              <div className="stats-bar">
                <Stat label="1RM (Epley)" value={`${oneRmResult.estimated_1rm.epley} kg`} gold />
                <Stat label="1RM (Brzycki)" value={`${oneRmResult.estimated_1rm.brzycki} kg`} />
                <Stat label="1RM khuyến nghị" value={`${oneRmResult.estimated_1rm.recommended} kg`} gold />
              </div>
              <Note>{oneRmResult.accuracy_note}</Note>
              <SectionTitle>Vùng tập luyện theo % 1RM</SectionTitle>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Vùng</th>
                      <th>% 1RM</th>
                      <th>Reps</th>
                      <th>Sets</th>
                      <th>Nghỉ</th>
                      <th>RPE</th>
                      <th>Mức tạ gợi ý</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.values(oneRmResult.training_zones).map((z: any, i) => (
                      <tr key={i}>
                        <td>
                          <strong>{z.zone}</strong>
                        </td>
                        <td className="hg-num-mono">{z.percent_1rm}</td>
                        <td className="hg-num">{z.reps}</td>
                        <td className="hg-num">{z.sets}</td>
                        <td style={{ fontSize: "12.5px" }}>{z.rest}</td>
                        <td className="hg-num">{z.rpe}</td>
                        <td className="hg-num-mono" style={{ fontWeight: 600 }}>
                          {z.suggested_weight_low_kg} – {z.suggested_weight_high_kg} kg
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Note tone="danger">{oneRmResult.safety_warning}</Note>
            </div>
          )}

          {deloadResult && (
            <div style={{ marginTop: "18px" }}>
              <Note tone={deloadResult.should_deload ? "gold" : "ok"}>
                {deloadResult.recommendation}
              </Note>
              <div className="stats-bar">
                <Stat label="Tuần đã tập" value={deloadResult.weeks_training} />
                <Stat label="Còn lại đến deload" value={`${deloadResult.weeks_until_next_deload} tuần`} gold />
                <Stat label="Nên giảm tải" value={deloadResult.should_deload ? "CÓ" : "CHƯA"} />
              </div>

              {deloadResult.reasons_to_deload.length > 0 && (
                <div className="hg-chart-card">
                  <div className="hg-chart-title">Lý do nên giảm tải</div>
                  <ul className="benefit-list">
                    {deloadResult.reasons_to_deload.map((r, i) => (
                      <li key={i}>
                        <span style={{ color: "#b8860b", marginRight: 6, fontWeight: 800 }}>▸</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="hg-warning-box">
                <h4>Dấu hiệu bạn cần giảm tải ngay</h4>
                <ul>
                  {deloadResult.signs_you_need_deload_now.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>

              {deloadResult.deload_plan && (
                <div className="hg-chart-card">
                  <div className="hg-chart-title">{deloadResult.deload_plan.purpose}</div>
                  <div className="hg-kv">
                    <span>Giảm khối lượng</span>
                    <span className="hg-num-mono">
                      −{deloadResult.deload_plan.volume_reduction_percent}%
                    </span>
                  </div>
                  <div className="hg-kv">
                    <span>Giảm cường độ</span>
                    <span className="hg-num-mono">
                      −{deloadResult.deload_plan.intensity_reduction_percent}%
                    </span>
                  </div>
                  <ul className="benefit-list" style={{ marginTop: "10px" }}>
                    {deloadResult.deload_plan.guidance.map((g, i) => (
                      <li key={i}>
                        <span style={{ color: "#0b6e8f", marginRight: 6, fontWeight: 800 }}>▸</span>
                        {g}
                      </li>
                    ))}
                  </ul>
                  <Note tone="gold">{deloadResult.deload_plan.expected_outcome}</Note>
                </div>
              )}
            </div>
          )}

          <SectionTitle>Đổi bài tập tức thì</SectionTitle>
          <div className="hg-chart-card">
            <p className="hg-chart-sub">
              Máy đang có người dùng, máy hỏng, đau khớp hay không có thiết bị? AI tìm bài thay thế
              tương đương — tự động tôn trọng chấn thương trong phiếu PAR-Q và thiết bị đang bảo trì.
            </p>
            <div className="hg-grid-2">
              <div>
                <label>Tên bài tập hiện tại</label>
                <input className="input-box" value={swap.exercise_name}
                  onChange={(e) => setSwap({ ...swap, exercise_name: e.target.value })}
                  placeholder="VD: Barbell Back Squat" />
              </div>
              <div>
                <label>Lý do đổi</label>
                <select className="input-box" value={swap.reason}
                  onChange={(e) => setSwap({ ...swap, reason: e.target.value })}>
                  <option value="equipment_busy">Máy đang có người dùng</option>
                  <option value="equipment_broken">Máy hỏng / bảo trì</option>
                  <option value="joint_pain">Đang đau khớp</option>
                  <option value="no_equipment">Không có thiết bị</option>
                  <option value="too_hard">Bài quá khó</option>
                  <option value="preference">Không thích bài này</option>
                </select>
              </div>
            </div>
            <button className="hg-btn-primary" style={{ width: "100%" }}
              onClick={swapExercise} disabled={busy || !swap.exercise_name}>
              {busy && <span className="hg-spinner" />}
              Tìm bài thay thế
            </button>

            {swapResult && (
              <div style={{ marginTop: "14px" }}>
                <Note>{swapResult.message}</Note>
                {swapResult.safety_note && <Note tone="danger">{swapResult.safety_note}</Note>}
                {swapResult.injury_context && <Note tone="warn">{swapResult.injury_context.note}</Note>}
                {swapResult.equipment_context && <Note tone="warn">{swapResult.equipment_context.note}</Note>}

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Bài thay thế</th>
                        <th>Nhóm cơ</th>
                        <th>Dụng cụ</th>
                        <th>Độ tương đồng</th>
                        <th>Vì sao</th>
                      </tr>
                    </thead>
                    <tbody>
                      {swapResult.substitutes.map((s, i) => (
                        <tr key={i}>
                          <td>
                            <strong>{s.name}</strong>
                            <div className="hg-exercise-muscle">{s.type} · {s.movement}</div>
                          </td>
                          <td style={{ fontSize: "12.5px" }}>{s.target_muscle}</td>
                          <td style={{ fontSize: "12.5px" }}>{s.equipment.join(", ")}</td>
                          <td>
                            <span className="hg-sets-badge">{s.similarity_percent}%</span>
                          </td>
                          <td style={{ fontSize: "12.5px", color: "#35505c" }}>{s.why}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {swapResult.when_to_stop && (
                  <div className="hg-warning-box">
                    <h4>DỪNG LẠI ngay nếu gặp các dấu hiệu sau</h4>
                    <ul>
                      {swapResult.when_to_stop.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ================= 4. DINH DƯỠNG NÂNG CAO ================= */}
      {tab === "nutrition" && (
        <div>
          <SectionTitle>Đổi món tương đương macro</SectionTitle>
          <div className="hg-chart-card">
            <p className="hg-chart-sub">
              Đổi thực phẩm này sang thực phẩm khác nhưng giữ nguyên lượng calo và đạm — dùng khi
              hết hàng, đổi khẩu vị hoặc đi ăn ngoài.
            </p>
            <div className="hg-grid-2">
              <div>
                <label>Thực phẩm cần đổi</label>
                <select className="input-box" value={foodSwap.food_key}
                  onChange={(e) => setFoodSwap({ ...foodSwap, food_key: e.target.value })}>
                  <option value="">Chọn thực phẩm...</option>
                  {foods.map((f) => (
                    <option key={f.key} value={f.key}>
                      {f.name} — {f.role_label}
                    </option>
                  ))}
                </select>
                <label>Khối lượng (gram)</label>
                <input className="input-box" type="number" value={foodSwap.grams}
                  onChange={(e) => setFoodSwap({ ...foodSwap, grams: e.target.value })} />
              </div>
              <div>
                <label>Ưu tiên giữ nguyên</label>
                <select className="input-box" value={foodSwap.prioritize}
                  onChange={(e) => setFoodSwap({ ...foodSwap, prioritize: e.target.value })}>
                  <option value="protein">Đạm (Protein)</option>
                  <option value="calories">Calo</option>
                  <option value="carbs">Tinh bột</option>
                  <option value="fat">Chất béo</option>
                </select>
                <button className="hg-btn-primary" style={{ width: "100%", marginTop: "10px" }}
                  onClick={doFoodSwap} disabled={busy || !foodSwap.food_key}>
                  {busy && <span className="hg-spinner" />}
                  Tìm món thay thế
                </button>
              </div>
            </div>

            {foodSwapResult && (
              <div style={{ marginTop: "14px" }}>
                <Note tone="ok">
                  <strong>{foodSwapResult.original}</strong> ({foodSwapResult.original_grams}g) —{" "}
                  {foodSwapResult.original_macros.calories} kcal ·{" "}
                  {foodSwapResult.original_macros.protein_g}g đạm · vai trò:{" "}
                  {foodSwapResult.role_label}
                </Note>
                {foodSwapResult.allergy_context && (
                  <Note tone="warn">{foodSwapResult.allergy_context.note}</Note>
                )}
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Món thay thế</th>
                        <th>Khối lượng</th>
                        <th>Calo</th>
                        <th>Đạm</th>
                        <th>Chênh lệch</th>
                        <th>Độ khớp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {foodSwapResult.options.map((o, i) => (
                        <tr key={i}>
                          <td>
                            <strong>{o.name}</strong>
                            <div className="hg-exercise-muscle">{o.note}</div>
                          </td>
                          <td className="hg-num-mono">
                            {o.grams}g<div className="hg-exercise-muscle">{o.ready_state}</div>
                          </td>
                          <td className="hg-num">{o.calories}</td>
                          <td className="hg-num">{o.protein_g}g</td>
                          <td>
                            <Delta value={o.delta_calories} unit=" kcal" />
                            <div style={{ fontSize: "11.5px" }}>
                              <Delta value={o.delta_protein_g} unit="g đạm" />
                            </div>
                          </td>
                          <td>
                            <Chip tone={o.match_quality === "excellent" ? "ok" : "default"}>
                              {o.match_quality}
                            </Chip>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <ul className="benefit-list">
                  {foodSwapResult.guidance.map((g, i) => (
                    <li key={i}>
                      <span style={{ color: "#0b6e8f", marginRight: 6, fontWeight: 800 }}>▸</span>
                      {g}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <SectionTitle>Bù trừ sau bữa ăn phá kèo (Cheat Meal)</SectionTitle>
          <div className="hg-chart-card">
            <p className="hg-chart-sub">
              Ăn quá đà không phải thảm họa. AI chia đều phần calo dư ra 3-4 ngày — KHÔNG bao giờ
              khuyến nghị nhịn đói hay cắt calo cực đoan.
            </p>
            <div className="hg-grid-2">
              <div>
                <label>Calo ăn vượt mức (kcal)</label>
                <input className="input-box" type="number" value={cheat.excess_calories}
                  onChange={(e) => setCheat({ ...cheat, excess_calories: e.target.value })} />
                <label>Mô tả bữa ăn (không bắt buộc)</label>
                <input className="input-box" value={cheat.meal_description}
                  onChange={(e) => setCheat({ ...cheat, meal_description: e.target.value })}
                  placeholder="VD: Buffet lẩu nướng với bạn bè" />
              </div>
              <div>
                <label>Số ngày có thể bù (1-7)</label>
                <input className="input-box" type="number" min={1} max={7} value={cheat.days_available}
                  onChange={(e) => setCheat({ ...cheat, days_available: e.target.value })} />
                <button className="hg-btn-primary" style={{ width: "100%", marginTop: "10px" }}
                  onClick={doCheat} disabled={busy}>
                  {busy && <span className="hg-spinner" />}
                  Lập kế hoạch bù trừ
                </button>
              </div>
            </div>

            {cheatResult && (
              <div style={{ marginTop: "14px" }}>
                <Note tone="gold">{cheatResult.tone_message}</Note>
                <div className="stats-bar">
                  <Stat label="Calo vượt mức" value={`${cheatResult.excess_calories} kcal`} />
                  <Stat label="Giảm mỗi ngày" value={`−${cheatResult.compensation_plan.daily_calorie_reduction} kcal`} gold />
                  <Stat label="Calo mục tiêu mới" value={`${cheatResult.compensation_plan.new_daily_target} kcal`} />
                  <Stat label="Thêm bước chân/ngày" value={cheatResult.compensation_plan.extra_steps_per_day.toLocaleString("vi-VN")} />
                </div>
                <div className="hg-kv">
                  <span>Số ngày bù</span>
                  <span className="hg-num">{cheatResult.compensation_plan.days} ngày</span>
                </div>
                <div className="hg-kv">
                  <span>Bù bằng ăn uống</span>
                  <span className="hg-num-mono">
                    {cheatResult.compensation_plan.total_covered_by_diet} kcal
                  </span>
                </div>
                <div className="hg-kv">
                  <span>Bù bằng vận động</span>
                  <span className="hg-num-mono">
                    {cheatResult.compensation_plan.total_covered_by_activity} kcal
                  </span>
                </div>
                <Note>{cheatResult.compensation_plan.extra_steps_note}</Note>
                <Note>
                  <strong>Tác động cân nặng:</strong> {cheatResult.weight_impact.grams}g —{" "}
                  {cheatResult.weight_impact.explanation}
                  <div style={{ marginTop: "4px" }}>{cheatResult.weight_impact.reassurance}</div>
                </Note>
                {cheatResult.floor_warning && <Note tone="danger">{cheatResult.floor_warning}</Note>}

                <div className="hg-grid-2">
                  <div className="hg-chart-card">
                    <div className="hg-chart-title">NÊN LÀM</div>
                    <ul className="benefit-list">
                      {cheatResult.do_this.map((d, i) => (
                        <li key={i}>
                          <span style={{ color: "#0f7a52", marginRight: 6, fontWeight: 800 }}>✓</span>
                          {d}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="hg-chart-card">
                    <div className="hg-chart-title">KHÔNG NÊN LÀM</div>
                    <ul className="benefit-list">
                      {cheatResult.do_not.map((d, i) => (
                        <li key={i}>
                          <span style={{ color: "#b01c2e", marginRight: 6, fontWeight: 800 }}>✕</span>
                          {d}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>

          <SectionTitle>Chu kỳ hóa tinh bột (Carb Cycling)</SectionTitle>
          <div className="hg-chart-card">
            <p className="hg-chart-sub">
              Xoay vòng lượng tinh bột theo ngày tập và ngày nghỉ — giữ hiệu suất tập luyện cao
              nhưng vẫn thâm hụt calo đều trong tuần.
            </p>
            <div className="hg-grid-2">
              <div>
                <label>Calo mục tiêu/ngày</label>
                <input className="input-box" type="number" value={carb.target_calories}
                  onChange={(e) => setCarb({ ...carb, target_calories: e.target.value })} />
                <label>Đạm (g)</label>
                <input className="input-box" type="number" value={carb.protein_g}
                  onChange={(e) => setCarb({ ...carb, protein_g: e.target.value })} />
              </div>
              <div>
                <label>Tinh bột (g)</label>
                <input className="input-box" type="number" value={carb.carbs_g}
                  onChange={(e) => setCarb({ ...carb, carbs_g: e.target.value })} />
                <label>Chất béo (g)</label>
                <input className="input-box" type="number" value={carb.fat_g}
                  onChange={(e) => setCarb({ ...carb, fat_g: e.target.value })} />
              </div>
            </div>
            <div className="hg-grid-2">
              <div>
                <label>Số buổi tập/tuần</label>
                <input className="input-box" type="number" value={carb.training_days_per_week}
                  onChange={(e) => setCarb({ ...carb, training_days_per_week: e.target.value })} />
              </div>
              <div>
                <label>Mục tiêu</label>
                <select className="input-box" value={carb.goal}
                  onChange={(e) => setCarb({ ...carb, goal: e.target.value })}>
                  <option value="recomp">Tái cấu trúc cơ thể</option>
                  <option value="cutting">Giảm mỡ</option>
                  <option value="bulking">Tăng cơ</option>
                </select>
              </div>
            </div>
            <button className="hg-btn-primary" style={{ width: "100%" }} onClick={doCarb} disabled={busy}>
              {busy && <span className="hg-spinner" />}
              Tạo lịch carb cycling
            </button>

            {carbResult && (
              <div style={{ marginTop: "14px" }}>
                {!carbResult.enabled ? (
                  <Note tone="warn">
                    Carb cycling chưa phù hợp với mục tiêu hiện tại của bạn.{" "}
                    {carbResult.suitable_for}
                  </Note>
                ) : (
                  <>
                    <div className="hg-kv">
                      <span>Tổng calo cả tuần</span>
                      <span className="hg-num-mono" style={{ fontWeight: 600 }}>
                        {carbResult.weekly_totals.calories} / {carbResult.weekly_totals.target_calories}{" "}
                        kcal
                      </span>
                    </div>
                    <div className="hg-kv">
                      <span>Chênh lệch</span>
                      <span>
                        <Delta
                          value={carbResult.weekly_totals.difference}
                          unit={` kcal (${carbResult.weekly_totals.difference_percent}%)`}
                          invert
                        />
                      </span>
                    </div>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Ngày</th>
                            <th>Loại ngày</th>
                            <th>Calo</th>
                            <th>Đạm</th>
                            <th>Tinh bột</th>
                            <th>Béo</th>
                            <th>Lý do</th>
                          </tr>
                        </thead>
                        <tbody>
                          {carbResult.days.map((d, i) => (
                            <tr key={i}>
                              <td className="hg-num-mono">{d.label}</td>
                              <td>
                                <Chip tone={d.day_type.includes("high") ? "gold" : "default"}>
                                  {d.day_type}
                                </Chip>
                              </td>
                              <td className="hg-num">{d.calories}</td>
                              <td className="hg-num">{d.protein_g}g</td>
                              <td className="hg-num" style={{ fontWeight: 600 }}>
                                {d.carbs_g}g
                              </td>
                              <td className="hg-num">{d.fat_g}g</td>
                              <td style={{ fontSize: "12px", color: "#35505c" }}>{d.rationale}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <ul className="benefit-list">
                      {carbResult.principles.map((p, i) => (
                        <li key={i}>
                          <span style={{ color: "#b8860b", marginRight: 6, fontWeight: 800 }}>▪</span>
                          {p}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ================= 5. ĐÁNH GIÁ HẰNG TUẦN ================= */}
      {tab === "weekly" && (
        <div>
          {!loggedIn ? (
            <div className="hg-empty">
              Vui lòng đăng nhập để sử dụng tính năng đánh giá định kỳ hằng tuần.
            </div>
          ) : (
            <>
              {weekForm && (
                <div className="hg-chart-card">
                  <div className="hg-chart-title">
                    Dữ liệu tuần này (tuần bắt đầu {weekForm.week_start})
                  </div>
                  <div className="stats-bar">
                    <Stat label="Buổi tập theo kế hoạch" value={weekForm.planned_sessions} />
                    <Stat label="Lượt đến phòng gym" value={weekForm.actual_visits} gold />
                    <Stat label="Ngày có ghi nhật ký" value={weekForm.logged_workout_days} />
                    <Stat
                      label="Cân nặng gần nhất"
                      value={weekForm.latest_weight_kg ? `${weekForm.latest_weight_kg} kg` : "—"}
                    />
                  </div>
                  {weekForm.previous_checkin && (
                    <Note>
                      <strong>Tuần trước:</strong> cân nặng {weekForm.previous_checkin.avg_weight_kg}kg
                      · {weekForm.previous_checkin.ai_feedback}
                    </Note>
                  )}
                  <Note tone="gold">{weekForm.why_this_matters}</Note>
                </div>
              )}

              <SectionTitle>Phiếu đánh giá tuần</SectionTitle>
              <div className="hg-chart-card">
                {(weekForm?.questions ?? []).map((q: any) => (
                  <div key={q.key}>
                    <label>{q.text}</label>
                    <input
                      className="input-box"
                      type="number"
                      value={weekData[q.key] ?? ""}
                      onChange={(e) => setWeekData({ ...weekData, [q.key]: e.target.value })}
                      placeholder={q.key === "adherence_percent" ? "0-100" : ""}
                    />
                    {q.hint && (
                      <p className="hg-muted" style={{ fontSize: "12px", marginTop: "-6px" }}>
                        {q.hint}
                      </p>
                    )}
                  </div>
                ))}
                <button className="hg-btn-gold" style={{ width: "100%" }} onClick={submitWeek} disabled={busy}>
                  {busy && <span className="hg-spinner" />}
                  Nộp đánh giá &amp; nhận hiệu chỉnh từ AI
                </button>
                <Note>
                  Mỗi tuần chỉ nộp được một lần. Nộp vào Chủ Nhật để AI kịp điều chỉnh kế hoạch cho
                  tuần sau.
                </Note>
              </div>

              {weekResult && (
                <div style={{ marginTop: "18px" }}>
                  <Note tone={weekResult.detected_issue === "on_track" ? "ok" : "gold"}>
                    {weekResult.ai_feedback}
                  </Note>

                  <div className="stats-bar">
                    <Stat label="Tuần" value={String(weekResult.week_start)} />
                    <Stat
                      label="Thay đổi cân nặng"
                      value={
                        weekResult.weight_change_kg != null
                          ? `${weekResult.weight_change_kg > 0 ? "+" : ""}${weekResult.weight_change_kg} kg`
                          : "—"
                      }
                      gold
                    />
                    <Stat label="Tỷ lệ thay đổi" value={`${weekResult.weight_change_percent}%`} />
                    <Stat label="Phát hiện" value={weekResult.issue_label} />
                  </div>

                  <div className="hg-chart-card">
                    <div className="hg-chart-title">
                      Hiệu chỉnh kế hoạch: {weekResult.adjustment.action}
                    </div>
                    <div className="hg-kv">
                      <span>Thay đổi calo</span>
                      <span>
                        <Delta value={weekResult.adjustment.calorie_delta} unit=" kcal" invert />
                      </span>
                    </div>
                    <div className="hg-kv">
                      <span>Calo mục tiêu mới</span>
                      <span className="hg-num-mono" style={{ fontWeight: 700 }}>
                        {weekResult.adjustment.new_target_calories} kcal
                      </span>
                    </div>
                    <Note>{weekResult.adjustment.reason}</Note>
                    {weekResult.adjustment.detail.length > 0 && (
                      <ul className="benefit-list" style={{ marginTop: "10px" }}>
                        {weekResult.adjustment.detail.map((d, i) => (
                          <li key={i}>
                            <span style={{ color: "#0b6e8f", marginRight: 6, fontWeight: 800 }}>▸</span>
                            {d}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {weekResult.monitoring.length > 0 && (
                    <div className="hg-chart-card">
                      <div className="hg-chart-title">Cần theo dõi tuần tới</div>
                      <ul className="benefit-list">
                        {weekResult.monitoring.map((m, i) => (
                          <li key={i}>
                            <span style={{ color: "#b8860b", marginRight: 6, fontWeight: 800 }}>▪</span>
                            {m}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <Note tone="danger">{weekResult.safety_note}</Note>
                  <Note>{weekResult.next_checkin_note}</Note>
                </div>
              )}

              {weekHistory?.trend && (
                <>
                  <SectionTitle>Xu hướng qua các tuần</SectionTitle>
                  <div className="hg-chart-card">
                    <div className="hg-chart-title">Cân nặng &amp; mức tuân thủ dinh dưỡng</div>
                    <LineChart
                      labels={weekHistory.trend.labels}
                      series={[
                        { name: "Cân nặng (kg)", data: weekHistory.trend.weight },
                        { name: "Tuân thủ (%)", data: weekHistory.trend.adherence },
                      ]}
                      yLabelFormatter={(v) => String(Math.round(v))}
                    />
                  </div>

                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Tuần</th>
                          <th>Cân nặng</th>
                          <th>Thay đổi</th>
                          <th>Buổi tập</th>
                          <th>Tuân thủ</th>
                          <th>Phát hiện</th>
                          <th>Hiệu chỉnh</th>
                        </tr>
                      </thead>
                      <tbody>
                        {weekHistory.checkins.map((c: any, i: number) => (
                          <tr key={i}>
                            <td className="hg-num-mono">{c.week_start}</td>
                            <td className="hg-num-mono">{c.avg_weight_kg ?? "—"}</td>
                            <td>
                              {c.weight_change_kg != null ? (
                                <Delta value={c.weight_change_kg} unit="kg" invert />
                              ) : (
                                "—"
                              )}
                            </td>
                            <td className="hg-num">
                              {c.sessions_completed}/{c.sessions_planned}
                            </td>
                            <td className="hg-num">{c.adherence_percent ?? "—"}%</td>
                            <td>
                              <Chip tone={c.detected_issue === "on_track" ? "ok" : "warn"}>
                                {c.detected_issue ?? "—"}
                              </Chip>
                            </td>
                            <td style={{ fontSize: "12.5px" }}>
                              {c.adjustment_type ?? "—"}
                              {c.calorie_delta ? (
                                <div className="hg-exercise-muscle">
                                  {c.calorie_delta > 0 ? "+" : ""}
                                  {c.calorie_delta} kcal
                                </div>
                              ) : null}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}

              {weekHistory && weekHistory.total_checkins === 0 && (
                <div className="hg-empty">
                  Bạn chưa có đánh giá tuần nào. Hãy nộp phiếu đầu tiên vào Chủ Nhật tuần này.
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}