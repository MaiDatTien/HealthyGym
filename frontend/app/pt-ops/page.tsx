"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { Chip, Note, SectionTitle, Stat, Toast } from "@/components/ui";
import type {
  BurnPendingItem,
  MyPTPackage,
  PTPackageItem,
} from "@/lib/erp-types";

/* ==========================================================================
   NGHIỆP VỤ HUẤN LUYỆN VIÊN (PT Operations)
     1. Buổi dạy — xác nhận hoàn thành theo cơ chế XÁC NHẬN KÉP (chống gian lận)
     2. Gói buổi tập — danh mục & bán gói
     3. Ca làm việc — đăng ký ca tuần & sinh khung giờ trống
     4. Lương & hoa hồng — bảng lương theo tháng
   ========================================================================== */

export default function PTOpsPage() {
  const [tab, setTab] = useState<"sessions" | "packages" | "shifts" | "payroll">("sessions");
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [role, setRole] = useState("");

  const [overview, setOverview] = useState<any>(null);
  const [pending, setPending] = useState<BurnPendingItem[]>([]);
  const [packages, setPackages] = useState<PTPackageItem[]>([]);
  const [myPackages, setMyPackages] = useState<MyPTPackage[]>([]);
  const [shifts, setShifts] = useState<any[]>([]);
  const [myPayroll, setMyPayroll] = useState<any>(null);
  const [payrollResult, setPayrollResult] = useState<any>(null);

  const today = new Date();
  const [shiftForm, setShiftForm] = useState({
    weekday: "0",
    start_hour: "8",
    end_hour: "17",
  });
  const [purchaseForm, setPurchaseForm] = useState({
    member_id: "",
    package_id: "",
    trainer_id: "",
  });
  const [payrollForm, setPayrollForm] = useState({
    year: String(today.getFullYear()),
    month: String(today.getMonth() + 1),
  });

  const load = () => {
    fetchGymData("/pt/coach/overview").then(setOverview).catch(() => {});
    fetchGymData("/pt-ops/burn/pending").then(setPending).catch(() => {});
    fetchGymData("/pt-ops/packages").then(setPackages).catch(() => {});
    fetchGymData("/pt-ops/packages/my").then(setMyPackages).catch(() => {});
    fetchGymData("/pt-ops/shifts").then(setShifts).catch(() => {});
    fetchGymData("/pt-ops/payroll/my").then(setMyPayroll).catch(() => {});
  };

  useEffect(() => {
    const saved = localStorage.getItem("hg_user");
    if (saved) {
      try {
        setRole(JSON.parse(saved).role ?? "");
      } catch {
        setRole("");
      }
    }
    load();
  }, []);

  const canManage = ["admin", "staff", "receptionist"].includes(role);

  const markComplete = async (bookingId: number) => {
    setBusy(true);
    try {
      const res = await postGymData("/pt-ops/burn/mark", { booking_id: bookingId });
      setToast({ kind: res.check_1_member_checked_in ? "ok" : "err", text: res.message });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const confirmSession = async (bookingId: number, rating: number) => {
    setBusy(true);
    try {
      const res = await postGymData("/pt-ops/burn/confirm", {
        booking_id: bookingId,
        method: "app_button",
        rating,
      });
      setToast({ kind: res.both_confirmed ? "ok" : "err", text: res.message });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const purchasePackage = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await postGymData("/pt-ops/packages/purchase", {
        member_id: Number(purchaseForm.member_id),
        package_id: Number(purchaseForm.package_id),
        trainer_id: purchaseForm.trainer_id ? Number(purchaseForm.trainer_id) : null,
      });
      setToast({ kind: "ok", text: res.message });
      setPurchaseForm({ member_id: "", package_id: "", trainer_id: "" });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const createShift = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await postGymData("/pt-ops/shifts", {
        trainer_id: overview?.trainer?.id ?? 0,
        weekday: Number(shiftForm.weekday),
        start_hour: Number(shiftForm.start_hour),
        end_hour: Number(shiftForm.end_hour),
        branch_id: 1,
      });
      setToast({ kind: "ok", text: res.message });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const generateSlots = async () => {
    if (!overview?.trainer?.id) {
      setToast({ kind: "err", text: "Chưa xác định được Huấn luyện viên." });
      return;
    }
    setBusy(true);
    try {
      const res = await postGymData(
        `/pt-ops/shifts/generate-slots?trainer_id=${overview.trainer.id}&days_ahead=14`,
        {}
      );
      setToast({ kind: "ok", text: res.message });
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const generatePayroll = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await postGymData("/pt-ops/payroll/generate", {
        year: Number(payrollForm.year),
        month: Number(payrollForm.month),
      });
      setPayrollResult(res);
      setToast({ kind: "ok", text: res.message });
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const stats = overview?.stats ?? {};
  const todaySchedule: any[] = overview?.today_schedule ?? [];

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <Chip>NGHIỆP VỤ HUẤN LUYỆN VIÊN</Chip>
          <h1>Buổi Dạy, Gói Tập &amp; Hoa Hồng</h1>
          <p>
            Xác nhận hoàn thành buổi tập theo cơ chế xác nhận kép, quản lý gói buổi tập, ca làm
            việc và bảng lương hoa hồng của Huấn luyện viên.
          </p>
        </div>
        <div className="hg-flex">
          {overview?.trainer && <Chip tone="gold">{overview.trainer.full_name}</Chip>}
          {myPayroll?.rating && <Chip tone="ok">Đánh giá {myPayroll.rating}/5</Chip>}
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      <div className="hg-tabs">
        <button
          className={`hg-tab ${tab === "sessions" ? "active" : ""}`}
          onClick={() => setTab("sessions")}
        >
          Buổi dạy
        </button>
        <button
          className={`hg-tab ${tab === "packages" ? "active" : ""}`}
          onClick={() => setTab("packages")}
        >
          Gói buổi tập
        </button>
        <button
          className={`hg-tab ${tab === "shifts" ? "active" : ""}`}
          onClick={() => setTab("shifts")}
        >
          Ca làm việc
        </button>
        <button
          className={`hg-tab ${tab === "payroll" ? "active" : ""}`}
          onClick={() => setTab("payroll")}
        >
          Lương &amp; Hoa hồng
        </button>
      </div>

      {/* ================= BUỔI DẠY ================= */}
      {tab === "sessions" && (
        <div>
          <div className="stats-bar">
            <Stat label="Học viên phụ trách" value={stats.total_trainees ?? 0} />
            <Stat label="Buổi hôm nay" value={stats.sessions_today ?? 0} gold />
            <Stat label="Buổi sắp tới" value={stats.upcoming_sessions ?? 0} />
            <Stat label="Chờ hội viên xác nhận" value={pending.length} />
          </div>

          <Note tone="gold">
            <strong>Cơ chế xác nhận kép (chống gian lận):</strong> Huấn luyện viên bấm hoàn thành
            là bước 1 — buổi tập <strong>chưa</strong> bị trừ. Chỉ khi hội viên check-in tại cổng
            trong ngày <strong>và</strong> tự xác nhận cuối buổi thì buổi mới được trừ và hoa hồng
            mới được ghi nhận.
          </Note>

          <SectionTitle>Lịch dạy hôm nay</SectionTitle>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Giờ</th>
                  <th>Học viên</th>
                  <th>Mục tiêu buổi tập</th>
                  <th>Trạng thái</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {todaySchedule.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center" }}>
                      Hôm nay chưa có buổi dạy nào.
                    </td>
                  </tr>
                ) : (
                  todaySchedule.map((s) => (
                    <tr key={s.booking_id}>
                      <td className="hg-num-mono" style={{ whiteSpace: "nowrap" }}>
                        {String(s.start_time).slice(11, 16)} — {String(s.end_time).slice(11, 16)}
                      </td>
                      <td>
                        <strong>{s.member_name}</strong>
                      </td>
                      <td style={{ fontSize: "12.5px", color: "#35505c" }}>
                        {s.goal_note ?? "—"}
                      </td>
                      <td>
                        <Chip tone={s.status === "completed" ? "ok" : "default"}>
                          {s.status === "completed" ? "ĐÃ HOÀN THÀNH" : "ĐÃ XÁC NHẬN"}
                        </Chip>
                      </td>
                      <td>
                        {s.status === "confirmed" ? (
                          <button
                            className="hg-btn-primary hg-btn-sm"
                            onClick={() => markComplete(s.booking_id)}
                            disabled={busy}
                          >
                            Bấm hoàn thành
                          </button>
                        ) : (
                          <Chip tone="ok">Đã ghi nhận</Chip>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <SectionTitle>Buổi tập chờ hội viên xác nhận ({pending.length})</SectionTitle>
          <p className="hg-muted" style={{ marginBottom: "12px" }}>
            Hội viên tự xác nhận trên trang <strong>Đặt PT</strong> của họ. Nhắc hội viên mở trang
            đó để bấm xác nhận kèm đánh giá sao — đây là bước 2 bắt buộc để buổi được trừ.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Mã buổi</th>
                  <th>Học viên</th>
                  <th>Check-in cổng</th>
                  <th>Thời điểm HLV bấm</th>
                  <th>Hướng dẫn hội viên</th>
                </tr>
              </thead>
              <tbody>
                {pending.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center" }}>
                      Không có buổi tập nào đang chờ xác nhận.
                    </td>
                  </tr>
                ) : (
                  pending.map((p) => (
                    <tr key={p.booking_id}>
                      <td className="hg-num-mono">#{p.booking_id}</td>
                      <td>
                        <strong>{p.member_name}</strong>
                      </td>
                      <td>
                        <Chip tone={p.member_checked_in ? "ok" : "danger"}>
                          {p.member_checked_in ? "ĐÃ CHECK-IN" : "CHƯA CHECK-IN"}
                        </Chip>
                      </td>
                      <td className="hg-num-mono" style={{ fontSize: "12.5px" }}>
                        {p.trainer_marked_at ? String(p.trainer_marked_at).slice(0, 16).replace("T", " ") : "—"}
                      </td>
                      <td style={{ fontSize: "12.5px" }}>
                        {p.member_checked_in ? (
                          <span style={{ color: "#0f7a52" }}>
                            Đủ điều kiện 1/2 — nhắc hội viên bấm xác nhận cuối buổi để trừ buổi.
                          </span>
                        ) : (
                          <span style={{ color: "#b01c2e" }}>
                            Hội viên chưa check-in tại cổng hôm nay — cần check-in trước, nếu không
                            buổi sẽ không được trừ.
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <SectionTitle>Gói buổi tập của học viên</SectionTitle>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Gói</th>
                  <th>Huấn luyện viên</th>
                  <th>Đã dùng / Tổng</th>
                  <th>Còn lại</th>
                  <th>Hạn dùng</th>
                  <th>Cảnh báo</th>
                </tr>
              </thead>
              <tbody>
                {myPackages.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center" }}>
                      Chưa có gói buổi tập nào.
                    </td>
                  </tr>
                ) : (
                  myPackages.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <strong>{p.package_name}</strong>
                      </td>
                      <td>{p.trainer_name ?? "—"}</td>
                      <td className="hg-num">
                        {p.sessions_used} / {p.sessions_total}
                      </td>
                      <td className="hg-num-mono" style={{ fontWeight: 600 }}>
                        {p.sessions_remaining} buổi
                      </td>
                      <td className="hg-num-mono">{p.expiry_date}</td>
                      <td>
                        {p.warning ? (
                          <Chip tone="warn">{p.days_remaining} ngày còn lại</Chip>
                        ) : (
                          <Chip tone="ok">{p.days_remaining} ngày</Chip>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================= GÓI BUỔI TẬP ================= */}
      {tab === "packages" && (
        <div>
          <SectionTitle>Danh mục gói buổi tập</SectionTitle>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))" }}>
            {packages.map((p) => (
              <div key={p.id} className="card" style={{ gap: "8px", padding: "14px" }}>
                <div className="hg-flex" style={{ justifyContent: "space-between" }}>
                  <Chip tone="gold">{p.tier.toUpperCase()}</Chip>
                  <Chip>{p.sessions} buổi</Chip>
                </div>
                <div style={{ fontWeight: 600, fontSize: "14px" }}>{p.name}</div>
                <div className="hg-num-mono" style={{ fontSize: "17px", fontWeight: 600 }}>
                  {Number(p.price).toLocaleString("vi-VN")}đ
                </div>
                <div className="hg-muted" style={{ fontSize: "12.5px" }}>
                  {Number(p.price_per_session).toLocaleString("vi-VN")}đ/buổi · Hạn{" "}
                  {p.validity_days} ngày
                </div>
                <div className="hg-flex" style={{ gap: "4px", flexWrap: "wrap" }}>
                  <Chip tone={p.includes_inbody ? "ok" : "default"}>
                    {p.includes_inbody ? "CÓ INBODY" : "KHÔNG INBODY"}
                  </Chip>
                  <Chip tone={p.includes_nutrition ? "ok" : "default"}>
                    {p.includes_nutrition ? "CÓ DINH DƯỠNG" : "KHÔNG DINH DƯỠNG"}
                  </Chip>
                </div>
                {p.description && <div className="hg-muted" style={{ fontSize: "12.5px" }}>{p.description}</div>}
              </div>
            ))}
          </div>

          <SectionTitle>Bán gói buổi tập</SectionTitle>
          <div className="hg-grid-2">
            <div className="hg-chart-card">
              <div className="hg-chart-title">Kích hoạt gói cho hội viên</div>
              <p className="hg-chart-sub">
                Hệ thống tự kiểm tra giới hạn số học viên của Huấn luyện viên trước khi gán.
              </p>
              <form onSubmit={purchasePackage}>
                <label>Mã hội viên</label>
                <input
                  className="input-box"
                  type="number"
                  value={purchaseForm.member_id}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, member_id: e.target.value })}
                  placeholder="VD: 1"
                  required
                />
                <label>Gói buổi tập</label>
                <select
                  className="input-box"
                  value={purchaseForm.package_id}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, package_id: e.target.value })}
                  required
                >
                  <option value="">Chọn gói...</option>
                  {packages.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} — {p.sessions} buổi — {Number(p.price).toLocaleString("vi-VN")}đ
                    </option>
                  ))}
                </select>
                <label>Mã Huấn luyện viên phụ trách (không bắt buộc)</label>
                <input
                  className="input-box"
                  type="number"
                  value={purchaseForm.trainer_id}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, trainer_id: e.target.value })}
                  placeholder="Bỏ trống để gán sau"
                />
                <button className="hg-btn-primary" style={{ width: "100%" }} disabled={busy || !canManage}>
                  {busy && <span className="hg-spinner" />}
                  Kích hoạt gói
                </button>
              </form>
              {!canManage && (
                <Note tone="danger">
                  Chỉ Lễ tân, Quản lý cơ sở vật chất hoặc Quản trị viên mới có quyền bán gói.
                </Note>
              )}
            </div>

            <div className="hg-chart-card">
              <div className="hg-chart-title">Chính sách hủy lịch &amp; vắng mặt</div>
              <div className="hg-kv">
                <span>Hủy trước 6 giờ</span>
                <span>
                  <Chip tone="ok">HOÀN BUỔI</Chip>
                </span>
              </div>
              <div className="hg-kv">
                <span>Hủy sát giờ (dưới 6 giờ)</span>
                <span>
                  <Chip tone="warn">TRỪ BUỔI</Chip>
                </span>
              </div>
              <div className="hg-kv">
                <span>Không đến (no-show)</span>
                <span>
                  <Chip tone="danger">TRỪ BUỔI</Chip>
                </span>
              </div>
              <Note>
                Chính sách này bảo vệ thời gian của Huấn luyện viên và được hệ thống tự áp dụng khi
                hủy lịch hoặc quét no-show.
              </Note>
              <div className="hg-kv">
                <span>Đổi Huấn luyện viên</span>
                <span>
                  <Chip tone="ok">MIỄN PHÍ</Chip>
                </span>
              </div>
              <p className="hg-muted" style={{ fontSize: "12.5px" }}>
                Khi đổi Huấn luyện viên, toàn bộ hồ sơ sức khỏe, chấn thương và lịch sử mức tạ được
                chuyển giao nguyên vẹn cho người mới.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ================= CA LÀM VIỆC ================= */}
      {tab === "shifts" && (
        <div className="hg-grid-2">
          <div className="hg-chart-card">
            <div className="hg-chart-title">Đăng ký ca làm việc</div>
            <p className="hg-chart-sub">
              Khai báo ca làm việc trong tuần, sau đó sinh khung giờ trống để hội viên đặt lịch.
            </p>
            <form onSubmit={createShift}>
              <label>Thứ trong tuần</label>
              <select
                className="input-box"
                value={shiftForm.weekday}
                onChange={(e) => setShiftForm({ ...shiftForm, weekday: e.target.value })}
              >
                {["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"].map(
                  (d, i) => (
                    <option key={i} value={i}>
                      {d}
                    </option>
                  )
                )}
              </select>
              <label>Giờ bắt đầu (0-23)</label>
              <input
                className="input-box"
                type="number"
                min={0}
                max={23}
                value={shiftForm.start_hour}
                onChange={(e) => setShiftForm({ ...shiftForm, start_hour: e.target.value })}
              />
              <label>Giờ kết thúc (1-24)</label>
              <input
                className="input-box"
                type="number"
                min={1}
                max={24}
                value={shiftForm.end_hour}
                onChange={(e) => setShiftForm({ ...shiftForm, end_hour: e.target.value })}
              />
              <button className="hg-btn-primary" style={{ width: "100%" }} disabled={busy}>
                {busy && <span className="hg-spinner" />}
                Đăng ký ca
              </button>
            </form>

            <button
              className="hg-btn-gold"
              style={{ width: "100%", marginTop: "10px" }}
              onClick={generateSlots}
              disabled={busy}
            >
              Sinh khung giờ trống 14 ngày tới
            </button>
            <Note>
              Mỗi khung giờ dài 60 phút. Hệ thống tự bỏ qua khung giờ đã tồn tại hoặc đã qua.
            </Note>
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Danh sách ca làm việc ({shifts.length})</div>
            <div style={{ maxHeight: "460px", overflowY: "auto" }}>
              {shifts.length === 0 ? (
                <div className="hg-empty">Chưa có ca làm việc nào được đăng ký.</div>
              ) : (
                shifts.map((s) => (
                  <div key={s.id} className="hg-kv">
                    <span>
                      <strong>{s.trainer_name}</strong>
                      <div className="hg-exercise-muscle">{s.weekday_name}</div>
                    </span>
                    <span className="hg-num-mono" style={{ fontWeight: 600 }}>
                      {s.time_range}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ================= LƯƠNG & HOA HỒNG ================= */}
      {tab === "payroll" && (
        <div>
          {myPayroll && (
            <div className="stats-bar">
              <Stat
                label="Lương cứng"
                value={`${Number(myPayroll.base_salary ?? 0).toLocaleString("vi-VN")}đ`}
              />
              <Stat label="Hoa hồng bán gói" value={myPayroll.sale_commission_rate} gold />
              <Stat
                label="Thù lao mỗi buổi dạy"
                value={`${Number(myPayroll.burn_fee_per_session ?? 0).toLocaleString("vi-VN")}đ`}
              />
              <Stat label="Học viên đang phụ trách" value={myPayroll.current_trainees ?? 0} />
            </div>
          )}

          <SectionTitle>Bảng lương của tôi</SectionTitle>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Kỳ</th>
                  <th>Lương cứng</th>
                  <th>Doanh số gói</th>
                  <th>Hoa hồng bán</th>
                  <th>Buổi đã dạy</th>
                  <th>Thù lao dạy</th>
                  <th>Thưởng 5 sao</th>
                  <th>Tổng lĩnh</th>
                </tr>
              </thead>
              <tbody>
                {(myPayroll?.payrolls ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: "center" }}>
                      Chưa có bảng lương nào. Quản trị viên cần chạy tính lương trước.
                    </td>
                  </tr>
                ) : (
                  myPayroll.payrolls.map((p: any) => (
                    <tr key={p.period}>
                      <td className="hg-num-mono" style={{ fontWeight: 600 }}>
                        {p.period}
                      </td>
                      <td className="hg-num-mono">{Number(p.base_salary).toLocaleString("vi-VN")}đ</td>
                      <td className="hg-num-mono">
                        {Number(p.packages_sold_amount).toLocaleString("vi-VN")}đ
                      </td>
                      <td className="hg-num-mono" style={{ color: "#0f7a52" }}>
                        {Number(p.sale_commission).toLocaleString("vi-VN")}đ
                      </td>
                      <td className="hg-num">{p.sessions_delivered}</td>
                      <td className="hg-num-mono">
                        {Number(p.delivery_commission).toLocaleString("vi-VN")}đ
                      </td>
                      <td className="hg-num-mono">
                        {Number(p.five_star_bonus).toLocaleString("vi-VN")}đ
                      </td>
                      <td className="hg-num-mono" style={{ fontWeight: 700 }}>
                        {Number(p.total_pay).toLocaleString("vi-VN")}đ
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <SectionTitle>Chạy tính lương tháng</SectionTitle>
          <div className="hg-grid-2">
            <div className="hg-chart-card">
              <div className="hg-chart-title">Tính lương &amp; hoa hồng</div>
              <p className="hg-chart-sub">
                Lương cứng + (Doanh số gói x % hoa hồng) + (Số buổi hoàn thành x Thù lao/buổi) +
                (Số buổi 5 sao x Thưởng)
              </p>
              <form onSubmit={generatePayroll}>
                <label>Năm</label>
                <input
                  className="input-box"
                  type="number"
                  value={payrollForm.year}
                  onChange={(e) => setPayrollForm({ ...payrollForm, year: e.target.value })}
                />
                <label>Tháng</label>
                <input
                  className="input-box"
                  type="number"
                  min={1}
                  max={12}
                  value={payrollForm.month}
                  onChange={(e) => setPayrollForm({ ...payrollForm, month: e.target.value })}
                />
                <button className="hg-btn-primary" style={{ width: "100%" }} disabled={busy || !canManage}>
                  {busy && <span className="hg-spinner" />}
                  Tính lương
                </button>
              </form>
              {!canManage && (
                <Note tone="danger">
                  Chỉ Lễ tân, Quản lý cơ sở vật chất hoặc Quản trị viên mới có quyền chạy tính lương.
                </Note>
              )}
            </div>

            <div className="hg-chart-card">
              <div className="hg-chart-title">Kết quả tính lương</div>
              {!payrollResult ? (
                <div className="hg-empty">Chưa chạy tính lương.</div>
              ) : (
                <>
                  <Note tone="ok">{payrollResult.message}</Note>
                  <div className="hg-kv">
                    <span>Kỳ lương</span>
                    <span className="hg-num-mono">{payrollResult.period}</span>
                  </div>
                  <div className="hg-kv">
                    <span>Tổng quỹ lương</span>
                    <span className="hg-num-mono" style={{ fontWeight: 700 }}>
                      {Number(payrollResult.total_payroll).toLocaleString("vi-VN")}đ
                    </span>
                  </div>
                  {payrollResult.trainers.map((t: any) => (
                    <div key={t.trainer_id} className="hg-kv">
                      <span>
                        <strong>{t.trainer_name}</strong>
                        <div className="hg-exercise-muscle">
                          {t.sessions_delivered} buổi · hoa hồng {t.commission_rate} ·{" "}
                          {t.five_star_sessions} buổi 5 sao
                        </div>
                      </span>
                      <span className="hg-num-mono" style={{ fontWeight: 600 }}>
                        {Number(t.total_pay).toLocaleString("vi-VN")}đ
                      </span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}