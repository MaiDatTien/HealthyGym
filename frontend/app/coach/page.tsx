"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { LineChart, Metric, SectionTitle, Toast } from "@/components/ui";

/* ==========================================================================
   DASHBOARD HUẤN LUYỆN VIÊN
     - Lịch dạy hôm nay, khung giờ sắp tới
     - Danh sách học viên kèm chỉ số mới nhất và phác đồ AI đang áp dụng
     - Xem chi tiết hồ sơ sức khỏe + điều chỉnh/đánh giá sau buổi tập
   ========================================================================== */

export default function CoachPage() {
  const [overview, setOverview] = useState<any>(null);
  const [trainees, setTrainees] = useState<any[]>([]);
  const [detail, setDetail] = useState<any>(null);
  const [allowed, setAllowed] = useState(true);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const [noteForm, setNoteForm] = useState({
    performance: "good",
    content: "",
    next_focus: "",
  });

  const load = () => {
    fetchGymData("/pt/coach/overview")
      .then(setOverview)
      .catch(() => setAllowed(false));
    fetchGymData("/pt/coach/trainees").then(setTrainees).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  const openTrainee = async (memberId: number) => {
    try {
      const res = await fetchGymData(`/pt/coach/trainees/${memberId}`);
      setDetail(res);
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const submitNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    try {
      const res = await postGymData("/pt/coach/notes", {
        member_id: detail.member.id,
        performance: noteForm.performance,
        content: noteForm.content,
        next_focus: noteForm.next_focus || null,
      });
      setToast({ kind: "ok", text: res.message });
      setNoteForm({ performance: "good", content: "", next_focus: "" });
      openTrainee(detail.member.id);
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  if (!allowed) {
    return (
      <div className="card" style={{ maxWidth: 460, margin: "3rem auto", textAlign: "center" }}>
        <h3 style={{ marginBottom: "0.6rem" }}>Khu vực dành cho Huấn luyện viên</h3>
        <p className="hg-muted" style={{ marginBottom: "1.2rem" }}>
          Vui lòng đăng nhập bằng tài khoản HLV hoặc Quản trị viên.
        </p>
        <a href="/login" className="hg-btn-emerald">
          Đăng nhập
        </a>
      </div>
    );
  }

  const hist = detail?.metrics_history ?? [];
  const plan = detail?.ai_plan;

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">COACH DASHBOARD</span>
          <h1 style={{ marginTop: "0.4rem" }}>
            {overview?.trainer?.full_name ?? "Bảng điều khiển Huấn luyện viên"}
          </h1>
          <p className="hg-muted">{overview?.trainer?.specialty}</p>
        </div>
        <div className="hg-flex">
          {overview?.trainer?.certifications && (
            <span className="chip chip-gold" style={{ maxWidth: 340 }}>
              🎓 {overview.trainer.certifications}
            </span>
          )}
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      {overview && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="hg-metric-label">Học viên phụ trách</div>
            <strong style={{ fontSize: "1.8rem", color: "#0a3d55" }}>
              {overview.stats.total_trainees}
            </strong>
          </div>
          <div className="stat-item gold">
            <div className="hg-metric-label">Buổi dạy hôm nay</div>
            <strong style={{ fontSize: "1.8rem", color: "#a8841a" }}>
              {overview.stats.sessions_today}
            </strong>
          </div>
          <div className="stat-item">
            <div className="hg-metric-label">Lịch sắp tới</div>
            <strong style={{ fontSize: "1.8rem", color: "#0a3d55" }}>
              {overview.stats.upcoming_sessions}
            </strong>
          </div>
          <div className="stat-item">
            <div className="hg-metric-label">Tổng khung giờ đã mở</div>
            <strong style={{ fontSize: "1.8rem", color: "#0e6d8c" }}>
              {overview.stats.total_slots_opened}
            </strong>
          </div>
        </div>
      )}

      {/* ---------- LỊCH DẠY HÔM NAY ---------- */}
      <SectionTitle>Lịch dạy hôm nay</SectionTitle>
      {overview?.today_schedule?.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Giờ</th>
                <th>Học viên</th>
                <th>Mục tiêu buổi tập</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {overview.today_schedule.map((s: any) => (
                <tr key={s.booking_id}>
                  <td style={{ whiteSpace: "nowrap", fontWeight: 800, color: "#0e6d8c" }}>
                    {new Date(s.start_time).toLocaleTimeString("vi-VN", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                  <td>
                    <button
                      className="hg-btn-ghost"
                      onClick={() => openTrainee(s.member_id)}
                      style={{ padding: "0.3rem 0.7rem", fontSize: "0.82rem" }}
                    >
                      {s.member_name}
                    </button>
                  </td>
                  <td className="hg-muted">{s.goal_note || "—"}</td>
                  <td>
                    <span className={`chip ${s.status === "completed" ? "chip-ok" : ""}`}>
                      {s.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="hg-empty">Hôm nay bạn chưa có buổi dạy nào.</div>
      )}

      {/* ---------- DANH SÁCH HỌC VIÊN ---------- */}
      <SectionTitle>Học viên đang phụ trách ({trainees.length})</SectionTitle>
      {trainees.length === 0 ? (
        <div className="hg-empty">Chưa có học viên nào được gán cho bạn.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Học viên</th>
                <th>Chỉ số mới nhất</th>
                <th>Phác đồ AI</th>
                <th>Chấn thương / Dị ứng</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {trainees.map((t) => (
                <tr key={t.member_id}>
                  <td>
                    <div className="hg-exercise-name">{t.full_name}</div>
                    <div className="hg-exercise-muscle">
                      {t.phone} · {t.status}
                    </div>
                  </td>
                  <td style={{ fontSize: "0.85rem" }}>
                    {t.latest_metric ? (
                      <>
                        <div>
                          <strong>{t.latest_metric.weight_kg}kg</strong> ·{" "}
                          {t.latest_metric.body_fat_percentage}% mỡ
                        </div>
                        <div className="hg-muted">
                          BMI {t.latest_metric.bmi} · {t.latest_metric.body_type}
                        </div>
                      </>
                    ) : (
                      <span className="hg-muted">Chưa đo</span>
                    )}
                  </td>
                  <td style={{ fontSize: "0.85rem" }}>
                    {t.ai_plan ? (
                      <>
                        <div>
                          <strong>{t.ai_plan.goal}</strong> · {t.ai_plan.target_daily_calories} kcal
                        </div>
                        <div className="hg-muted">{t.ai_plan.split_type}</div>
                      </>
                    ) : (
                      <span className="hg-muted">Chưa có phác đồ</span>
                    )}
                  </td>
                  <td style={{ fontSize: "0.82rem" }}>
                    {t.ai_plan?.injuries ? (
                      <span className="chip chip-warn">{t.ai_plan.injuries}</span>
                    ) : (
                      <span className="hg-muted">Không</span>
                    )}
                    {t.ai_plan?.allergies && (
                      <div style={{ marginTop: "0.3rem" }}>
                        <span className="chip chip-danger">Dị ứng: {t.ai_plan.allergies}</span>
                      </div>
                    )}
                  </td>
                  <td>
                    <button className="hg-btn-emerald" onClick={() => openTrainee(t.member_id)}>
                      Xem hồ sơ
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ---------- CHI TIẾT HỌC VIÊN ---------- */}
      {detail && (
        <div style={{ marginTop: "2rem" }}>
          <div className="hg-flex" style={{ justifyContent: "space-between" }}>
            <SectionTitle>Hồ sơ sức khỏe — {detail.member.full_name}</SectionTitle>
            <button className="hg-btn-ghost" onClick={() => setDetail(null)}>
              Đóng
            </button>
          </div>

          {hist.length > 0 && (
            <>
              <div className="hg-metric-grid">
                <Metric
                  label="Cân nặng hiện tại"
                  value={hist[hist.length - 1].weight_kg}
                  unit="kg"
                  note={hist[hist.length - 1].measured_at}
                />
                <Metric
                  label="Body Fat"
                  value={hist[hist.length - 1].body_fat_percentage}
                  unit="%"
                  gold
                />
                <Metric label="Khối cơ" value={hist[hist.length - 1].muscle_mass_kg} unit="kg" />
                <Metric label="BMI" value={hist[hist.length - 1].bmi} />
                <Metric label="TDEE" value={hist[hist.length - 1].tdee_kcal} unit="kcal" gold />
              </div>

              <div className="hg-chart-card">
                <div className="hg-chart-title">Diễn biến chỉ số qua các lần đo</div>
                <LineChart
                  labels={hist.map((h: any) => h.measured_at)}
                  series={[
                    { name: "Cân nặng (kg)", data: hist.map((h: any) => h.weight_kg) },
                    { name: "Body Fat (%)", data: hist.map((h: any) => h.body_fat_percentage) },
                  ]}
                  colors={["#0e6d8c", "#c9a227"]}
                />
              </div>
            </>
          )}

          {plan && (
            <div className="hg-verdict">
              <h3>Phác đồ AI đang áp dụng</h3>
              <div className="hg-flex" style={{ marginBottom: "0.7rem" }}>
                <span className="chip">{plan.goal}</span>
                <span className="chip">{plan.split_type}</span>
                <span className="chip chip-gold">{plan.target_daily_calories} kcal/ngày</span>
                <span className="chip">
                  P {plan.macros.protein_grams}g / C {plan.macros.carbs_grams}g / F{" "}
                  {plan.macros.fat_grams}g
                </span>
              </div>
              {plan.injuries && (
                <p style={{ color: "#c2410c", fontWeight: 700 }}>
                  ⚠️ Chấn thương: {plan.injuries}
                </p>
              )}
              {plan.allergies && (
                <p style={{ color: "#c02a3f", fontWeight: 700 }}>
                  ⚠️ Dị ứng thực phẩm: {plan.allergies}
                </p>
              )}
              {plan.diagnosis?.ai_assessment_summary && (
                <p style={{ marginTop: "0.6rem" }}>{plan.diagnosis.ai_assessment_summary}</p>
              )}
            </div>
          )}

          {/* Đánh giá của HLV */}
          <div className="hg-grid-2">
            <div className="hg-chart-card">
              <div className="hg-chart-title">📝 Ghi đánh giá sau buổi tập</div>
              <form onSubmit={submitNote}>
                <select
                  className="input-box"
                  value={noteForm.performance}
                  onChange={(e) => setNoteForm({ ...noteForm, performance: e.target.value })}
                >
                  <option value="excellent">Xuất sắc</option>
                  <option value="good">Tốt</option>
                  <option value="needs_work">Cần cải thiện</option>
                </select>
                <textarea
                  className="input-box"
                  rows={4}
                  placeholder="Nhận xét chi tiết về buổi tập *"
                  value={noteForm.content}
                  onChange={(e) => setNoteForm({ ...noteForm, content: e.target.value })}
                  required
                />
                <input
                  className="input-box"
                  placeholder="Trọng tâm buổi tới"
                  value={noteForm.next_focus}
                  onChange={(e) => setNoteForm({ ...noteForm, next_focus: e.target.value })}
                />
                <button className="hg-btn-emerald" style={{ width: "100%" }} type="submit">
                  Lưu đánh giá
                </button>
              </form>
            </div>

            <div className="hg-chart-card">
              <div className="hg-chart-title">Lịch sử đánh giá ({detail.coach_notes?.length ?? 0})</div>
              {(detail.coach_notes ?? []).length === 0 ? (
                <div className="hg-empty">Chưa có đánh giá nào.</div>
              ) : (
                detail.coach_notes.map((nt: any) => (
                  <div
                    key={nt.id}
                    style={{
                      paddingBottom: "0.9rem",
                      marginBottom: "0.9rem",
                      borderBottom: "1px dashed #dbe9f0",
                    }}
                  >
                    <div className="hg-flex" style={{ justifyContent: "space-between" }}>
                      <span
                        className={`chip ${
                          nt.performance === "excellent"
                            ? "chip-ok"
                            : nt.performance === "needs_work"
                            ? "chip-warn"
                            : ""
                        }`}
                      >
                        {nt.performance === "excellent"
                          ? "Xuất sắc"
                          : nt.performance === "needs_work"
                          ? "Cần cải thiện"
                          : "Tốt"}
                      </span>
                      <span className="hg-muted">{nt.note_date}</span>
                    </div>
                    <p style={{ fontSize: "0.88rem", marginTop: "0.5rem" }}>{nt.content}</p>
                    {nt.next_focus && (
                      <p className="hg-muted" style={{ fontSize: "0.83rem", fontStyle: "italic" }}>
                        Trọng tâm tiếp theo: {nt.next_focus}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Nhật ký tập luyện của học viên */}
          <SectionTitle>Nhật ký tập luyện gần đây</SectionTitle>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ngày</th>
                  <th>Bài tập</th>
                  <th>Sets × Reps</th>
                  <th>Tạ</th>
                  <th>RPE</th>
                </tr>
              </thead>
              <tbody>
                {(detail.recent_workouts ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", color: "#6b8598" }}>
                      Chưa có nhật ký.
                    </td>
                  </tr>
                ) : (
                  detail.recent_workouts.map((wk: any, i: number) => (
                    <tr key={i}>
                      <td style={{ whiteSpace: "nowrap" }}>{wk.log_date}</td>
                      <td className="hg-exercise-name">{wk.exercise_name}</td>
                      <td>
                        <span className="hg-sets-badge">
                          {wk.sets} × {wk.reps}
                        </span>
                      </td>
                      <td>
                        <strong>{wk.weight_kg ?? "—"}</strong> kg
                      </td>
                      <td>{wk.rpe ?? "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}