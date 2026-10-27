"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { Chip, Note, SectionTitle, Stat, Toast } from "@/components/ui";
import type { GateScanResult, LockerStatus } from "@/lib/erp-types";

/* ==========================================================================
   LỄ TÂN — Quầy làm việc: quét QR cổng, cấp/thu tủ đồ & khăn, check-in thủ công.
   Đây là màn hình vận hành chính của vai trò Receptionist.
   ========================================================================== */

export default function FrontDeskPage() {
  const [qrInput, setQrInput] = useState("");
  const [scan, setScan] = useState<GateScanResult | null>(null);
  const [history, setHistory] = useState<any>(null);
  const [lockers, setLockers] = useState<LockerStatus | null>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [tab, setTab] = useState<"gate" | "locker" | "debt">("gate");
  const [busy, setBusy] = useState(false);

  // Cấp tủ
  const [assignForm, setAssignForm] = useState({
    member_id: "",
    zone: "male",
    towels: "1",
  });
  const [activeAssignments, setActiveAssignments] = useState<any[]>([]);
  const [debt, setDebt] = useState<any>(null);

  const load = () => {
    fetchGymData("/gym-ops/gate/history?limit=40").then(setHistory).catch(() => {});
    fetchGymData("/gym-ops/lockers/status").then(setLockers).catch(() => {});
    fetchGymData("/memberships/debt/overdue").then(setDebt).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  const doScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!qrInput.trim()) return;
    setBusy(true);
    try {
      const res = await postGymData("/gym-ops/gate/scan", {
        qr_token: qrInput.trim(),
        branch_id: 1,
        direction: "in",
      });
      setScan(res);
      setToast({
        kind: res.granted ? "ok" : "err",
        text: res.message,
      });
      setQrInput("");
      load();
    } catch (err: any) {
      setScan(null);
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const assignLocker = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await postGymData("/gym-ops/lockers/assign", {
        member_id: Number(assignForm.member_id),
        zone: assignForm.zone,
        towels: Number(assignForm.towels),
      });
      setToast({ kind: "ok", text: res.message });
      setAssignForm({ ...assignForm, member_id: "" });
      fetchGymData("/gym-ops/lockers/status").then(setLockers).catch(() => {});
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const returnLocker = async (assignmentId: number, towelsIssued: number) => {
    try {
      const res = await postGymData(`/gym-ops/lockers/${assignmentId}/return`, {
        towels_returned: towelsIssued,
        key_returned: true,
        penalty_amount: 0,
      });
      setToast({ kind: "ok", text: res.message });
      fetchGymData("/gym-ops/lockers/status").then(setLockers).catch(() => {});
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const checkKey = (checks: Record<string, unknown>, key: string) => checks?.[key];

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <Chip>LỄ TÂN - TƯ VẤN</Chip>
          <h1>Quầy Làm Việc</h1>
          <p>Quét QR động tại cổng, cấp phát tủ đồ và khăn tập, theo dõi công nợ.</p>
        </div>
        <div className="hg-flex">
          {lockers && <Chip tone="ok">{lockers.available} tủ trống</Chip>}
          {debt && debt.total_members > 0 && (
            <Chip tone="danger">{debt.total_members} hội viên nợ quá hạn</Chip>
          )}
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      <div className="hg-tabs">
        <button className={`hg-tab ${tab === "gate" ? "active" : ""}`} onClick={() => setTab("gate")}>
          Cổng Check-in
        </button>
        <button className={`hg-tab ${tab === "locker" ? "active" : ""}`} onClick={() => setTab("locker")}>
          Tủ đồ &amp; Khăn
        </button>
        <button className={`hg-tab ${tab === "debt" ? "active" : ""}`} onClick={() => setTab("debt")}>
          Công nợ
        </button>
      </div>

      {/* ================= CỔNG CHECK-IN ================= */}
      {tab === "gate" && (
        <div className="hg-grid-2">
          <div className="hg-chart-card">
            <div className="hg-chart-title">Quét mã QR động</div>
            <p className="hg-chart-sub">
              Hội viên mở app lấy mã mới. Mã chỉ có hiệu lực 60 giây và không dùng lại được.
            </p>

            <form onSubmit={doScan}>
              <input
                className="input-box"
                placeholder="Dán hoặc quét mã QR (DG-... hoặc TRIAL-...)"
                value={qrInput}
                onChange={(e) => setQrInput(e.target.value)}
                autoFocus
              />
              <button className="hg-btn-primary" style={{ width: "100%" }} disabled={busy}>
                {busy && <span className="hg-spinner" />}
                Kiểm tra và cho vào
              </button>
            </form>

            {scan && (
              <div style={{ marginTop: "18px" }}>
                <div
                  className={`hg-toast ${scan.granted ? "ok" : "err"}`}
                  style={{ marginBottom: "14px" }}
                >
                  {scan.message}
                </div>

                <div className="hg-metric-label" style={{ marginBottom: "8px" }}>
                  Kết quả kiểm tra 4 điều kiện
                </div>
                <div className="hg-kv">
                  <span>1. Thẻ còn hiệu lực</span>
                  <span>
                    <Chip tone={checkKey(scan.checks, "membership_active") ? "ok" : "danger"}>
                      {checkKey(scan.checks, "membership_active") ? "ĐẠT" : "KHÔNG ĐẠT"}
                    </Chip>
                  </span>
                </div>
                <div className="hg-kv">
                  <span>2. Chi nhánh hợp lệ</span>
                  <span>
                    <Chip tone={checkKey(scan.checks, "branch_valid") ? "ok" : "danger"}>
                      {checkKey(scan.checks, "branch_valid") ? "ĐẠT" : "KHÔNG ĐẠT"}
                    </Chip>
                  </span>
                </div>
                <div className="hg-kv">
                  <span>3. Khung giờ hợp lệ</span>
                  <span>
                    <Chip tone={checkKey(scan.checks, "time_window_valid") ? "ok" : "warn"}>
                      {checkKey(scan.checks, "time_window_valid") ? "ĐẠT" : "PHỤ PHÍ"}
                    </Chip>
                  </span>
                </div>
                <div className="hg-kv">
                  <span>4. Có lịch hẹn sắp tới</span>
                  <span>
                    <Chip tone={checkKey(scan.checks, "upcoming_booking") ? "gold" : "default"}>
                      {checkKey(scan.checks, "upcoming_booking") ? "CÓ" : "KHÔNG"}
                    </Chip>
                  </span>
                </div>

                {scan.upcoming_pt_session && (
                  <Note tone="gold">
                    <strong>Nhắc HLV:</strong> hội viên có lịch tập 1-1 với{" "}
                    {scan.upcoming_pt_session.trainer_name} lúc{" "}
                    {String(scan.upcoming_pt_session.start_time).slice(11, 16)} (còn{" "}
                    {scan.upcoming_pt_session.minutes_until} phút).
                  </Note>
                )}

                {scan.upcoming_class && (
                  <Note tone="gold">
                    <strong>Nhắc lớp học:</strong> {scan.upcoming_class.class_name} bắt đầu lúc{" "}
                    {String(scan.upcoming_class.start_time).slice(11, 16)}.
                  </Note>
                )}

                {scan.surcharge_amount > 0 && (
                  <Note tone="danger">
                    Thu phụ phí nâng khung giờ:{" "}
                    <strong className="hg-num-mono">
                      {scan.surcharge_amount.toLocaleString("vi-VN")}đ
                    </strong>
                  </Note>
                )}

                {scan.points_awarded > 0 && (
                  <Note tone="ok">
                    Đã cộng {scan.points_awarded} điểm thưởng. Tổng điểm:{" "}
                    <strong className="hg-num-mono">{scan.loyalty_points}</strong>
                  </Note>
                )}
              </div>
            )}
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Lịch sử ra/vào gần đây</div>
            {history?.today_denied_count > 0 && (
              <Note tone="danger">
                Hôm nay có {history.today_denied_count} lượt bị từ chối check-in.
              </Note>
            )}
            <div style={{ maxHeight: "460px", overflowY: "auto" }}>
              {(history?.logs ?? []).length === 0 ? (
                <div className="hg-empty">Chưa có lượt check-in nào.</div>
              ) : (
                history.logs.map((g: any) => (
                  <div key={g.id} className="hg-kv">
                    <span>
                      <strong>{g.member_name ?? "Khách tập thử"}</strong>
                      <div className="hg-exercise-muscle">
                        {new Date(g.checkin_time).toLocaleTimeString("vi-VN", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}{" "}
                        · {g.direction === "in" ? "VÀO" : "RA"} · {g.verified_by}
                      </div>
                    </span>
                    <span>
                      <Chip tone={g.result === "granted" ? "ok" : "danger"}>
                        {g.result === "granted" ? "ĐẠT" : "TỪ CHỐI"}
                      </Chip>
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ================= TỦ ĐỒ ================= */}
      {tab === "locker" && (
        <div>
          <div className="hg-grid-2">
            <div className="hg-chart-card">
              <div className="hg-chart-title">Cấp tủ và khăn</div>
              <p className="hg-chart-sub">
                Hệ thống tự chọn tủ trống theo khu vực. Nhắc hội viên trả chìa khóa và khăn khi ra về.
              </p>
              <form onSubmit={assignLocker}>
                <label>Mã hội viên</label>
                <input
                  className="input-box"
                  type="number"
                  placeholder="VD: 1"
                  value={assignForm.member_id}
                  onChange={(e) => setAssignForm({ ...assignForm, member_id: e.target.value })}
                  required
                />
                <label>Khu vực tủ</label>
                <select
                  className="input-box"
                  value={assignForm.zone}
                  onChange={(e) => setAssignForm({ ...assignForm, zone: e.target.value })}
                >
                  <option value="male">Khu Nam</option>
                  <option value="female">Khu Nữ</option>
                  <option value="vip">Khu VIP</option>
                </select>
                <label>Số khăn phát</label>
                <input
                  className="input-box"
                  type="number"
                  min={0}
                  max={5}
                  value={assignForm.towels}
                  onChange={(e) => setAssignForm({ ...assignForm, towels: e.target.value })}
                />
                <button className="hg-btn-primary" style={{ width: "100%" }}>
                  Cấp tủ và khăn
                </button>
              </form>
              <Note>
                Phí phạt tự động khi thu hồi: mất khăn 100.000đ/cái, mất chìa khóa tủ 200.000đ.
              </Note>
            </div>

            <div className="hg-chart-card">
              <div className="hg-chart-title">Tình trạng tủ đồ</div>
              {lockers ? (
                <>
                  <div className="hg-metric-grid">
                    <Stat label="Tổng tủ" value={lockers.total} />
                    <Stat label="Trống" value={lockers.available} gold />
                    <Stat label="Đang dùng" value={lockers.occupied} />
                  </div>
                  <div style={{ maxHeight: "300px", overflowY: "auto" }}>
                    {lockers.lockers.slice(0, 40).map((l) => (
                      <div key={l.code} className="hg-kv">
                        <span>
                          <strong className="hg-num-mono">{l.code}</strong>
                          <div className="hg-exercise-muscle">
                            {l.zone === "male" ? "Nam" : l.zone === "female" ? "Nữ" : "VIP"}
                            {l.kind === "private" ? " · Tủ cố định" : " · Tủ ngày"}
                          </div>
                        </span>
                        <span>
                          {l.is_available ? (
                            <Chip tone="ok">TRỐNG</Chip>
                          ) : (
                            <Chip tone="warn">{l.holder ?? "ĐANG DÙNG"}</Chip>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="hg-empty">Đang tải...</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ================= CÔNG NỢ ================= */}
      {tab === "debt" && (
        <div>
          {debt && (
            <div className="stats-bar">
              <Stat label="Hội viên nợ quá hạn" value={debt.total_members} />
              <Stat
                label="Tổng tiền quá hạn"
                value={`${Number(debt.total_overdue).toLocaleString("vi-VN")}đ`}
                gold
              />
            </div>
          )}
          <Note tone="danger">
            Hội viên có công nợ quá hạn sẽ bị TỰ ĐỘNG KHÓA THẺ khi quét QR tại cổng. Hệ thống tự
            mở khóa ngay khi thanh toán đủ.
          </Note>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Hội viên</th>
                  <th>Số điện thoại</th>
                  <th>Số tiền quá hạn</th>
                  <th>Số ngày quá hạn</th>
                </tr>
              </thead>
              <tbody>
                {(debt?.members ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: "center" }}>
                      Không có hội viên nào nợ quá hạn.
                    </td>
                  </tr>
                ) : (
                  debt.members.map((m: any) => (
                    <tr key={m.member_id}>
                      <td>
                        <strong>{m.full_name}</strong>
                      </td>
                      <td className="hg-num-mono">{m.phone}</td>
                      <td className="hg-num-mono" style={{ color: "#b01c2e", fontWeight: 600 }}>
                        {Number(m.overdue_amount).toLocaleString("vi-VN")}đ
                      </td>
                      <td className="hg-num">{m.days_overdue} ngày</td>
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