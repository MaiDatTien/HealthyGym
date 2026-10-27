"use client";
import React, { useEffect, useMemo, useState } from "react";
import { fetchGymData, postGymData, putGymData } from "@/lib/api";
import { Chip, Note, SectionTitle, Stat, Toast } from "@/components/ui";
import type { LeadItem } from "@/lib/erp-types";
import { LEAD_STAGE_LABELS } from "@/lib/erp-types";

/* ==========================================================================
   CRM KHÁCH TẬP THỬ — Phễu chuyển đổi (Lead Pipeline)
     Bước 1: Khách đăng ký tập thử miễn phí -> sinh QR + OTP chống lạm dụng
     Bước 2: Xác thực OTP -> kích hoạt vé tập thử
     Bước 3: Lễ tân chăm sóc theo 6 trạng thái phễu
     Bước 4: Chốt gói -> tự động tạo hội viên + hợp đồng
   ========================================================================== */

const STAGE_ORDER = [
  "new",
  "scheduled",
  "first_visit",
  "inbody_consulted",
  "won",
  "lost",
];

export default function LeadsPage() {
  const [leads, setLeads] = useState<any>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [stageFilter, setStageFilter] = useState("");
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<"pipeline" | "trial">("pipeline");

  // --- Form cấp vé tập thử ---
  const [trialForm, setTrialForm] = useState({ full_name: "", phone: "", days: "7" });
  const [trial, setTrial] = useState<any>(null);
  const [otpCode, setOtpCode] = useState("");
  const [activated, setActivated] = useState<any>(null);

  // --- Chốt gói ---
  const [convertId, setConvertId] = useState<number | null>(null);
  const [convertPlan, setConvertPlan] = useState("");

  const load = (stage = stageFilter) => {
    const qs = stage ? `?stage=${stage}` : "";
    fetchGymData(`/memberships/leads${qs}`).then(setLeads).catch(() => {});
  };

  useEffect(() => {
    load("");
    fetchGymData("/listings/plans").then(setPlans).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const registerTrial = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await postGymData("/memberships/trial/register", {
        full_name: trialForm.full_name,
        phone: trialForm.phone,
        days: Number(trialForm.days),
        branch_id: 1,
      });
      setTrial(res);
      setActivated(null);
      setToast({ kind: "ok", text: res.message });
      load();
    } catch (err: any) {
      setTrial(null);
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const verifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await postGymData("/memberships/trial/verify-otp", {
        phone: trialForm.phone,
        otp_code: otpCode,
      });
      setActivated(res);
      setToast({ kind: "ok", text: res.message });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const changeStage = async (leadId: number, stage: string) => {
    try {
      const res = await putGymData(`/memberships/leads/${leadId}`, { stage });
      setToast({ kind: "ok", text: res.message });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const convert = async (leadId: number) => {
    if (!convertPlan) {
      setToast({ kind: "err", text: "Vui lòng chọn gói tập để chốt." });
      return;
    }
    setBusy(true);
    try {
      const res = await postGymData(
        `/memberships/leads/${leadId}/convert?plan_id=${convertPlan}`,
        {}
      );
      setToast({ kind: "ok", text: res.message });
      setConvertId(null);
      setConvertPlan("");
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const pipelineCounts = useMemo(() => {
    const p = leads?.pipeline ?? {};
    return STAGE_ORDER.map((s) => ({
      stage: s,
      label: LEAD_STAGE_LABELS[s] ?? s,
      count: p[s] ?? 0,
    }));
  }, [leads]);

  const maxStage = Math.max(1, ...pipelineCounts.map((p) => p.count));

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <Chip>LỄ TÂN - TƯ VẤN</Chip>
          <h1>Khách Tập Thử &amp; Phễu Chuyển Đổi</h1>
          <p>
            Cấp vé tập thử miễn phí có xác thực OTP, theo dõi khách hàng tiềm năng qua 6 trạng
            thái và chốt gói thành hội viên chính thức.
          </p>
        </div>
        <div className="hg-flex">
          {leads && <Chip tone="gold">{leads.total} khách hàng</Chip>}
          {leads && <Chip tone="ok">Tỷ lệ chốt {leads.conversion_rate}%</Chip>}
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      <div className="hg-tabs">
        <button
          className={`hg-tab ${tab === "pipeline" ? "active" : ""}`}
          onClick={() => setTab("pipeline")}
        >
          Phễu khách hàng
        </button>
        <button
          className={`hg-tab ${tab === "trial" ? "active" : ""}`}
          onClick={() => setTab("trial")}
        >
          Cấp vé tập thử
        </button>
      </div>

      {/* ================= PHỄU KHÁCH HÀNG ================= */}
      {tab === "pipeline" && (
        <div>
          {leads && (
            <>
              <div className="stats-bar">
                <Stat label="Tổng khách hàng" value={leads.total} />
                <Stat label="Đã chốt gói" value={leads.pipeline?.won ?? 0} gold />
                <Stat label="Đang chăm sóc" value={(leads.pipeline?.new ?? 0) + (leads.pipeline?.scheduled ?? 0)} />
                <Stat label="Tỷ lệ chuyển đổi" value={`${leads.conversion_rate}%`} />
              </div>

              <div className="hg-chart-card">
                <div className="hg-chart-title">Phễu chuyển đổi theo trạng thái</div>
                <p className="hg-chart-sub">
                  Bấm vào một trạng thái để lọc danh sách bên dưới. Bấm lại để bỏ lọc.
                </p>
                {pipelineCounts.map((p) => (
                  <div
                    key={p.stage}
                    onClick={() => {
                      const next = stageFilter === p.stage ? "" : p.stage;
                      setStageFilter(next);
                      load(next);
                    }}
                    style={{ cursor: "pointer", marginBottom: "10px" }}
                  >
                    <div className="hg-flex" style={{ justifyContent: "space-between" }}>
                      <span style={{ fontSize: "12.5px", fontWeight: stageFilter === p.stage ? 700 : 500 }}>
                        {p.label}
                      </span>
                      <span className="hg-num-mono" style={{ fontWeight: 600 }}>
                        {p.count}
                      </span>
                    </div>
                    <div
                      style={{
                        height: 8,
                        background: "#eef3f6",
                        border: "1px solid #d4e0e5",
                        marginTop: "4px",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          width: `${(p.count / maxStage) * 100}%`,
                          background: p.stage === "won" ? "#b8860b" : "#0b6e8f",
                          transition: "width .3s ease",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          <SectionTitle>
            Danh sách khách hàng {stageFilter ? `— ${LEAD_STAGE_LABELS[stageFilter]}` : ""}
          </SectionTitle>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Khách hàng</th>
                  <th>Liên hệ</th>
                  <th>Nguồn</th>
                  <th>Trạng thái</th>
                  <th>Đã tập / InBody</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {(leads?.leads ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center" }}>
                      Chưa có khách tập thử nào.
                    </td>
                  </tr>
                ) : (
                  leads.leads.map((l: LeadItem) => (
                    <tr key={l.id}>
                      <td>
                        <strong>{l.full_name}</strong>
                        <div className="hg-exercise-muscle">
                          Tạo cách đây {l.days_since_created} ngày
                          {l.assigned_to ? ` · Phụ trách: ${l.assigned_to}` : ""}
                        </div>
                      </td>
                      <td>
                        <span className="hg-num-mono">{l.phone}</span>
                        {l.email && <div className="hg-exercise-muscle">{l.email}</div>}
                      </td>
                      <td>
                        <Chip>{l.source}</Chip>
                      </td>
                      <td>
                        <select
                          className="input-box"
                          style={{ marginBottom: 0, minWidth: "160px" }}
                          value={l.stage}
                          onChange={(e) => changeStage(l.id, e.target.value)}
                        >
                          {STAGE_ORDER.map((s) => (
                            <option key={s} value={s}>
                              {LEAD_STAGE_LABELS[s] ?? s}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td style={{ fontSize: "12.5px" }}>
                        <div>{l.first_visit_at ? "Đã tập buổi 1" : "Chưa tập"}</div>
                        <div className="hg-exercise-muscle">
                          {l.inbody_done_at ? "Đã đo InBody" : "Chưa đo InBody"}
                        </div>
                      </td>
                      <td>
                        {l.stage === "won" ? (
                          <Chip tone="ok">ĐÃ LÀ HỘI VIÊN</Chip>
                        ) : convertId === l.id ? (
                          <div className="hg-flex" style={{ gap: "4px" }}>
                            <select
                              className="input-box"
                              style={{ marginBottom: 0, minWidth: "150px" }}
                              value={convertPlan}
                              onChange={(e) => setConvertPlan(e.target.value)}
                            >
                              <option value="">Chọn gói...</option>
                              {plans.map((p) => (
                                <option key={p.id} value={p.id}>
                                  {p.name} — {Number(p.price).toLocaleString("vi-VN")}đ
                                </option>
                              ))}
                            </select>
                            <button
                              className="hg-btn-primary hg-btn-sm"
                              onClick={() => convert(l.id)}
                              disabled={busy}
                            >
                              Chốt
                            </button>
                            <button
                              className="hg-btn-ghost hg-btn-sm"
                              onClick={() => setConvertId(null)}
                            >
                              Hủy
                            </button>
                          </div>
                        ) : (
                          <button
                            className="hg-btn-primary hg-btn-sm"
                            onClick={() => {
                              setConvertId(l.id);
                              setConvertPlan("");
                            }}
                          >
                            Chốt gói
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {convertId && (
            <Note tone="gold">
              Khi chốt gói, hệ thống tự tạo hồ sơ hội viên, hợp đồng, phiếu thu và áp dụng quyền
              lợi theo hạng thẻ. Khách hàng chuyển thẳng sang trạng thái &quot;Đã chốt gói&quot;.
            </Note>
          )}
        </div>
      )}

      {/* ================= CẤP VÉ TẬP THỬ ================= */}
      {tab === "trial" && (
        <div className="hg-grid-2">
          <div className="hg-chart-card">
            <div className="hg-chart-title">Đăng ký tập thử miễn phí</div>
            <p className="hg-chart-sub">
              Mỗi số điện thoại chỉ được dùng ưu đãi tập thử MỘT LẦN. Hệ thống tự chặn nếu số này
              đã có thẻ hội viên đang hiệu lực hoặc đã từng đăng ký.
            </p>

            <form onSubmit={registerTrial}>
              <label>Họ và tên</label>
              <input
                className="input-box"
                value={trialForm.full_name}
                onChange={(e) => setTrialForm({ ...trialForm, full_name: e.target.value })}
                placeholder="VD: Nguyễn Văn A"
                required
              />
              <label>Số điện thoại</label>
              <input
                className="input-box"
                value={trialForm.phone}
                onChange={(e) => setTrialForm({ ...trialForm, phone: e.target.value })}
                placeholder="VD: 0901234567"
                required
              />
              <label>Số ngày tập thử (1-14)</label>
              <input
                className="input-box"
                type="number"
                min={1}
                max={14}
                value={trialForm.days}
                onChange={(e) => setTrialForm({ ...trialForm, days: e.target.value })}
              />
              <button className="hg-btn-primary" style={{ width: "100%" }} disabled={busy}>
                {busy && <span className="hg-spinner" />}
                Tạo vé tập thử
              </button>
            </form>

            {trial && (
              <div style={{ marginTop: "18px" }}>
                <Note tone="ok">{trial.message}</Note>
                <div className="hg-kv">
                  <span>Mã QR vé</span>
                  <span className="hg-num-mono" style={{ fontWeight: 600 }}>
                    {trial.qr_code}
                  </span>
                </div>
                <div className="hg-kv">
                  <span>Hiệu lực</span>
                  <span className="hg-num-mono">
                    {trial.start_date} → {trial.end_date} ({trial.days} ngày)
                  </span>
                </div>
                {trial.debug_otp && (
                  <Note tone="gold">
                    Mã OTP (chế độ demo): <strong className="hg-num-mono">{trial.debug_otp}</strong>
                    <div style={{ marginTop: "4px", fontSize: "12px" }}>{trial.otp_note}</div>
                  </Note>
                )}
              </div>
            )}
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Xác thực OTP để kích hoạt</div>
            <p className="hg-chart-sub">
              Vé tập thử chỉ có hiệu lực sau khi xác thực OTP. Nhập sai quá 5 lần sẽ bị khóa và cần
              liên hệ hotline.
            </p>

            <form onSubmit={verifyOtp}>
              <label>Số điện thoại đã đăng ký</label>
              <input
                className="input-box"
                value={trialForm.phone}
                onChange={(e) => setTrialForm({ ...trialForm, phone: e.target.value })}
                placeholder="VD: 0901234567"
                required
              />
              <label>Mã OTP (6 chữ số)</label>
              <input
                className="input-box"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                placeholder="VD: 123456"
                required
              />
              <button className="hg-btn-gold" style={{ width: "100%" }} disabled={busy}>
                {busy && <span className="hg-spinner" />}
                Kích hoạt vé tập thử
              </button>
            </form>

            {activated && (
              <div style={{ marginTop: "18px" }}>
                <Note tone="ok">{activated.message}</Note>
                <div className="hg-kv">
                  <span>Mã QR để vào cổng</span>
                  <span className="hg-num-mono" style={{ fontWeight: 600 }}>
                    {activated.qr_code}
                  </span>
                </div>
                <div className="hg-kv">
                  <span>Hiệu lực đến</span>
                  <span className="hg-num-mono">{activated.end_date}</span>
                </div>
                <div className="hg-kv">
                  <span>Lượt đã dùng</span>
                  <span className="hg-num">{activated.visits_used}</span>
                </div>
                <Note>{activated.note}</Note>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}