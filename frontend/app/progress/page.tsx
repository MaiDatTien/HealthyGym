"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { BarChart, Delta, LineChart, Metric, ProgressRing, SectionTitle, Toast } from "@/components/ui";
import type { ProgressCharts, ProgressSummary, WorkoutLogEntry } from "@/lib/types";

/* ==========================================================================
   DASHBOARD HỘI VIÊN & THEO DÕI TIẾN ĐỘ
     - Biểu đồ Cân nặng / % Body Fat / Khối lượng cơ theo tuần
     - Nhật ký tập luyện (Progressive Overload) + Kỷ lục cá nhân
     - Nhật ký Calo / Nước / Giấc ngủ / Bước chân
     - Mã QR Check-in điện tử
   ========================================================================== */

type Tab = "charts" | "log" | "checkin";

export default function ProgressPage() {
  const [charts, setCharts] = useState<ProgressCharts | null>(null);
  const [summary, setSummary] = useState<ProgressSummary | null>(null);
  const [logs, setLogs] = useState<WorkoutLogEntry[]>([]);
  const [records, setRecords] = useState<any[]>([]);
  const [qr, setQr] = useState<any>(null);
  const [loggedIn, setLoggedIn] = useState(true);
  const [tab, setTab] = useState<Tab>("charts");
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [range, setRange] = useState(180);

  // Form nhập chỉ số mới
  const [metricForm, setMetricForm] = useState({
    weight_kg: "",
    body_fat_percentage: "",
    waist_cm: "",
    muscle_mass_kg: "",
    note: "",
  });

  // Form nhật ký tập luyện
  const [logForm, setLogForm] = useState({
    exercise_name: "",
    session_focus: "Upper / Lower Split",
    sets: "4",
    reps: "10",
    weight_kg: "",
    rpe: "8",
    duration_minutes: "60",
    notes: "",
  });

  // Form nhật ký dinh dưỡng
  const [dayForm, setDayForm] = useState({
    calories_in: "",
    protein_g: "",
    water_liters: "",
    sleep_hours: "",
    steps: "",
    weight_kg: "",
  });

  const loadAll = () => {
    fetchGymData(`/progress/charts?days=${range}`)
      .then(setCharts)
      .catch(() => setLoggedIn(false));
    fetchGymData("/progress/summary").then(setSummary).catch(() => {});
    fetchGymData("/progress/workout-logs?limit=40").then(setLogs).catch(() => {});
    fetchGymData("/progress/workout-logs/personal-records").then(setRecords).catch(() => {});
    fetchGymData("/pt/checkin/qr").then(setQr).catch(() => {});
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range]);

  const submitMetric = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const last = summary?.latest_metric;
      const res = await postGymData("/progress/metrics", {
        height_cm: 172,
        weight_kg: Number(metricForm.weight_kg),
        body_fat_percentage: metricForm.body_fat_percentage
          ? Number(metricForm.body_fat_percentage)
          : null,
        waist_cm: metricForm.waist_cm ? Number(metricForm.waist_cm) : null,
        muscle_mass_kg: metricForm.muscle_mass_kg ? Number(metricForm.muscle_mass_kg) : null,
        source: "manual",
        note: metricForm.note || null,
        gender: "male",
        age: 29,
      });
      setToast({ kind: "ok", text: res.message });
      setMetricForm({ weight_kg: "", body_fat_percentage: "", waist_cm: "", muscle_mass_kg: "", note: "" });
      void last;
      loadAll();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const submitLog = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await postGymData("/progress/workout-logs", {
        session_focus: logForm.session_focus,
        exercise_name: logForm.exercise_name,
        sets: Number(logForm.sets),
        reps: Number(logForm.reps),
        weight_kg: logForm.weight_kg ? Number(logForm.weight_kg) : null,
        rpe: logForm.rpe ? Number(logForm.rpe) : null,
        duration_minutes: logForm.duration_minutes ? Number(logForm.duration_minutes) : null,
        notes: logForm.notes || null,
      });
      setToast({
        kind: "ok",
        text: res.message + (res.progressive_overload_hint ? ` — ${res.progressive_overload_hint}` : ""),
      });
      setLogForm({ ...logForm, exercise_name: "", weight_kg: "", notes: "" });
      loadAll();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const submitDay = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await postGymData("/progress/checkins", {
        calories_in: dayForm.calories_in ? Number(dayForm.calories_in) : null,
        protein_g: dayForm.protein_g ? Number(dayForm.protein_g) : null,
        water_liters: dayForm.water_liters ? Number(dayForm.water_liters) : null,
        sleep_hours: dayForm.sleep_hours ? Number(dayForm.sleep_hours) : null,
        steps: dayForm.steps ? Number(dayForm.steps) : null,
        weight_kg: dayForm.weight_kg ? Number(dayForm.weight_kg) : null,
      });
      setToast({ kind: "ok", text: res.message });
      setDayForm({ calories_in: "", protein_g: "", water_liters: "", sleep_hours: "", steps: "", weight_kg: "" });
      loadAll();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  if (!loggedIn) {
    return (
      <div className="card" style={{ maxWidth: 460, margin: "3rem auto", textAlign: "center" }}>
        <h3 style={{ marginBottom: "0.6rem" }}>Vui lòng đăng nhập</h3>
        <p className="hg-muted" style={{ marginBottom: "1.2rem" }}>
          Mục Theo dõi Tiến độ yêu cầu tài khoản hội viên.
        </p>
        <a href="/login" className="hg-btn-emerald">
          Đi tới trang Đăng nhập
        </a>
      </div>
    );
  }

  const d = charts?.delta ?? {};
  const lm = summary?.latest_metric;
  const tgt = summary?.active_target;
  const last30 = summary?.last_30_days;

  const calPercent = tgt && last30 && tgt.target_daily_calories
    ? (last30.avg_calories_in / tgt.target_daily_calories) * 100
    : 0;
  const proteinPercent = tgt && last30 && tgt.protein_grams
    ? (last30.avg_protein_g / tgt.protein_grams) * 100
    : 0;
  const waterPercent = tgt && last30 && tgt.daily_water_liters
    ? (last30.avg_water_liters / tgt.daily_water_liters) * 100
    : 0;

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">DASHBOARD HỘI VIÊN</span>
          <h1 style={{ marginTop: "0.4rem" }}>Theo Dõi Tiến Độ Cơ Thể</h1>
          <p className="hg-muted">
            {charts?.total_records ?? 0} lần đo được ghi nhận
            {charts?.target ? ` · Phác đồ AI #${charts.target.plan_id} đang áp dụng` : ""}
          </p>
        </div>
        <div className="hg-flex">
          {[90, 180, 365].map((r) => (
            <button
              key={r}
              className={range === r ? "hg-btn-emerald" : "hg-btn-ghost"}
              onClick={() => setRange(r)}
            >
              {r === 365 ? "1 năm" : `${r} ngày`}
            </button>
          ))}
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      {charts?.motivation && (
        <div className="hg-verdict" style={{ marginBottom: "1.5rem" }}>
          <h3>💪 Nhận xét tiến độ</h3>
          <p>{charts.motivation}</p>
        </div>
      )}

      {/* ---------- THẺ CHỈ SỐ MỚI NHẤT ---------- */}
      {lm && (
        <div className="hg-metric-grid">
          <Metric label="Cân nặng" value={lm.weight_kg} unit="kg" note={`Đo ${lm.measured_at}`} />
          <Metric
            label="Body Fat"
            value={lm.body_fat_percentage}
            unit="%"
            note={lm.body_type}
            gold
          />
          <Metric label="Khối cơ" value={lm.muscle_mass_kg} unit="kg" note="Lean mass" />
          <Metric label="BMI" value={lm.bmi} />
          <Metric label="TDEE" value={lm.tdee_kcal} unit="kcal" gold />
        </div>
      )}

      {/* ---------- MỨC TUÂN THỦ 30 NGÀY ---------- */}
      {tgt && last30 && (
        <div className="hg-chart-card">
          <div className="hg-chart-title">Mức tuân thủ 30 ngày gần nhất</div>
          <p className="hg-chart-sub">
            So sánh thực tế với mục tiêu trong phác đồ AI · {last30.checkin_days} ngày có ghi nhật ký
          </p>
          <div className="hg-flex" style={{ gap: "2rem", justifyContent: "space-around", flexWrap: "wrap" }}>
            <div className="hg-stack" style={{ alignItems: "center" }}>
              <ProgressRing percent={calPercent} label="Calo" color="#0e6d8c" />
              <span className="hg-muted">
                {last30.avg_calories_in} / {tgt.target_daily_calories} kcal
              </span>
            </div>
            <div className="hg-stack" style={{ alignItems: "center" }}>
              <ProgressRing percent={proteinPercent} label="Đạm" color="#c9a227" />
              <span className="hg-muted">
                {last30.avg_protein_g} / {tgt.protein_grams} g
              </span>
            </div>
            <div className="hg-stack" style={{ alignItems: "center" }}>
              <ProgressRing percent={waterPercent} label="Nước" color="#1aa8cc" />
              <span className="hg-muted">
                {last30.avg_water_liters} / {tgt.daily_water_liters} lít
              </span>
            </div>
            <div className="hg-stack" style={{ alignItems: "center" }}>
              <ProgressRing
                percent={(last30.avg_sleep_hours / 8) * 100}
                label="Giấc ngủ"
                color="#0f8a6a"
              />
              <span className="hg-muted">{last30.avg_sleep_hours} / 8 giờ</span>
            </div>
            <div className="hg-stack" style={{ alignItems: "center" }}>
              <ProgressRing
                percent={(last30.avg_steps / 8000) * 100}
                label="Bước chân"
                color="#e8590c"
              />
              <span className="hg-muted">{last30.avg_steps.toLocaleString("vi-VN")} bước</span>
            </div>
          </div>
        </div>
      )}

      {/* ---------- TABS ---------- */}
      <div className="hg-tabs">
        <button className={`hg-tab ${tab === "charts" ? "active" : ""}`} onClick={() => setTab("charts")}>
          📈 Biểu đồ tiến độ
        </button>
        <button className={`hg-tab ${tab === "log" ? "active" : ""}`} onClick={() => setTab("log")}>
          📝 Nhật ký tập luyện &amp; Dinh dưỡng
        </button>
        <button className={`hg-tab ${tab === "checkin" ? "active" : ""}`} onClick={() => setTab("checkin")}>
          🎫 Check-in QR
        </button>
      </div>

      {/* ================= BIỂU ĐỒ ================= */}
      {tab === "charts" && (
        <div>
          <div className="hg-chart-card">
            <div className="hg-chart-title">
              <span>Cân nặng &amp; Tỷ lệ mỡ cơ thể</span>
              <span className="hg-flex">
                {d.weight_kg !== undefined && <Delta value={d.weight_kg} unit="kg" invert />}
                {d.body_fat_percentage !== undefined && (
                  <Delta value={d.body_fat_percentage} unit="%" invert />
                )}
              </span>
            </div>
            <p className="hg-chart-sub">Đơn vị: kg và % · thay đổi so với lần đo đầu kỳ</p>
            <LineChart
              labels={charts?.labels ?? []}
              series={[
                { name: "Cân nặng (kg)", data: charts?.series.weight_kg ?? [] },
                { name: "Body Fat (%)", data: charts?.series.body_fat_percentage ?? [] },
              ]}
              colors={["#0e6d8c", "#c9a227"]}
            />
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">
              <span>Khối lượng cơ nạc &amp; Khối mỡ</span>
              {d.muscle_mass_kg !== undefined && <Delta value={d.muscle_mass_kg} unit="kg" />}
            </div>
            <p className="hg-chart-sub">
              Mục tiêu vàng: cơ nạc tăng hoặc giữ nguyên trong khi khối mỡ giảm
            </p>
            <LineChart
              labels={charts?.labels ?? []}
              series={[
                { name: "Khối cơ (kg)", data: charts?.series.muscle_mass_kg ?? [] },
                { name: "Khối mỡ (kg)", data: charts?.series.fat_mass_kg ?? [] },
              ]}
              colors={["#0f8a6a", "#e8590c"]}
            />
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Chỉ số BMI</div>
            <p className="hg-chart-sub">Vùng bình thường theo chuẩn châu Á: 18.5 - 22.9</p>
            <BarChart
              labels={charts?.labels ?? []}
              data={charts?.series.bmi ?? []}
              color="#1391b4"
              goal={23}
            />
          </div>

          {/* Kỷ lục cá nhân */}
          {records.length > 0 && (
            <div className="hg-chart-card">
              <div className="hg-chart-title">🏆 Kỷ lục cá nhân (Personal Records)</div>
              <p className="hg-chart-sub">Mức tạ nặng nhất từng hoàn thành cho mỗi bài tập</p>
              {records.slice(0, 8).map((rec, i) => (
                <div key={i} className="hg-pr-row">
                  <div>
                    <div className="hg-exercise-name">{rec.exercise_name}</div>
                    <div className="hg-exercise-muscle">
                      {rec.target_muscle} · {rec.sets}×{rec.reps} · {rec.achieved_on}
                    </div>
                  </div>
                  <span className="hg-pr-weight">{rec.weight_kg} kg</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ================= NHẬT KÝ ================= */}
      {tab === "log" && (
        <div>
          <div className="hg-grid-2">
            {/* Ghi chỉ số cơ thể */}
            <div className="hg-chart-card">
              <div className="hg-chart-title">📊 Ghi chỉ số cơ thể mới</div>
              <p className="hg-chart-sub">
                Cân vào buổi sáng lúc bụng đói để có số liệu chính xác nhất.
              </p>
              <form onSubmit={submitMetric}>
                <input
                  className="input-box"
                  type="number"
                  step="0.1"
                  placeholder="Cân nặng (kg) *"
                  value={metricForm.weight_kg}
                  onChange={(e) => setMetricForm({ ...metricForm, weight_kg: e.target.value })}
                  required
                />
                <input
                  className="input-box"
                  type="number"
                  step="0.1"
                  placeholder="Body Fat % (bỏ trống nếu chưa đo)"
                  value={metricForm.body_fat_percentage}
                  onChange={(e) =>
                    setMetricForm({ ...metricForm, body_fat_percentage: e.target.value })
                  }
                />
                <input
                  className="input-box"
                  type="number"
                  step="0.1"
                  placeholder="Vòng eo (cm) — dùng để ước tính nếu thiếu Body Fat"
                  value={metricForm.waist_cm}
                  onChange={(e) => setMetricForm({ ...metricForm, waist_cm: e.target.value })}
                />
                <input
                  className="input-box"
                  type="number"
                  step="0.1"
                  placeholder="Khối lượng cơ (kg) — nếu có máy InBody"
                  value={metricForm.muscle_mass_kg}
                  onChange={(e) => setMetricForm({ ...metricForm, muscle_mass_kg: e.target.value })}
                />
                <input
                  className="input-box"
                  placeholder="Ghi chú (VD: Đo InBody tại Quận 1)"
                  value={metricForm.note}
                  onChange={(e) => setMetricForm({ ...metricForm, note: e.target.value })}
                />
                <button className="hg-btn-emerald" style={{ width: "100%" }} type="submit">
                  Lưu chỉ số
                </button>
              </form>
            </div>

            {/* Nhật ký tập luyện */}
            <div className="hg-chart-card">
              <div className="hg-chart-title">🏋️ Nhật ký tập luyện (Progressive Overload)</div>
              <p className="hg-chart-sub">
                Ghi lại mức tạ mỗi buổi — hệ thống sẽ so sánh và gợi ý khi nào nên tăng tải.
              </p>
              <form onSubmit={submitLog}>
                <input
                  className="input-box"
                  placeholder="Tên bài tập (VD: Incline Dumbbell Press) *"
                  value={logForm.exercise_name}
                  onChange={(e) => setLogForm({ ...logForm, exercise_name: e.target.value })}
                  required
                />
                <input
                  className="input-box"
                  placeholder="Buổi tập (VD: Upper Body A)"
                  value={logForm.session_focus}
                  onChange={(e) => setLogForm({ ...logForm, session_focus: e.target.value })}
                />
                <div className="hg-flex" style={{ gap: "0.5rem" }}>
                  <input
                    className="input-box"
                    type="number"
                    placeholder="Sets"
                    value={logForm.sets}
                    onChange={(e) => setLogForm({ ...logForm, sets: e.target.value })}
                  />
                  <input
                    className="input-box"
                    type="number"
                    placeholder="Reps"
                    value={logForm.reps}
                    onChange={(e) => setLogForm({ ...logForm, reps: e.target.value })}
                  />
                  <input
                    className="input-box"
                    type="number"
                    step="0.5"
                    placeholder="Tạ (kg)"
                    value={logForm.weight_kg}
                    onChange={(e) => setLogForm({ ...logForm, weight_kg: e.target.value })}
                  />
                </div>
                <div className="hg-flex" style={{ gap: "0.5rem" }}>
                  <input
                    className="input-box"
                    type="number"
                    step="0.5"
                    placeholder="RPE (1-10)"
                    value={logForm.rpe}
                    onChange={(e) => setLogForm({ ...logForm, rpe: e.target.value })}
                  />
                  <input
                    className="input-box"
                    type="number"
                    placeholder="Thời lượng (phút)"
                    value={logForm.duration_minutes}
                    onChange={(e) => setLogForm({ ...logForm, duration_minutes: e.target.value })}
                  />
                </div>
                <input
                  className="input-box"
                  placeholder="Ghi chú kỹ thuật"
                  value={logForm.notes}
                  onChange={(e) => setLogForm({ ...logForm, notes: e.target.value })}
                />
                <button className="hg-btn-gold" style={{ width: "100%" }} type="submit">
                  Ghi nhật ký tập
                </button>
              </form>
            </div>
          </div>

          {/* Nhật ký dinh dưỡng */}
          <div className="hg-chart-card">
            <div className="hg-chart-title">🥗 Nhật ký dinh dưỡng &amp; Phục hồi hôm nay</div>
            <p className="hg-chart-sub">
              Hệ thống sẽ đối chiếu với mục tiêu calo/đạm/nước trong phác đồ AI của bạn.
            </p>
            <form onSubmit={submitDay}>
              <div className="hg-flex" style={{ gap: "0.6rem", alignItems: "flex-start" }}>
                <input
                  className="input-box"
                  type="number"
                  placeholder="Calo nạp (kcal)"
                  value={dayForm.calories_in}
                  onChange={(e) => setDayForm({ ...dayForm, calories_in: e.target.value })}
                />
                <input
                  className="input-box"
                  type="number"
                  placeholder="Đạm (g)"
                  value={dayForm.protein_g}
                  onChange={(e) => setDayForm({ ...dayForm, protein_g: e.target.value })}
                />
                <input
                  className="input-box"
                  type="number"
                  step="0.1"
                  placeholder="Nước (lít)"
                  value={dayForm.water_liters}
                  onChange={(e) => setDayForm({ ...dayForm, water_liters: e.target.value })}
                />
                <input
                  className="input-box"
                  type="number"
                  step="0.5"
                  placeholder="Ngủ (giờ)"
                  value={dayForm.sleep_hours}
                  onChange={(e) => setDayForm({ ...dayForm, sleep_hours: e.target.value })}
                />
                <input
                  className="input-box"
                  type="number"
                  placeholder="Bước chân"
                  value={dayForm.steps}
                  onChange={(e) => setDayForm({ ...dayForm, steps: e.target.value })}
                />
              </div>
              <button className="hg-btn-emerald" type="submit">
                Lưu nhật ký hôm nay
              </button>
            </form>
          </div>

          {/* Bảng nhật ký tập luyện */}
          <SectionTitle>Lịch sử tập luyện ({logs.length})</SectionTitle>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ngày</th>
                  <th>Bài tập</th>
                  <th>Sets × Reps</th>
                  <th>Tạ</th>
                  <th>Volume</th>
                  <th>RPE</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", color: "#6b8598" }}>
                      Chưa có nhật ký tập luyện nào.
                    </td>
                  </tr>
                ) : (
                  logs.map((l) => (
                    <tr key={l.id}>
                      <td style={{ whiteSpace: "nowrap" }}>{l.log_date}</td>
                      <td>
                        <div className="hg-exercise-name">{l.exercise_name}</div>
                        <div className="hg-exercise-muscle">{l.session_focus}</div>
                      </td>
                      <td>
                        <span className="hg-sets-badge">
                          {l.sets} × {l.reps}
                        </span>
                      </td>
                      <td>
                        <strong>{l.weight_kg ?? "—"}</strong> kg
                      </td>
                      <td>{l.volume_kg.toLocaleString("vi-VN")} kg</td>
                      <td>{l.rpe ?? "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================= CHECK-IN QR ================= */}
      {tab === "checkin" && (
        <div className="hg-grid-2">
          <div className="hg-qr-box">
            <span className="chip">MÃ QR CHECK-IN ĐIỆN TỬ</span>
            <h3 style={{ marginTop: "0.8rem" }}>{qr?.member_name ?? "—"}</h3>
            <p className="hg-muted">
              {qr?.plan_name} · Trạng thái: <strong>{qr?.status?.toUpperCase()}</strong>
              {qr?.expire_date ? ` · Hạn thẻ: ${qr.expire_date}` : ""}
            </p>
            <div className="hg-qr-code">{qr?.qr_code ?? "—"}</div>
            <div className={qr?.can_checkin ? "hg-note ok" : "hg-note danger"}>
              {qr?.can_checkin
                ? "✓ Thẻ hợp lệ — đưa mã này cho lễ tân hoặc quét tại cổng vào."
                : `✕ ${qr?.reason ?? "Thẻ không hợp lệ"}`}
            </div>
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Lịch sử check-in gần đây</div>
            <p className="hg-chart-sub">10 lượt check-in mới nhất tại phòng tập</p>
            {(qr?.recent_checkins ?? []).length === 0 ? (
              <div className="hg-empty">Chưa có lượt check-in nào.</div>
            ) : (
              qr.recent_checkins.map((c: any, i: number) => (
                <div key={i} className="hg-kv">
                  <span>{new Date(c.checkin_time).toLocaleString("vi-VN")}</span>
                  <span>{c.checked_by}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}