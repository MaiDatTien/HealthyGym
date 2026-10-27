"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { Chip, Note, SectionTitle, Stat, Toast } from "@/components/ui";
import type { EquipmentItem, MachineQRInfo } from "@/lib/erp-types";

/* ==========================================================================
   QUÉT MÃ QR THIẾT BỊ — Hướng dẫn sử dụng & báo hỏng
     Hội viên quét mã dán trên máy để xem hướng dẫn setup, tư thế đúng,
     lỗi thường gặp và báo hỏng ngay cho kỹ thuật viên.
   ========================================================================== */

const DEMO_CODES = ["MQ-TREADMILL-07", "MQ-SQUAT-RACK-01"];

export default function EquipmentScanPage() {
  const [code, setCode] = useState("");
  const [machine, setMachine] = useState<MachineQRInfo | null>(null);
  const [equipment, setEquipment] = useState<EquipmentItem[]>([]);
  const [upcoming, setUpcoming] = useState<any>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const [report, setReport] = useState({ issue: "", severity: "medium" });

  const load = () => {
    fetchGymData("/equipment/list").then(setEquipment).catch(() => {});
    fetchGymData("/equipment/maintenance/upcoming?days_ahead=60").then(setUpcoming).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  const scan = async (qrCode?: string) => {
    const target = (qrCode ?? code).trim();
    if (!target) return;
    setBusy(true);
    try {
      const res = await fetchGymData(`/equipment/scan/${encodeURIComponent(target)}`);
      setMachine(res);
      setToast(null);
      setCode(target);
    } catch (err: any) {
      setMachine(null);
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const submitReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!machine) return;
    setBusy(true);
    try {
      const facilityId = equipment.find((x) => x.name === machine.facility_name)?.id;
      const res = await postGymData("/equipment/report-issue", {
        facility_id: facilityId ?? 1,
        issue: report.issue,
        severity: report.severity,
        // Backend tra cứu theo qr_code, không phải machine_code
        machine_qr_code: code,
      });
      setToast({
        kind: "ok",
        text: `${res.message} ${res.severity_note ?? ""} ${res.ai_coach_sync ?? ""}`.trim(),
      });
      setReport({ issue: "", severity: "medium" });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const broken = equipment.filter((e) => !e.is_usable);
  const dueSoon = equipment.filter((e) => e.maintenance_due);

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <Chip>THIẾT BỊ &amp; HƯỚNG DẪN SỬ DỤNG</Chip>
          <h1>Quét Mã QR Trên Máy Tập</h1>
          <p>
            Mỗi máy tập có một mã QR riêng. Quét mã để xem hướng dẫn setup, tư thế đúng, lỗi thường
            gặp và báo hỏng ngay cho kỹ thuật viên.
          </p>
        </div>
        <div className="hg-flex">
          {broken.length > 0 && <Chip tone="danger">{broken.length} máy ngưng sử dụng</Chip>}
          {dueSoon.length > 0 && <Chip tone="warn">{dueSoon.length} máy đến hạn bảo trì</Chip>}
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      <div className="hg-grid-2">
        <div className="hg-chart-card">
          <div className="hg-chart-title">Nhập mã máy</div>
          <p className="hg-chart-sub">
            Dán mã QR hoặc nhập mã máy in trên thân thiết bị (VD: MQ-TREADMILL-07).
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              scan();
            }}
          >
            <input
              className="input-box"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="MQ-..."
              autoFocus
            />
            <button className="hg-btn-primary" style={{ width: "100%" }} disabled={busy}>
              {busy && <span className="hg-spinner" />}
              Xem hướng dẫn sử dụng
            </button>
          </form>

          <div className="hg-metric-label" style={{ marginTop: "14px", marginBottom: "6px" }}>
            Mã máy có sẵn để thử
          </div>
          <div className="hg-flex" style={{ gap: "6px", flexWrap: "wrap" }}>
            {DEMO_CODES.map((d) => (
              <button key={d} className="hg-btn-ghost hg-btn-sm" onClick={() => scan(d)}>
                {d}
              </button>
            ))}
          </div>

          {machine && machine.status_warning && (
            <Note tone="danger">{machine.status_warning}</Note>
          )}
        </div>

        <div className="hg-chart-card">
          <div className="hg-chart-title">
            {machine ? machine.display_name : "Chưa chọn máy"}
          </div>
          {!machine ? (
            <div className="hg-empty">
              Quét một mã máy để xem hướng dẫn sử dụng chi tiết và tình trạng thiết bị.
            </div>
          ) : (
            <>
              <div className="hg-kv">
                <span>Mã máy</span>
                <span className="hg-num-mono" style={{ fontWeight: 600 }}>
                  {machine.machine_code}
                </span>
              </div>
              <div className="hg-kv">
                <span>Thiết bị</span>
                <span>{machine.facility_name ?? "—"}</span>
              </div>
              <div className="hg-kv">
                <span>Nhóm cơ tác động</span>
                <span>{machine.target_muscles ?? "—"}</span>
              </div>
              <div className="hg-kv">
                <span>Độ khó</span>
                <span>
                  <Chip>{machine.difficulty}</Chip>
                </span>
              </div>
              <div className="hg-kv">
                <span>Tình trạng</span>
                <span>
                  <Chip tone={machine.is_usable ? "ok" : "danger"}>
                    {machine.is_usable ? "SẴN SÀNG SỬ DỤNG" : "TẠM NGƯNG"}
                  </Chip>
                </span>
              </div>
              <div className="hg-kv">
                <span>Phiếu bảo trì đang mở</span>
                <span className="hg-num">{machine.open_tickets}</span>
              </div>
              {machine.linked_exercise && (
                <div className="hg-kv">
                  <span>Bài tập tương ứng</span>
                  <span>{machine.linked_exercise}</span>
                </div>
              )}
              {machine.video_url && (
                <Note>
                  Video hướng dẫn:{" "}
                  <a href={machine.video_url} target="_blank" rel="noreferrer">
                    {machine.video_url}
                  </a>
                </Note>
              )}
              <Note tone="gold">{machine.ai_tip}</Note>
            </>
          )}
        </div>
      </div>

      {machine && (
        <>
          <SectionTitle>Hướng dẫn sử dụng</SectionTitle>
          <div className="hg-grid-2">
            <div className="hg-chart-card">
              <div className="hg-chart-title">Các bước thiết lập máy</div>
              <ul className="benefit-list">
                {String(machine.setup_guide ?? "")
                  .split("\n")
                  .filter(Boolean)
                  .map((s, i) => (
                    <li key={i}>
                      <span style={{ color: "#0b6e8f", marginRight: 6, fontWeight: 800 }}>▸</span>
                      {s}
                    </li>
                  ))}
              </ul>
            </div>
            <div className="hg-chart-card">
              <div className="hg-chart-title">Tư thế đúng</div>
              <ul className="benefit-list">
                {String(machine.posture_guide ?? "")
                  .split("\n")
                  .filter(Boolean)
                  .map((s, i) => (
                    <li key={i}>
                      <span style={{ color: "#0f7a52", marginRight: 6, fontWeight: 800 }}>✓</span>
                      {s}
                    </li>
                  ))}
              </ul>
            </div>
          </div>

          <div className="hg-warning-box">
            <h4>Lỗi thường gặp — tránh để phòng chấn thương</h4>
            <ul>
              {String(machine.common_mistakes ?? "")
                .split("\n")
                .filter(Boolean)
                .map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
            </ul>
          </div>

          <SectionTitle>Báo hỏng thiết bị</SectionTitle>
          <div className="hg-chart-card">
            <p className="hg-chart-sub">{machine.report_hint}</p>
            <form onSubmit={submitReport}>
              <label>Mô tả tình trạng hỏng (tối thiểu 5 ký tự)</label>
              <input
                className="input-box"
                value={report.issue}
                onChange={(e) => setReport({ ...report, issue: e.target.value })}
                placeholder="VD: Đứt cáp kéo, đệm ngồi rách, kẹt tạ ở tầng 3"
                required
              />
              <label>Mức độ nghiêm trọng</label>
              <select
                className="input-box"
                value={report.severity}
                onChange={(e) => setReport({ ...report, severity: e.target.value })}
              >
                <option value="low">Nhẹ — vẫn dùng tạm được</option>
                <option value="medium">Trung bình — cần sửa sớm</option>
                <option value="high">Nặng — nguy hiểm, ngưng sử dụng ngay</option>
              </select>
              <button className="hg-btn-gold" style={{ width: "100%" }} disabled={busy}>
                {busy && <span className="hg-spinner" />}
                Gửi báo hỏng cho kỹ thuật viên
              </button>
            </form>
            <Note tone="danger">
              Chọn mức độ &quot;Nặng&quot; sẽ tự động chuyển máy sang trạng thái NGƯNG SỬ DỤNG và
              loại bài tập này khỏi phác đồ AI Coach của hội viên.
            </Note>
          </div>
        </>
      )}

      <SectionTitle>Danh mục thiết bị phòng tập</SectionTitle>
      {upcoming && (
        <div className="stats-bar">
          <Stat label="Tổng thiết bị" value={equipment.length} />
          <Stat label="Đang hoạt động" value={equipment.length - broken.length} gold />
          <Stat label="Ngưng sử dụng" value={broken.length} />
          <Stat
            label="Đến hạn bảo trì"
            value={(upcoming.overdue_count ?? 0) + (upcoming.upcoming_count ?? 0)}
          />
        </div>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Thiết bị</th>
              <th>Danh mục</th>
              <th>Số lượng</th>
              <th>Trạng thái</th>
              <th>Bảo trì gần nhất</th>
              <th>Bảo trì kế tiếp</th>
              <th>Cảnh báo</th>
            </tr>
          </thead>
          <tbody>
            {equipment.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center" }}>
                  Chưa có thiết bị nào trong hệ thống.
                </td>
              </tr>
            ) : (
              equipment.map((e) => (
                <tr key={e.id}>
                  <td>
                    <strong>{e.name}</strong>
                    <div className="hg-exercise-muscle">
                      {e.brand ?? "—"} {e.model ?? ""}
                    </div>
                  </td>
                  <td>{e.category}</td>
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
                  <td className="hg-num-mono" style={{ fontSize: "12.5px" }}>
                    {e.last_maintenance_date ?? "—"}
                  </td>
                  <td className="hg-num-mono" style={{ fontSize: "12.5px" }}>
                    {e.next_maintenance_date ?? "—"}
                  </td>
                  <td style={{ fontSize: "12.5px" }}>
                    {e.maintenance_warning ? (
                      <span style={{ color: "#b45309" }}>{e.maintenance_warning}</span>
                    ) : e.open_maintenance_tickets > 0 ? (
                      <Chip tone="warn">{e.open_maintenance_tickets} phiếu mở</Chip>
                    ) : (
                      <Chip tone="ok">BÌNH THƯỜNG</Chip>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}