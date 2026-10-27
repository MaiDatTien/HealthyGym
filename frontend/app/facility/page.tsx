"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData, putGymData } from "@/lib/api";
import { Chip, KV, Note, SectionTitle, Stat, Toast } from "@/components/ui";
import type { EquipmentItem } from "@/lib/erp-types";
import { LIFECYCLE_LABELS } from "@/lib/erp-types";

/* ==========================================================================
   QUẢN LÝ CƠ SỞ VẬT CHẤT — Vòng đời thiết bị, phiếu bảo trì, lịch bảo trì
   định kỳ, và đồng bộ với AI Coach (bài tập bị chặn khi máy hỏng).
   ========================================================================== */

export default function FacilityPage() {
  const [equipment, setEquipment] = useState<EquipmentItem[]>([]);
  const [tickets, setTickets] = useState<any>(null);
  const [upcoming, setUpcoming] = useState<any>(null);
  const [unavailable, setUnavailable] = useState<any>(null);
  const [tab, setTab] = useState<"equipment" | "tickets" | "schedule" | "ai-sync">("equipment");
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const [reportForm, setReportForm] = useState({
    facility_id: "",
    issue: "",
    severity: "medium",
    technician: "",
    cost: "0",
  });
  const [scheduleForm, setScheduleForm] = useState({
    facility_id: "",
    cycle_days: "90",
  });
  const [qrForm, setQrForm] = useState({
    facility_id: "",
    machine_code: "",
    display_name: "",
    target_muscles: "",
    exercise_name: "",
  });

  const load = () => {
    fetchGymData("/equipment/list").then(setEquipment).catch(() => {});
    fetchGymData("/equipment/maintenance/tickets").then(setTickets).catch(() => {});
    fetchGymData("/equipment/maintenance/upcoming?days_ahead=60").then(setUpcoming).catch(() => {});
    fetchGymData("/equipment/ai-coach/unavailable").then(setUnavailable).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  const createTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await postGymData("/equipment/maintenance", {
        facility_id: Number(reportForm.facility_id),
        issue: reportForm.issue,
        severity: reportForm.severity,
        technician: reportForm.technician || null,
        cost: Number(reportForm.cost || 0),
      });
      setToast({ kind: "ok", text: res.message });
      setReportForm({ facility_id: "", issue: "", severity: "medium", technician: "", cost: "0" });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const updateTicket = async (id: number, status: string, technician?: string) => {
    try {
      const params = new URLSearchParams({ status });
      if (technician) params.set("technician", technician);
      const res = await putGymData(`/equipment/maintenance/${id}?${params.toString()}`, {});
      setToast({ kind: "ok", text: res.message });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const setSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await postGymData("/equipment/maintenance/schedule", {
        facility_id: Number(scheduleForm.facility_id),
        maintenance_cycle_days: Number(scheduleForm.cycle_days),
      });
      setToast({ kind: "ok", text: res.message });
      setScheduleForm({ facility_id: "", cycle_days: "90" });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const createQR = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await postGymData("/equipment/machine-qr", {
        facility_id: Number(qrForm.facility_id),
        machine_code: qrForm.machine_code,
        display_name: qrForm.display_name,
        target_muscles: qrForm.target_muscles || null,
        exercise_name: qrForm.exercise_name || null,
      });
      setToast({ kind: "ok", text: `${res.message} — ${res.print_note}` });
      setQrForm({ facility_id: "", machine_code: "", display_name: "", target_muscles: "", exercise_name: "" });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const broken = equipment.filter((e) => !e.is_usable);
  const dueMaintenance = equipment.filter((e) => e.maintenance_due);

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <Chip>QUẢN LÝ CSVC</Chip>
          <h1>Cơ Sở Vật Chất &amp; Thiết Bị</h1>
          <p>
            Theo dõi vòng đời thiết bị, xử lý phiếu bảo trì và đồng bộ trạng thái máy với
            AI Coach của hội viên.
          </p>
        </div>
        <div className="hg-flex">
          {broken.length > 0 && <Chip tone="danger">{broken.length} thiết bị không dùng được</Chip>}
          {dueMaintenance.length > 0 && (
            <Chip tone="warn">{dueMaintenance.length} đến hạn bảo trì</Chip>
          )}
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      <div className="stats-bar">
        <Stat label="Tổng thiết bị" value={equipment.length} />
        <Stat
          label="Hoạt động tốt"
          value={equipment.filter((e) => e.lifecycle_status === "active").length}
          gold
        />
        <Stat label="Đang bảo trì" value={equipment.filter((e) => e.lifecycle_status === "maintenance").length} />
        <Stat
          label="Ngưng sử dụng"
          value={equipment.filter((e) => e.lifecycle_status === "out_of_order").length}
        />
        {tickets && <Stat label="Phiếu chờ xử lý" value={tickets.pending} />}
      </div>

      <div className="hg-tabs">
        <button className={`hg-tab ${tab === "equipment" ? "active" : ""}`} onClick={() => setTab("equipment")}>
          Danh mục thiết bị
        </button>
        <button className={`hg-tab ${tab === "tickets" ? "active" : ""}`} onClick={() => setTab("tickets")}>
          Phiếu bảo trì
        </button>
        <button className={`hg-tab ${tab === "schedule" ? "active" : ""}`} onClick={() => setTab("schedule")}>
          Bảo trì định kỳ
        </button>
        <button className={`hg-tab ${tab === "ai-sync" ? "active" : ""}`} onClick={() => setTab("ai-sync")}>
          Đồng bộ AI Coach
        </button>
      </div>

      {/* ================= DANH MỤC THIẾT BỊ ================= */}
      {tab === "equipment" && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Thiết bị</th>
                <th>Loại</th>
                <th>SL</th>
                <th>Trạng thái</th>
                <th>Bảo trì tới</th>
                <th>Phiếu mở</th>
              </tr>
            </thead>
            <tbody>
              {equipment.map((e) => (
                <tr key={e.id}>
                  <td>
                    <strong>{e.name}</strong>
                    {(e.brand || e.model) && (
                      <div className="hg-exercise-muscle">
                        {[e.brand, e.model].filter(Boolean).join(" ")}
                      </div>
                    )}
                  </td>
                  <td>
                    <Chip>{e.category}</Chip>
                  </td>
                  <td className="hg-num">{e.quantity}</td>
                  <td>
                    <Chip
                      tone={
                        e.lifecycle_status === "active"
                          ? "ok"
                          : e.lifecycle_status === "maintenance"
                          ? "warn"
                          : "danger"
                      }
                    >
                      {e.lifecycle_label}
                    </Chip>
                  </td>
                  <td className="hg-num-mono">
                    {e.next_maintenance_date ?? "—"}
                    {e.maintenance_warning && (
                      <div style={{ fontSize: "11px", color: "#b45309" }}>
                        {e.maintenance_warning}
                      </div>
                    )}
                  </td>
                  <td>
                    {e.open_maintenance_tickets > 0 ? (
                      <Chip tone="danger">{e.open_maintenance_tickets}</Chip>
                    ) : (
                      <span className="hg-muted">0</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ================= PHIẾU BẢO TRÌ ================= */}
      {tab === "tickets" && (
        <div className="hg-grid-2">
          <div className="hg-chart-card">
            <div className="hg-chart-title">Tạo phiếu bảo trì</div>
            <form onSubmit={createTicket}>
              <label>Thiết bị</label>
              <select
                className="input-box"
                value={reportForm.facility_id}
                onChange={(e) => setReportForm({ ...reportForm, facility_id: e.target.value })}
                required
              >
                <option value="">— Chọn thiết bị —</option>
                {equipment.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name}
                  </option>
                ))}
              </select>

              <label>Mô tả sự cố</label>
              <textarea
                className="input-box"
                rows={3}
                placeholder="VD: Đứt cáp máy kéo, rách đệm ghế, kẹt tạ..."
                value={reportForm.issue}
                onChange={(e) => setReportForm({ ...reportForm, issue: e.target.value })}
                required
              />

              <label>Mức độ nghiêm trọng</label>
              <select
                className="input-box"
                value={reportForm.severity}
                onChange={(e) => setReportForm({ ...reportForm, severity: e.target.value })}
              >
                <option value="low">Thấp — ghi nhận cho lần bảo trì tới</option>
                <option value="medium">Trung bình — chuyển sang đang bảo trì</option>
                <option value="high">Nghiêm trọng — ngưng sử dụng ngay</option>
              </select>

              <label>Kỹ thuật viên</label>
              <input
                className="input-box"
                placeholder="VD: KTV Trung"
                value={reportForm.technician}
                onChange={(e) => setReportForm({ ...reportForm, technician: e.target.value })}
              />

              <label>Chi phí dự kiến (đ)</label>
              <input
                className="input-box"
                type="number"
                value={reportForm.cost}
                onChange={(e) => setReportForm({ ...reportForm, cost: e.target.value })}
              />

              <Note>
                Mức độ <strong>trung bình</strong> hoặc <strong>nghiêm trọng</strong> sẽ tự động
                chuyển thiết bị sang trạng thái bảo trì và AI Coach sẽ loại bài tập tương ứng.
              </Note>

              <button className="hg-btn-primary" style={{ width: "100%" }}>
                Tạo phiếu bảo trì
              </button>
            </form>

            <SectionTitle>Tạo mã QR cho máy tập</SectionTitle>
            <form onSubmit={createQR}>
              <label>Thiết bị</label>
              <select
                className="input-box"
                value={qrForm.facility_id}
                onChange={(e) => setQrForm({ ...qrForm, facility_id: e.target.value })}
                required
              >
                <option value="">— Chọn thiết bị —</option>
                {equipment.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name}
                  </option>
                ))}
              </select>
              <label>Mã máy (in trên tem)</label>
              <input
                className="input-box"
                placeholder="VD: TREADMILL-08"
                value={qrForm.machine_code}
                onChange={(e) => setQrForm({ ...qrForm, machine_code: e.target.value })}
                required
              />
              <label>Tên hiển thị</label>
              <input
                className="input-box"
                placeholder="VD: Máy chạy bộ số 08"
                value={qrForm.display_name}
                onChange={(e) => setQrForm({ ...qrForm, display_name: e.target.value })}
                required
              />
              <label>Nhóm cơ tác động</label>
              <input
                className="input-box"
                placeholder="VD: Chân, Mông, Tim mạch"
                value={qrForm.target_muscles}
                onChange={(e) => setQrForm({ ...qrForm, target_muscles: e.target.value })}
              />
              <label>Bài tập liên kết (để đồng bộ AI)</label>
              <input
                className="input-box"
                placeholder="VD: Leg Press (Đạp đùi máy)"
                value={qrForm.exercise_name}
                onChange={(e) => setQrForm({ ...qrForm, exercise_name: e.target.value })}
              />
              <button className="hg-btn-primary" style={{ width: "100%" }}>
                Tạo mã QR
              </button>
            </form>
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Danh sách phiếu bảo trì</div>
            {tickets && (
              <div className="hg-flex" style={{ marginBottom: "12px" }}>
                <Chip tone="warn">{tickets.pending} chờ xử lý</Chip>
                <Chip>{tickets.in_progress} đang xử lý</Chip>
              </div>
            )}
            <div style={{ maxHeight: "680px", overflowY: "auto" }}>
              {(tickets?.tickets ?? []).length === 0 ? (
                <div className="hg-empty">Chưa có phiếu bảo trì nào.</div>
              ) : (
                tickets.tickets.map((t: any) => (
                  <div
                    key={t.id}
                    style={{
                      padding: "12px 0",
                      borderBottom: "1px solid #d4e0e5",
                    }}
                  >
                    <div className="hg-flex" style={{ justifyContent: "space-between" }}>
                      <strong style={{ fontSize: "13px" }}>{t.facility_name}</strong>
                      <div className="hg-flex" style={{ gap: "4px" }}>
                        <Chip
                          tone={
                            t.severity === "high"
                              ? "danger"
                              : t.severity === "medium"
                              ? "warn"
                              : "default"
                          }
                        >
                          {t.severity}
                        </Chip>
                        <Chip
                          tone={
                            t.status === "resolved"
                              ? "ok"
                              : t.status === "in_progress"
                              ? "warn"
                              : "danger"
                          }
                        >
                          {t.status === "resolved"
                            ? "ĐÃ XỬ LÝ"
                            : t.status === "in_progress"
                            ? "ĐANG XỬ LÝ"
                            : "CHỜ XỬ LÝ"}
                        </Chip>
                      </div>
                    </div>

                    <p style={{ fontSize: "12.5px", color: "#35505c", marginTop: "6px" }}>
                      {t.issue}
                    </p>

                    <div className="hg-flex" style={{ marginTop: "8px", gap: "10px" }}>
                      <span className="hg-muted">Báo bởi: {t.reported_by}</span>
                      {t.technician && <span className="hg-muted">KTV: {t.technician}</span>}
                      <span className="hg-muted">{t.days_open} ngày</span>
                      {t.cost > 0 && (
                        <span className="hg-num-mono" style={{ fontSize: "12px" }}>
                          {Number(t.cost).toLocaleString("vi-VN")}đ
                        </span>
                      )}
                    </div>

                    {t.status !== "resolved" && (
                      <div className="hg-flex" style={{ marginTop: "8px" }}>
                        {t.status === "pending" && (
                          <button
                            className="hg-btn-ghost hg-btn-sm"
                            onClick={() => updateTicket(t.id, "in_progress")}
                          >
                            Nhận xử lý
                          </button>
                        )}
                        <button
                          className="hg-btn-primary hg-btn-sm"
                          onClick={() => updateTicket(t.id, "resolved")}
                        >
                          Hoàn tất
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ================= BẢO TRÌ ĐỊNH KỲ ================= */}
      {tab === "schedule" && (
        <div className="hg-grid-2">
          <div className="hg-chart-card">
            <div className="hg-chart-title">Đặt lịch bảo trì định kỳ</div>
            <form onSubmit={setSchedule}>
              <label>Thiết bị</label>
              <select
                className="input-box"
                value={scheduleForm.facility_id}
                onChange={(e) => setScheduleForm({ ...scheduleForm, facility_id: e.target.value })}
                required
              >
                <option value="">— Chọn thiết bị —</option>
                {equipment.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name} (chu kỳ hiện tại: {e.maintenance_cycle_days} ngày)
                  </option>
                ))}
              </select>

              <label>Chu kỳ bảo trì (ngày)</label>
              <input
                className="input-box"
                type="number"
                min={7}
                max={730}
                value={scheduleForm.cycle_days}
                onChange={(e) => setScheduleForm({ ...scheduleForm, cycle_days: e.target.value })}
              />

              <div className="hg-flex" style={{ marginBottom: "10px" }}>
                {["30", "60", "90", "180"].map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={
                      scheduleForm.cycle_days === d ? "hg-btn-primary hg-btn-sm" : "hg-btn-ghost hg-btn-sm"
                    }
                    onClick={() => setScheduleForm({ ...scheduleForm, cycle_days: d })}
                  >
                    {d} ngày
                  </button>
                ))}
              </div>

              <button className="hg-btn-primary" style={{ width: "100%" }}>
                Đặt lịch bảo trì
              </button>
            </form>
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Thiết bị đến hạn bảo trì</div>
            {upcoming && (
              <>
                {upcoming.overdue_count > 0 && (
                  <Note tone="danger">
                    <strong>{upcoming.overdue_count} thiết bị QUÁ HẠN bảo trì.</strong> Nên xử lý
                    ngay để tránh hỏng nặng và gián đoạn dịch vụ.
                  </Note>
                )}

                <SectionTitle>Quá hạn ({upcoming.overdue_count})</SectionTitle>
                {upcoming.overdue.length === 0 ? (
                  <div className="hg-muted">Không có thiết bị nào quá hạn.</div>
                ) : (
                  upcoming.overdue.map((f: any) => (
                    <div key={f.facility_id} className="hg-kv">
                      <span>
                        <strong>{f.name}</strong>
                        <div className="hg-exercise-muscle">{f.category}</div>
                      </span>
                      <span>
                        <Chip tone="danger">QUÁ {f.days_overdue} NGÀY</Chip>
                      </span>
                    </div>
                  ))
                )}

                <SectionTitle>Sắp đến hạn ({upcoming.upcoming_count})</SectionTitle>
                {upcoming.upcoming.length === 0 ? (
                  <div className="hg-muted">Không có thiết bị nào sắp đến hạn.</div>
                ) : (
                  upcoming.upcoming.map((f: any) => (
                    <div key={f.facility_id} className="hg-kv">
                      <span>
                        <strong>{f.name}</strong>
                        <div className="hg-exercise-muscle">{f.next_maintenance_date}</div>
                      </span>
                      <span>
                        <Chip tone={f.days_until <= 7 ? "warn" : "default"}>
                          CÒN {f.days_until} NGÀY
                        </Chip>
                      </span>
                    </div>
                  ))
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* ================= ĐỒNG BỘ AI COACH ================= */}
      {tab === "ai-sync" && (
        <div>
          <Note tone="gold">
            <strong>Cơ chế liên kết thông minh:</strong> khi thiết bị chuyển sang trạng thái
            &quot;Đang bảo trì&quot; hoặc &quot;Ngưng sử dụng&quot;, AI Coach tự động biết và tạm
            thời không xếp bài tập dùng thiết bị đó vào lịch của hội viên — đồng thời gợi ý bài
            thay thế cùng nhóm cơ tác động.
          </Note>

          {unavailable && (
            <>
              <div className="stats-bar">
                <Stat label="Thiết bị không khả dụng" value={unavailable.unavailable_count} />
                <Stat label="Bài tập bị chặn" value={unavailable.blocked_exercise_names.length} gold />
              </div>

              {unavailable.unavailable_count === 0 ? (
                <div className="hg-empty">
                  <h3>Tất cả thiết bị đang hoạt động tốt</h3>
                  <p>Không có bài tập nào bị chặn khỏi lịch tập của hội viên.</p>
                </div>
              ) : (
                <>
                  <SectionTitle>Bài tập đang bị chặn</SectionTitle>
                  <div className="hg-flex" style={{ marginBottom: "16px" }}>
                    {unavailable.blocked_exercise_names.map((n: string) => (
                      <Chip key={n} tone="danger">
                        {n}
                      </Chip>
                    ))}
                  </div>

                  <SectionTitle>Chi tiết theo thiết bị</SectionTitle>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Thiết bị</th>
                          <th>Loại</th>
                          <th>Trạng thái</th>
                          <th>Số lượng ảnh hưởng</th>
                          <th>Bài tập bị ảnh hưởng</th>
                        </tr>
                      </thead>
                      <tbody>
                        {unavailable.details.map((d: any) => (
                          <tr key={d.facility_id}>
                            <td>
                              <strong>{d.name}</strong>
                            </td>
                            <td>
                              <Chip>{d.category}</Chip>
                            </td>
                            <td>
                              <Chip tone={d.lifecycle_status === "maintenance" ? "warn" : "danger"}>
                                {d.lifecycle_label}
                              </Chip>
                            </td>
                            <td className="hg-num">{d.quantity_affected}</td>
                            <td style={{ fontSize: "12.5px" }}>
                              {d.affected_exercises.length > 0
                                ? d.affected_exercises.join(", ")
                                : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <Note>{unavailable.ai_coach_behavior}</Note>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}