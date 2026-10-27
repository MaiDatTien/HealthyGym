"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { Delta, MacroBar, Metric, ProgressRing, SectionTitle, Toast } from "@/components/ui";
import type { FullPlan, OnboardingFlow, OnboardingStep } from "@/lib/types";

/* ==========================================================================
   AI SMART FITNESS COACH — 4 bước nghiệp vụ
     Bước 1: Thu thập dữ liệu (wizard từng bước hoặc chat)
     Bước 2: Chẩn đoán thể trạng
     Bước 3: Lịch tập cá nhân hoá
     Bước 4: Dinh dưỡng & Nghị ngơi - Phục hồi
   ========================================================================== */

type Profile = Record<string, any>;

const EMPTY_PROFILE: Profile = {
  gender: "",
  age: "",
  height_cm: "",
  weight_kg: "",
  body_fat_percentage: "",
  goal: "cutting",
  activity_level: "moderate",
  training_days_per_week: 4,
  session_minutes: 60,
  training_location: "gym",
  injuries: [] as string[],
  allergies: [] as string[],
};

export default function AICoachPage() {
  const [flow, setFlow] = useState<OnboardingFlow | null>(null);
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [stepIndex, setStepIndex] = useState(0);
  const [plan, setPlan] = useState<FullPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [tab, setTab] = useState<"diagnosis" | "workout" | "nutrition" | "recovery">("diagnosis");
  const [mode, setMode] = useState<"wizard" | "chat">("wizard");

  // Ước tính Body Fat bằng US Navy Method
  const [bfEstimator, setBfEstimator] = useState({ neck: "", waist: "", hip: "" });
  const [showEstimator, setShowEstimator] = useState(false);

  // Hội thoại
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState<{ sender: "ai" | "user"; text: string }[]>([
    {
      sender: "ai",
      text:
        "Chào bạn! Tôi là AI Smart Coach — Huấn luyện viên thể hình và chuyên gia dinh dưỡng ảo của HealthyGym.\n\n" +
        "Tôi sẽ chẩn đoán thể trạng và lập phác đồ 3 trụ cột riêng cho bạn: Lịch tập luyện • Dinh dưỡng • Nghỉ ngơi & Phục hồi.\n\n" +
        "Để bắt đầu, hãy dùng form từng bước bên cạnh cho nhanh và chính xác, hoặc hỏi tôi bất cứ điều gì.",
    },
  ]);

  useEffect(() => {
    fetchGymData("/ai/onboarding").then(setFlow).catch(() => {});
    // Nếu đã có phác đồ đang áp dụng thì hiển thị luôn
    fetchGymData("/ai/plan/my")
      .then((p) => {
        setPlan(p);
        setProfile((prev) => ({
          ...prev,
          height_cm: p.member_diagnosis.height_cm,
          weight_kg: p.member_diagnosis.weight_kg,
          body_fat_percentage: p.member_diagnosis.body_fat_percentage,
          gender: p.member_diagnosis.gender,
          age: p.member_diagnosis.age ?? "",
          goal: p.goal,
        }));
      })
      .catch(() => {});
  }, []);

  const steps: OnboardingStep[] = flow?.steps ?? [];
  const current: OnboardingStep | undefined = steps[stepIndex];
  const requiredFields = flow?.required_fields ?? [];
  const requiredDone = requiredFields.filter((f) => profile[f] !== "" && profile[f] != null).length;

  const setField = (field: string, value: any) =>
    setProfile((prev) => ({ ...prev, [field]: value }));

  const toggleMulti = (field: string, value: string) => {
    setProfile((prev) => {
      const list: string[] = Array.isArray(prev[field]) ? prev[field] : [];
      if (value === "none") return { ...prev, [field]: [] };
      const next = list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
      return { ...prev, [field]: next };
    });
  };

  const canAdvance = (): boolean => {
    if (!current) return false;
    const v = profile[current.field];
    if (current.input_type === "multi") return true; // không bắt buộc
    if (v === "" || v === null || v === undefined) return false;
    if (current.input_type === "number" || current.input_type === "hybrid") {
      const num = Number(v);
      if (Number.isNaN(num)) return false;
      if (current.min !== undefined && num < current.min) return false;
      if (current.max !== undefined && num > current.max) return false;
    }
    return true;
  };

  const estimateBodyFat = async () => {
    try {
      const res = await postGymData("/ai/estimate-body-fat", {
        gender: profile.gender || "male",
        height_cm: Number(profile.height_cm),
        neck_cm: Number(bfEstimator.neck),
        waist_cm: Number(bfEstimator.waist),
        hip_cm: bfEstimator.hip ? Number(bfEstimator.hip) : null,
      });
      setField("body_fat_percentage", res.body_fat_percentage);
      setShowEstimator(false);
      setToast({
        kind: "ok",
        text: `Đã ước tính Body Fat: ${res.body_fat_percentage}% (${res.category_vi}). ${res.accuracy_note}`,
      });
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const generatePlan = async () => {
    const missing = requiredFields.filter((f) => profile[f] === "" || profile[f] == null);
    if (missing.length > 0) {
      setToast({ kind: "err", text: `Còn thiếu chỉ số bắt buộc: ${missing.join(", ")}` });
      return;
    }
    setLoading(true);
    setToast(null);
    try {
      const res = await postGymData("/ai/plan", {
        height_cm: Number(profile.height_cm),
        weight_kg: Number(profile.weight_kg),
        body_fat_percentage: Number(profile.body_fat_percentage),
        gender: profile.gender,
        age: profile.age ? Number(profile.age) : null,
        activity_level: profile.activity_level,
        goal: profile.goal,
        training_days_per_week: Number(profile.training_days_per_week),
        session_minutes: Number(profile.session_minutes),
        training_location: profile.training_location,
        injuries: profile.injuries,
        allergies: profile.allergies,
        save_to_profile: true,
      });
      setPlan(res);
      setTab("diagnosis");
      setToast({
        kind: "ok",
        text: res.saved_to_profile
          ? "Phác đồ đã được tạo và lưu vào hồ sơ của bạn. Theo dõi tiến độ tại mục Tiến Độ."
          : "Phác đồ đã được tạo. Đăng nhập để lưu vào hồ sơ và theo dõi tiến độ.",
      });
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const sendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    const text = chatInput;
    setMessages((prev) => [...prev, { sender: "user", text }]);
    setChatInput("");

    const runDiagnosis = /(xuất|tạo|lập|xem).*(phác đồ|kế hoạch|giáo án)/i.test(text);
    try {
      const res = await postGymData("/ai/chat", {
        message: text,
        profile,
        run_diagnosis: runDiagnosis,
        session_key: "web",
      });
      setMessages((prev) => [...prev, { sender: "ai", text: res.reply }]);
      if (res.plan) {
        setPlan(res.plan);
        setTab("diagnosis");
      }
      if (res.body_fat_percentage) setField("body_fat_percentage", res.body_fat_percentage);
    } catch {
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: "Không kết nối được tới máy chủ. Vui lòng thử lại." },
      ]);
    }
  };

  const d = plan?.member_diagnosis;
  const n = plan?.nutrition_plan;
  const w = plan?.workout_schedule;
  const r = plan?.recovery_protocol;

  return (
    <div>
      <div className="hg-ai-banner">
        <span className="chip">🤖 AI SMART FITNESS COACH — MIỄN PHÍ</span>
        <h2 style={{ marginTop: "0.7rem" }}>Chẩn Đoán Thể Trạng & Phác Đồ Cá Nhân Hoá</h2>
        <p>
          Hệ thống phân tích BMI, tỷ lệ mỡ cơ thể, khối lượng cơ nạc, BMR (Katch-McArdle) và TDEE
          để thiết kế lịch tập theo khoa học, thực đơn Việt Nam định lượng gram và phác đồ phục hồi
          dành riêng cho bạn.
        </p>
        <div className="hg-flex" style={{ marginTop: "1.2rem" }}>
          {["Bước 1 · Thu thập chỉ số", "Bước 2 · Chẩn đoán", "Bước 3 · Lịch tập", "Bước 4 · Dinh dưỡng & Phục hồi"].map(
            (s, i) => (
              <span key={s} className="chip" style={{ fontSize: "0.72rem" }}>
                {s}
              </span>
            )
          )}
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      <div className="hg-flex" style={{ marginBottom: "1.3rem" }}>
        <button
          className={mode === "wizard" ? "hg-btn-emerald" : "hg-btn-ghost"}
          onClick={() => setMode("wizard")}
        >
          📋 Form từng bước
        </button>
        <button
          className={mode === "chat" ? "hg-btn-emerald" : "hg-btn-ghost"}
          onClick={() => setMode("chat")}
        >
          💬 Trò chuyện với AI
        </button>
      </div>

      <div className="hg-grid-2">
        {/* ============ CỘT TRÁI: THU THẬP DỮ LIỆU (BƯỚC 1) ============ */}
        <div className="card" style={{ display: "block" }}>
          {mode === "wizard" ? (
            <>
              <SectionTitle>Bước 1 · Thông số của bạn</SectionTitle>
              <p className="hg-muted" style={{ marginBottom: "1rem" }}>
                Đã thu thập <strong>{requiredDone}</strong>/{requiredFields.length} chỉ số bắt buộc.
              </p>

              <div className="hg-wizard-steps">
                {steps.map((s, i) => (
                  <div
                    key={s.step}
                    className={`hg-wizard-dot ${
                      i < stepIndex ? "done" : i === stepIndex ? "current" : ""
                    }`}
                    title={s.field}
                  />
                ))}
              </div>

              {current ? (
                <div>
                  <div className="hg-flex" style={{ justifyContent: "space-between" }}>
                    <span className="chip">
                      Câu {current.step}/{steps.length}
                    </span>
                    <span className="hg-muted">{current.field}</span>
                  </div>

                  <h3 style={{ fontSize: "1.1rem", margin: "0.9rem 0 0.4rem", whiteSpace: "pre-line" }}>
                    {current.question}
                  </h3>
                  {current.hint && (
                    <p className="hg-muted" style={{ marginBottom: "0.9rem", fontStyle: "italic" }}>
                      {current.hint}
                    </p>
                  )}

                  {/* --- Nhập số --- */}
                  {(current.input_type === "number" || current.input_type === "hybrid") && (
                    <div>
                      <input
                        className="input-box"
                        type="number"
                        min={current.min}
                        max={current.max}
                        value={profile[current.field] ?? ""}
                        onChange={(e) => setField(current.field, e.target.value)}
                        placeholder={`${current.min ?? ""} - ${current.max ?? ""}`}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && canAdvance())
                            setStepIndex((i) => Math.min(i + 1, steps.length - 1));
                        }}
                      />
                      {current.field === "body_fat_percentage" && (
                        <div style={{ marginTop: "-0.3rem" }}>
                          <button
                            className="hg-btn-ghost"
                            style={{ fontSize: "0.82rem" }}
                            onClick={() => setShowEstimator((v) => !v)}
                          >
                            📏 Chưa biết? Ước tính bằng số đo (US Navy Method)
                          </button>

                          {showEstimator && (
                            <div className="hg-note" style={{ marginTop: "0.8rem" }}>
                              <strong>Đo bằng thước dây (cm):</strong>
                              <div style={{ marginTop: "0.6rem" }}>
                                <input
                                  className="input-box"
                                  type="number"
                                  placeholder="Vòng cổ (cm)"
                                  value={bfEstimator.neck}
                                  onChange={(e) =>
                                    setBfEstimator({ ...bfEstimator, neck: e.target.value })
                                  }
                                />
                                <input
                                  className="input-box"
                                  type="number"
                                  placeholder="Vòng eo tại rốn (cm)"
                                  value={bfEstimator.waist}
                                  onChange={(e) =>
                                    setBfEstimator({ ...bfEstimator, waist: e.target.value })
                                  }
                                />
                                {profile.gender === "female" && (
                                  <input
                                    className="input-box"
                                    type="number"
                                    placeholder="Vòng hông (cm) — bắt buộc với nữ"
                                    value={bfEstimator.hip}
                                    onChange={(e) =>
                                      setBfEstimator({ ...bfEstimator, hip: e.target.value })
                                    }
                                  />
                                )}
                                <button
                                  className="hg-btn-gold"
                                  style={{ width: "100%" }}
                                  onClick={estimateBodyFat}
                                  disabled={!bfEstimator.neck || !bfEstimator.waist}
                                >
                                  Tính Body Fat cho tôi
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* --- Chọn một --- */}
                  {current.input_type === "choice" && (
                    <div className="hg-choice-grid">
                      {current.options?.map((o) => (
                        <button
                          key={o.value}
                          className={`hg-choice ${profile[current.field] === o.value ? "selected" : ""}`}
                          onClick={() => {
                            setField(current.field, o.value);
                            setTimeout(
                              () => setStepIndex((i) => Math.min(i + 1, steps.length - 1)),
                              180
                            );
                          }}
                        >
                          {o.label}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* --- Chọn nhiều --- */}
                  {current.input_type === "multi" && (
                    <div className="hg-choice-grid">
                      {current.options?.map((o) => {
                        const list: string[] = profile[current.field] ?? [];
                        const sel = list.includes(o.value);
                        return (
                          <button
                            key={o.value}
                            className={`hg-choice ${sel ? "selected" : ""}`}
                            onClick={() => toggleMulti(current.field, o.value)}
                          >
                            {sel ? "✓ " : ""}
                            {o.label}
                          </button>
                        );
                      })}
                      <button
                        className={`hg-choice ${(profile[current.field] ?? []).length === 0 ? "selected" : ""}`}
                        onClick={() => setField(current.field, [])}
                      >
                        Không có
                      </button>
                    </div>
                  )}

                  <div className="hg-flex" style={{ marginTop: "1.2rem", justifyContent: "space-between" }}>
                    <button
                      className="hg-btn-ghost"
                      onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
                      disabled={stepIndex === 0}
                    >
                      ← Quay lại
                    </button>
                    {stepIndex < steps.length - 1 ? (
                      <button
                        className="hg-btn-emerald"
                        onClick={() => setStepIndex((i) => i + 1)}
                        disabled={!canAdvance()}
                      >
                        Tiếp theo →
                      </button>
                    ) : (
                      <button className="hg-btn-gold" onClick={generatePlan} disabled={loading}>
                        {loading && <span className="hg-spinner" />}
                        ✨ Xuất phác đồ AI
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="hg-empty">Đang tải bộ câu hỏi…</div>
              )}

              {/* Nút xuất phác đồ luôn sẵn sàng khi đã đủ chỉ số */}
              {stepIndex < steps.length - 1 && requiredDone === requiredFields.length && (
                <button
                  className="hg-btn-gold"
                  style={{ width: "100%", marginTop: "1rem" }}
                  onClick={generatePlan}
                  disabled={loading}
                >
                  {loading && <span className="hg-spinner" />}
                  ✨ Đã đủ chỉ số — Xuất phác đồ ngay
                </button>
              )}
            </>
          ) : (
            <>
              <SectionTitle>Trò chuyện cùng AI Smart Coach</SectionTitle>
              <div className="hg-chat-window">
                {messages.map((m, i) => (
                  <div key={i} className={`hg-bubble ${m.sender}`}>
                    {m.text}
                  </div>
                ))}
              </div>
              <form onSubmit={sendChat} className="hg-flex" style={{ alignItems: "stretch" }}>
                <input
                  className="input-box"
                  style={{ marginBottom: 0, flex: 1 }}
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="VD: Tôi nam 29 tuổi, cao 172cm, nặng 75kg, muốn giảm mỡ…"
                />
                <button type="submit" className="hg-btn-emerald">
                  Gửi
                </button>
              </form>
              <p className="hg-muted" style={{ marginTop: "0.7rem" }}>
                AI sẽ hỏi lần lượt các chỉ số còn thiếu trước khi đưa ra phác đồ — đúng quy trình tư
                vấn của một PT chuyên nghiệp.
              </p>
            </>
          )}
        </div>

        {/* ============ CỘT PHẢI: KẾT QUẢ ============ */}
        <div className="card" style={{ display: "block" }}>
          {!plan ? (
            <div className="hg-empty">
              <div style={{ fontSize: "2.6rem", marginBottom: "0.6rem" }}>🧬</div>
              <h3 style={{ marginBottom: "0.5rem" }}>Chưa có phác đồ</h3>
              <p>
                Hoàn thành các chỉ số ở cột bên trái rồi bấm <strong>Xuất phác đồ AI</strong> để nhận
                chẩn đoán thể trạng, lịch tập và thực đơn cá nhân hoá.
              </p>
            </div>
          ) : (
            <>
              <SectionTitle>Tóm tắt phác đồ</SectionTitle>
              <div className="hg-verdict" style={{ whiteSpace: "pre-line" }}>
                {plan.summary_text}
              </div>

              {plan.saved_to_profile && (
                <div className="hg-note ok" style={{ marginBottom: "1.2rem" }}>
                  ✓ Phác đồ đã lưu vào hồ sơ. Theo dõi tiến độ tại mục <strong>Tiến Độ</strong>.
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* ============ KẾT QUẢ CHI TIẾT ============ */}
      {plan && d && n && w && r && (
        <div style={{ marginTop: "2.4rem" }}>
          <div className="hg-tabs">
            {[
              { id: "diagnosis", label: "🧬 Bước 2 · Chẩn đoán" },
              { id: "workout", label: "🏋️ Bước 3 · Lịch tập" },
              { id: "nutrition", label: "🥗 Bước 4 · Dinh dưỡng" },
              { id: "recovery", label: "😴 Nghỉ ngơi & Phục hồi" },
            ].map((t) => (
              <button
                key={t.id}
                className={`hg-tab ${tab === t.id ? "active" : ""}`}
                onClick={() => setTab(t.id as any)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* ---------------- CHẨN ĐOÁN ---------------- */}
          {tab === "diagnosis" && (
            <div>
              <div className="hg-metric-grid">
                <Metric label="BMI" value={d.bmi} note={d.bmi_category} />
                <Metric
                  label="Body Fat"
                  value={d.body_fat_percentage}
                  unit="%"
                  note={d.body_fat_category}
                  gold
                />
                <Metric label="Cơ nạc (LBM)" value={d.lean_body_mass_kg} unit="kg" note="Khối lượng cơ" />
                <Metric label="Khối mỡ" value={d.fat_mass_kg} unit="kg" note="Fat Mass" />
                <Metric label="BMR" value={d.bmr_kcal} unit="kcal" note="Katch-McArdle" />
                <Metric label="TDEE" value={d.tdee_kcal} unit="kcal" note={`Hệ số ×${d.activity_multiplier}`} gold />
                <Metric label="FFMI" value={d.ffmi_normalized} note={d.ffmi_interpretation} />
                <Metric
                  label="Lộ trình"
                  value={d.estimated_weeks_to_goal}
                  unit="tuần"
                  note={`~${d.estimated_months_to_goal} tháng`}
                  gold
                />
              </div>

              <div className="hg-verdict">
                <h3>Nhận định chuyên môn</h3>
                <p style={{ marginBottom: "0.8rem" }}>
                  <strong>Tạng người:</strong> {d.body_type_classification}
                </p>
                <p>{d.ai_assessment_summary}</p>
                <div className="hg-flex" style={{ marginTop: "1rem" }}>
                  <span className="chip">Chất lượng cơ: {d.muscle_quality}</span>
                  <span className="chip chip-gold">
                    Mục tiêu Body Fat: {d.target_body_fat_percentage}%
                  </span>
                  {d.fat_to_lose_kg > 0 && (
                    <span className="chip chip-warn">Cần giảm {d.fat_to_lose_kg}kg mỡ</span>
                  )}
                  {d.muscle_to_gain_kg > 0 && (
                    <span className="chip chip-ok">Cần tăng {d.muscle_to_gain_kg}kg cơ</span>
                  )}
                </div>
              </div>

              {d.safety_warnings?.length > 0 && (
                <div className="hg-warning-box">
                  <h4>⚠️ Lưu ý an toàn dành riêng cho bạn</h4>
                  <ul>
                    {d.safety_warnings.map((wn, i) => (
                      <li key={i}>{wn}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="hg-note gold">{plan.disclaimer}</div>
            </div>
          )}

          {/* ---------------- LỊCH TẬP ---------------- */}
          {tab === "workout" && (
            <div>
              <div className="hg-verdict">
                <h3>{w.split_type}</h3>
                <p>{w.split_rationale}</p>
                <div className="hg-flex" style={{ marginTop: "1rem" }}>
                  <span className="chip">{w.training_days_per_week} buổi/tuần</span>
                  <span className="chip">~{w.session_minutes} phút/buổi</span>
                  <span className="chip chip-gold">RPE mục tiêu: {w.target_rpe}</span>
                </div>
              </div>

              <div className="hg-grid-2" style={{ marginBottom: "1.4rem" }}>
                <div className="hg-note">
                  <strong>Tăng tiến (Progressive Overload):</strong>
                  <p style={{ marginTop: "0.4rem" }}>{w.progression_rule}</p>
                </div>
                <div className="hg-note">
                  <strong>Khối lượng &amp; nghỉ:</strong>
                  <p style={{ marginTop: "0.4rem" }}>{w.rep_guidance}</p>
                  <p style={{ marginTop: "0.3rem" }}>{w.rest_guidance}</p>
                  <p style={{ marginTop: "0.3rem", fontStyle: "italic" }}>{w.volume_note}</p>
                </div>
              </div>

              {w.exercise_substitutions?.length > 0 && (
                <div className="hg-warning-box">
                  <h4>🔄 Bài tập đã được điều chỉnh cho phù hợp với bạn</h4>
                  <ul>
                    {w.exercise_substitutions.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {w.sessions.map((s, si) => (
                <div key={si} className="hg-session">
                  <div className="hg-session-head">
                    <div>
                      <span className="hg-session-day">{s.day}</span>
                      <div className="hg-session-focus">{s.focus}</div>
                      <div className="hg-session-meta">
                        {s.exercises.length} bài tập · ước tính ~{Math.round(s.estimated_minutes)} phút
                      </div>
                    </div>
                  </div>

                  <div className="hg-phase">
                    <strong>Khởi động (Warm-up &amp; Mobility):</strong> {s.warmup}
                  </div>

                  <div className="table-wrap" style={{ padding: "0.6rem", marginBottom: "0.8rem" }}>
                    <table>
                      <thead>
                        <tr>
                          <th style={{ minWidth: 230 }}>Bài tập</th>
                          <th>Nhóm cơ</th>
                          <th style={{ whiteSpace: "nowrap" }}>Sets × Reps</th>
                          <th style={{ whiteSpace: "nowrap" }}>Nghỉ</th>
                          <th>Lưu ý kỹ thuật</th>
                        </tr>
                      </thead>
                      <tbody>
                        {s.exercises.map((e, ei) => (
                          <tr key={ei}>
                            <td>
                              <div className="hg-exercise-name">{e.name}</div>
                              <div className="hg-exercise-muscle">{e.type}</div>
                            </td>
                            <td style={{ fontSize: "0.85rem" }}>{e.target_muscle}</td>
                            <td>
                              <span className="hg-sets-badge">
                                {e.sets} × {e.reps}
                              </span>
                            </td>
                            <td style={{ fontSize: "0.85rem", whiteSpace: "nowrap" }}>
                              {e.rest_seconds}s
                            </td>
                            <td className="hg-exercise-note">{e.notes}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="hg-phase">
                    <strong>Giãn cơ (Cool-down):</strong> {s.cooldown}
                  </div>
                </div>
              ))}

              <div className="hg-session">
                <h3 style={{ fontSize: "1.1rem", marginBottom: "0.7rem" }}>
                  🏃 Cardio — {w.cardio.type}
                </h3>
                <ul className="benefit-list">
                  {w.cardio.details.map((c, i) => (
                    <li key={i}>
                      <span style={{ color: "#0e6d8c", marginRight: 6, fontWeight: 800 }}>▸</span>
                      {c}
                    </li>
                  ))}
                </ul>
                <div className="hg-note" style={{ marginTop: "0.8rem" }}>
                  {w.cardio.low_impact_note}
                </div>
              </div>

              {w.extra_notes?.length > 0 && (
                <div className="hg-note gold">
                  {w.extra_notes.map((nt, i) => (
                    <p key={i} style={{ marginBottom: i < w.extra_notes.length - 1 ? "0.6rem" : 0 }}>
                      {nt}
                    </p>
                  ))}
                </div>
              )}

              <div className="hg-note" style={{ marginTop: "1rem" }}>
                {w.weekly_structure}
              </div>
            </div>
          )}

          {/* ---------------- DINH DƯỠNG ---------------- */}
          {tab === "nutrition" && (
            <div>
              <div className="hg-metric-grid">
                <Metric label="Calo mục tiêu" value={n.target_daily_calories} unit="kcal" gold />
                <Metric
                  label="Điều chỉnh"
                  value={`${n.caloric_adjustment > 0 ? "+" : ""}${n.caloric_adjustment}`}
                  unit="kcal"
                  note={n.caloric_adjustment < 0 ? "Thâm hụt" : "Thặng dư"}
                />
                <Metric label="Protein" value={n.macros.protein_grams} unit="g" note={`${n.macros.protein_percent}% calo`} />
                <Metric label="Carbs" value={n.macros.carbs_grams} unit="g" note={`${n.macros.carbs_percent}% calo`} gold />
                <Metric label="Fat" value={n.macros.fat_grams} unit="g" note={`${n.macros.fat_percent}% calo`} />
                <Metric label="Nước/ngày" value={n.daily_water_liters} unit="lít" note={`~${n.water_plan.glasses_250ml} ly 250ml`} />
              </div>

              <div className="hg-verdict">
                <h3>Chiến lược năng lượng</h3>
                <p>{n.caloric_strategy}</p>
                <p className="hg-muted" style={{ marginTop: "0.5rem" }}>
                  BMR {n.bmr_kcal} kcal → TDEE {n.tdee_kcal} kcal → mục tiêu{" "}
                  <strong>{n.target_daily_calories} kcal/ngày</strong>.
                </p>
              </div>

              <div className="hg-chart-card">
                <div className="hg-chart-title">Phân bổ đa lượng (Macros)</div>
                <p className="hg-chart-sub">
                  Protein {n.macros.protein_per_kg}g/kg cân nặng · {n.macros.protein_per_kg_lbm}g/kg khối cơ nạc
                </p>
                <MacroBar
                  protein={n.macros.protein_grams}
                  carbs={n.macros.carbs_grams}
                  fat={n.macros.fat_grams}
                />
                <div style={{ marginTop: "1.2rem" }}>
                  <div className="hg-kv">
                    <span>Đạm (Protein)</span>
                    <span>{n.macro_guidance.protein}</span>
                  </div>
                  <div className="hg-kv">
                    <span>Chất béo (Fat)</span>
                    <span>{n.macro_guidance.fat}</span>
                  </div>
                  <div className="hg-kv">
                    <span>Tinh bột (Carbs)</span>
                    <span>{n.macro_guidance.carbs}</span>
                  </div>
                </div>
              </div>

              <SectionTitle>Thực đơn mẫu trong ngày</SectionTitle>
              <p className="hg-muted" style={{ marginBottom: "1rem" }}>
                Định lượng theo gram thực phẩm thuần Việt, dễ mua và dễ chuẩn bị.
              </p>

              {n.meal_substitutions?.length > 0 && (
                <div className="hg-note ok" style={{ marginBottom: "1rem" }}>
                  <strong>Đã thay thế theo dị ứng của bạn:</strong>
                  <ul style={{ marginTop: "0.4rem" }}>
                    {n.meal_substitutions.map((s, i) => (
                      <li key={i} style={{ fontSize: "0.87rem" }}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {n.sample_meals.map((m, i) => (
                <div key={i} className="hg-meal">
                  <div className="hg-meal-head">
                    <span className="hg-meal-name">{m.meal_name}</span>
                    <span className="hg-meal-time">🕐 {m.time}</span>
                  </div>
                  <ul className="hg-food-list">
                    {m.foods.map((f, fi) => (
                      <li key={fi}>{f}</li>
                    ))}
                  </ul>
                  <div className="hg-meal-macros">
                    <span className="hg-macro-pill">🔥 {m.calories} kcal</span>
                    <span className="hg-macro-pill p">Đạm {m.protein_g}g</span>
                    <span className="hg-macro-pill c">Carb {m.carbs_g}g</span>
                    <span className="hg-macro-pill f">Fat {m.fat_g}g</span>
                  </div>
                  {m.tip && (
                    <p className="hg-muted" style={{ marginTop: "0.6rem", fontStyle: "italic" }}>
                      💡 {m.tip}
                    </p>
                  )}
                </div>
              ))}

              <div className="hg-grid-2" style={{ marginTop: "1.5rem" }}>
                <div className="hg-chart-card">
                  <div className="hg-chart-title">✅ Thực phẩm nên ưu tiên</div>
                  <ul className="benefit-list">
                    {n.foods_to_prioritize.map((f, i) => (
                      <li key={i}>
                        <span style={{ color: "#0f8a6a", marginRight: 6, fontWeight: 800 }}>✓</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="hg-chart-card">
                  <div className="hg-chart-title">⛔ Nên hạn chế</div>
                  <ul className="benefit-list">
                    {n.foods_to_limit.map((f, i) => (
                      <li key={i}>
                        <span style={{ color: "#c02a3f", marginRight: 6, fontWeight: 800 }}>✕</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="hg-chart-card">
                <div className="hg-chart-title">💧 Kế hoạch uống nước — {n.daily_water_liters} lít/ngày</div>
                <p className="hg-chart-sub">
                  Nền {n.water_plan.base_liters}L + bù tập luyện {n.water_plan.training_bonus_liters}L
                </p>
                <ul className="benefit-list">
                  {n.water_plan.schedule.map((s, i) => (
                    <li key={i}>
                      <span style={{ color: "#1391b4", marginRight: 6, fontWeight: 800 }}>▸</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="hg-chart-card">
                <div className="hg-chart-title">📋 Nguyên tắc ăn uống</div>
                <ul className="benefit-list">
                  {n.eating_rules.map((rule, i) => (
                    <li key={i}>
                      <span style={{ color: "#c9a227", marginRight: 6, fontWeight: 800 }}>▪</span>
                      {rule}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* ---------------- PHỤC HỒI ---------------- */}
          {tab === "recovery" && (
            <div>
              <div className="hg-metric-grid">
                <Metric label="Giấc ngủ" value={r.recommended_sleep_hours} gold />
                <Metric label="Giờ đi ngủ" value={r.ideal_bedtime} note="Khung giờ vàng cho GH" />
                <Metric label="Thức dậy" value={r.wake_time} />
                <Metric label="NEAT mục tiêu" value={r.neat_target_steps.toLocaleString("vi-VN")} unit="bước" gold />
              </div>

              <div className="hg-grid-2" style={{ marginBottom: "1.5rem" }}>
                <div className="hg-chart-card">
                  <div className="hg-chart-title">🗓️ Lịch tập &amp; nghỉ</div>
                  <div className="hg-kv">
                    <span>Ngày tập</span>
                    <span>{r.training_days.join(", ")}</span>
                  </div>
                  <div className="hg-kv">
                    <span>Ngày nghỉ</span>
                    <span>{r.rest_days.join(", ") || "Không có"}</span>
                  </div>
                </div>
                <div className="hg-chart-card">
                  <div className="hg-chart-title">😴 Phác đồ giấc ngủ</div>
                  <ul className="benefit-list" style={{ fontSize: "0.87rem" }}>
                    {r.sleep_protocol.map((s, i) => (
                      <li key={i}>
                        <span style={{ color: "#0e6d8c", marginRight: 6 }}>▸</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="hg-chart-card">
                <div className="hg-chart-title">🚶 Phục hồi chủ động (Active Recovery)</div>
                <ul className="benefit-list">
                  {r.active_recovery_tips.map((t, i) => (
                    <li key={i}>
                      <span style={{ color: "#1391b4", marginRight: 6, fontWeight: 800 }}>▸</span>
                      {t}
                    </li>
                  ))}
                </ul>
              </div>

              <SectionTitle>Thực phẩm bổ sung (nếu cần)</SectionTitle>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Loại</th>
                      <th>Liều dùng</th>
                      <th>Thời điểm</th>
                      <th>Vì sao</th>
                      <th>Ưu tiên</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.supplements.map((s, i) => (
                      <tr key={i}>
                        <td>
                          <strong>{s.name}</strong>
                        </td>
                        <td style={{ fontSize: "0.85rem" }}>{s.dose}</td>
                        <td style={{ fontSize: "0.85rem" }}>{s.when}</td>
                        <td style={{ fontSize: "0.82rem", color: "#3d5768" }}>{s.why}</td>
                        <td>
                          <span className={`chip ${s.priority.includes("Nên") ? "chip-ok" : ""}`}>
                            {s.priority}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="hg-warning-box">
                <h4>🚨 Dấu hiệu tập quá sức (Overtraining) — cần giảm tải ngay</h4>
                <ul>
                  {r.overtraining_warning_signs.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>

              <div className="hg-note">
                <strong>Quản lý căng thẳng:</strong>
                <ul className="benefit-list" style={{ marginTop: "0.5rem" }}>
                  {r.stress_management.map((s, i) => (
                    <li key={i}>
                      <span style={{ color: "#c9a227", marginRight: 6 }}>▪</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}