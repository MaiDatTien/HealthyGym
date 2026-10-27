"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { Chip, KV, Note, SectionTitle, Stat, Toast } from "@/components/ui";
import type { Contract, Installment, MyPTPackage, UpgradeQuote } from "@/lib/erp-types";
import { CONTRACT_STATUS_LABELS } from "@/lib/erp-types";

/* ==========================================================================
   HỢP ĐỒNG CỦA TÔI — Quản lý gói tập: bảo lưu, chuyển nhượng, nâng cấp
   (khấu trừ prorated), lịch trả góp, ví trả trước và gói PT.
   ========================================================================== */

export default function ContractPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [installments, setInstallments] = useState<any>(null);
  const [wallet, setWallet] = useState<any>(null);
  const [ptPackages, setPtPackages] = useState<MyPTPackage[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [quote, setQuote] = useState<UpgradeQuote | null>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [tab, setTab] = useState<"overview" | "lifecycle" | "money" | "pt">("overview");

  const [freezeDays, setFreezeDays] = useState("14");
  const [freezeReason, setFreezeReason] = useState("");
  const [transferForm, setTransferForm] = useState({ name: "", phone: "", email: "" });
  const [upgradePlanId, setUpgradePlanId] = useState("");

  const load = () => {
    fetchGymData("/memberships/contracts/my").then(setContracts).catch(() => {});
    fetchGymData("/memberships/installments/my").then(setInstallments).catch(() => {});
    fetchGymData("/memberships/wallet/my").then(setWallet).catch(() => {});
    fetchGymData("/pt-ops/packages/my").then(setPtPackages).catch(() => {});
    fetchGymData("/listings/plans").then(setPlans).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  const active = contracts.find((c) => c.status === "active" || c.status === "frozen") ?? contracts[0];

  const requestFreeze = async () => {
    try {
      const res = await postGymData("/memberships/freeze/request", {
        days: Number(freezeDays),
        reason: freezeReason || null,
      });
      setToast({ kind: "ok", text: res.message });
      setFreezeReason("");
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const unfreeze = async () => {
    try {
      const res = await postGymData("/memberships/freeze/unfreeze");
      setToast({ kind: "ok", text: res.message });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const requestTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await postGymData("/memberships/transfer/request", {
        to_full_name: transferForm.name,
        to_phone: transferForm.phone,
        to_email: transferForm.email || null,
      });
      setToast({ kind: "ok", text: res.message });
      setTransferForm({ name: "", phone: "", email: "" });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const getQuote = async () => {
    if (!upgradePlanId) return;
    try {
      const q = await fetchGymData(`/memberships/upgrade/quote?new_plan_id=${upgradePlanId}`);
      setQuote(q);
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const doUpgrade = async () => {
    if (!upgradePlanId) return;
    try {
      const res = await postGymData("/memberships/upgrade", {
        new_plan_id: Number(upgradePlanId),
      });
      setToast({ kind: "ok", text: res.message });
      setQuote(null);
      setUpgradePlanId("");
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <Chip>HỢP ĐỒNG HỘI VIÊN</Chip>
          <h1>Gói Tập Của Tôi</h1>
          <p>Quản lý thời hạn, quyền lợi, bảo lưu, chuyển nhượng, nâng cấp và thanh toán.</p>
        </div>
        {wallet && (
          <div className="hg-flex">
            <Chip tone="gold">
              Ví: {Number(wallet.balance).toLocaleString("vi-VN")}đ
            </Chip>
          </div>
        )}
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      {/* Tổng quan hợp đồng */}
      {active ? (
        <>
          <div className="hg-metric-grid">
            <Stat label="Mã hợp đồng" value={active.contract_code} />
            <Stat label="Hạng thẻ" value={active.tier.toUpperCase()} gold />
            <Stat label="Còn lại" value={`${active.days_remaining} ngày`} />
            <Stat label="Hết hạn" value={active.end_date} />
            <Stat
              label="Giá trị còn lại"
              value={`${Number(active.prorated_value).toLocaleString("vi-VN")}đ`}
              gold
            />
          </div>

          <div className="hg-flex" style={{ marginBottom: "18px" }}>
            <Chip
              tone={
                active.status === "active"
                  ? "ok"
                  : active.status === "frozen"
                  ? "warn"
                  : "default"
              }
            >
              {CONTRACT_STATUS_LABELS[active.status] ?? active.status}
            </Chip>
            <Chip>{active.time_window === "off_peak" ? "OFF-PEAK" : "TOÀN THỜI GIAN"}</Chip>
            {active.benefits.sauna && <Chip tone="gold">SAUNA</Chip>}
            {active.benefits.locker && <Chip tone="gold">TỦ CỐ ĐỊNH</Chip>}
            {active.benefits.towel && <Chip>KHĂN MIỄN PHÍ</Chip>}
            {active.benefits.guest_passes_month > 0 && (
              <Chip tone="gold">{active.benefits.guest_passes_month} LƯỢT DẪN KHÁCH/THÁNG</Chip>
            )}
          </div>

          {active.status === "frozen" && (
            <Note tone="warn">
              Thẻ đang trong thời gian bảo lưu. Bạn không thể check-in hoặc đặt lớp. Ngày bảo lưu
              đã được cộng bù vào hạn thẻ.
            </Note>
          )}
        </>
      ) : (
        <div className="hg-empty">
          <h3>Chưa có hợp đồng</h3>
          <p>Vui lòng đăng ký gói tập để bắt đầu sử dụng dịch vụ.</p>
        </div>
      )}

      <div className="hg-tabs">
        <button className={`hg-tab ${tab === "overview" ? "active" : ""}`} onClick={() => setTab("overview")}>
          Tổng quan
        </button>
        <button className={`hg-tab ${tab === "lifecycle" ? "active" : ""}`} onClick={() => setTab("lifecycle")}>
          Bảo lưu &amp; Chuyển nhượng
        </button>
        <button className={`hg-tab ${tab === "money" ? "active" : ""}`} onClick={() => setTab("money")}>
          Thanh toán &amp; Ví
        </button>
        <button className={`hg-tab ${tab === "pt" ? "active" : ""}`} onClick={() => setTab("pt")}>
          Gói PT
        </button>
      </div>

      {/* ================= TỔNG QUAN ================= */}
      {tab === "overview" && active && (
        <div className="hg-grid-2">
          <div className="hg-chart-card">
            <div className="hg-chart-title">Chi tiết hợp đồng</div>
            <KV label="Mã hợp đồng">{active.contract_code}</KV>
            <KV label="Gói tập">{active.plan_name}</KV>
            <KV label="Ngày bắt đầu">{active.start_date}</KV>
            <KV label="Ngày hết hạn">{active.end_date}</KV>
            <KV label="Tổng ngày">{active.days_remaining} ngày còn lại</KV>
            <KV label="Số ngày đã bảo lưu">{active.freeze_days_used} ngày</KV>
            <KV label="Trạng thái thanh toán">
              <Chip
                tone={
                  active.payment_status === "paid"
                    ? "ok"
                    : active.payment_status === "overdue"
                    ? "danger"
                    : "warn"
                }
              >
                {active.payment_status}
              </Chip>
            </KV>
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Nâng cấp gói tập</div>
            <p className="hg-chart-sub">
              Giá trị còn lại của gói hiện tại được khấu trừ trực tiếp vào hoá đơn gói mới.
            </p>
            <label>Chọn gói muốn nâng cấp</label>
            <select
              className="input-box"
              value={upgradePlanId}
              onChange={(e) => {
                setUpgradePlanId(e.target.value);
                setQuote(null);
              }}
            >
              <option value="">— Chọn gói —</option>
              {plans
                .filter((p) => p.id !== undefined)
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {Number(p.price).toLocaleString("vi-VN")}đ
                  </option>
                ))}
            </select>
            <button
              className="hg-btn-ghost"
              onClick={getQuote}
              disabled={!upgradePlanId}
              style={{ width: "100%" }}
            >
              Xem báo giá khấu trừ
            </button>

            {quote && (
              <div style={{ marginTop: "14px" }}>
                <div className="hg-verdict">
                  <h3>Báo giá nâng cấp</h3>
                  <KV label="Gói hiện tại">{quote.current_contract.plan_name}</KV>
                  <KV label="Số ngày còn lại">
                    {quote.current_contract.days_remaining}/
                    {quote.current_contract.duration_days} ngày
                  </KV>
                  <KV label="Giá trị khấu trừ">
                    <span className="hg-num-mono" style={{ color: "#0f7a52", fontWeight: 600 }}>
                      −{Number(quote.prorated_credit).toLocaleString("vi-VN")}đ
                    </span>
                  </KV>
                  <KV label="Gói mới">{quote.new_plan.name}</KV>
                  <KV label="Giá niêm yết">
                    {Number(quote.new_plan.price).toLocaleString("vi-VN")}đ
                  </KV>
                  <KV label="Phải trả thêm">
                    <span className="hg-num-mono" style={{ fontWeight: 700, fontSize: "16px" }}>
                      {Number(quote.amount_due).toLocaleString("vi-VN")}đ
                    </span>
                  </KV>
                </div>
                <Note tone="ok">{quote.savings_note}</Note>
                <button className="hg-btn-gold" style={{ width: "100%" }} onClick={doUpgrade}>
                  Xác nhận nâng cấp
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ================= BẢO LƯU & CHUYỂN NHƯỢNG ================= */}
      {tab === "lifecycle" && (
        <div className="hg-grid-2">
          <div className="hg-chart-card">
            <div className="hg-chart-title">Bảo lưu thẻ tập</div>
            <p className="hg-chart-sub">
              Tạm dừng gói tập khi đi công tác, ốm đau hoặc thai sản. Ngày bảo lưu được cộng bù
              vào hạn thẻ.
            </p>

            <Note>
              <strong>Quy tắc bảo lưu:</strong>
              <ul className="benefit-list" style={{ marginTop: "6px" }}>
                <li>Chỉ áp dụng cho gói từ 3 tháng trở lên</li>
                <li>Thời gian mỗi lần: 7 - 60 ngày</li>
                <li>Tổng không quá 60 ngày trong một năm</li>
                <li>Không thể check-in hoặc đặt lớp trong thời gian bảo lưu</li>
              </ul>
            </Note>

            {active?.status === "frozen" ? (
              <button className="hg-btn-gold" style={{ width: "100%" }} onClick={unfreeze}>
                Mở khóa thẻ sớm
              </button>
            ) : (
              <>
                <label>Số ngày bảo lưu</label>
                <input
                  className="input-box"
                  type="number"
                  min={7}
                  max={60}
                  value={freezeDays}
                  onChange={(e) => setFreezeDays(e.target.value)}
                />
                <label>Lý do (tuỳ chọn)</label>
                <input
                  className="input-box"
                  placeholder="VD: Đi công tác nước ngoài"
                  value={freezeReason}
                  onChange={(e) => setFreezeReason(e.target.value)}
                />
                <div className="hg-flex" style={{ marginBottom: "10px" }}>
                  {["7", "14", "30", "60"].map((d) => (
                    <button
                      key={d}
                      className={freezeDays === d ? "hg-btn-primary hg-btn-sm" : "hg-btn-ghost hg-btn-sm"}
                      onClick={() => setFreezeDays(d)}
                    >
                      {d} ngày
                    </button>
                  ))}
                </div>
                <button className="hg-btn-primary" style={{ width: "100%" }} onClick={requestFreeze}>
                  Gửi yêu cầu bảo lưu
                </button>
              </>
            )}
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Chuyển nhượng gói tập</div>
            <p className="hg-chart-sub">
              Chuyển toàn bộ thời hạn còn lại cho người khác. Hồ sơ của bạn sẽ được đóng lại và
              người nhận có hợp đồng kế thừa.
            </p>

            <Note>
              <strong>Điều kiện:</strong>
              <ul className="benefit-list" style={{ marginTop: "6px" }}>
                <li>Gói còn hạn ít nhất 30 ngày</li>
                <li>Phí chuyển nhượng: 300.000đ</li>
                <li>Không áp dụng cho thẻ đang bảo lưu</li>
              </ul>
            </Note>

            <form onSubmit={requestTransfer}>
              <label>Họ tên người nhận</label>
              <input
                className="input-box"
                value={transferForm.name}
                onChange={(e) => setTransferForm({ ...transferForm, name: e.target.value })}
                required
              />
              <label>Số điện thoại</label>
              <input
                className="input-box"
                value={transferForm.phone}
                onChange={(e) => setTransferForm({ ...transferForm, phone: e.target.value })}
                required
              />
              <label>Email (tuỳ chọn)</label>
              <input
                className="input-box"
                type="email"
                value={transferForm.email}
                onChange={(e) => setTransferForm({ ...transferForm, email: e.target.value })}
              />
              <button className="hg-btn-primary" style={{ width: "100%" }}>
                Gửi yêu cầu chuyển nhượng
              </button>
            </form>
          </div>
        </div>
      )}

      {/* ================= THANH TOÁN & VÍ ================= */}
      {tab === "money" && (
        <div className="hg-grid-2">
          <div className="hg-chart-card">
            <div className="hg-chart-title">Ví trả trước</div>
            {wallet ? (
              <>
                <div className="hg-metric-grid">
                  <Stat
                    label="Số dư hiện tại"
                    value={`${Number(wallet.balance).toLocaleString("vi-VN")}đ`}
                    gold
                  />
                  <Stat
                    label="Tổng đã nạp"
                    value={`${Number(wallet.total_topup).toLocaleString("vi-VN")}đ`}
                  />
                  <Stat
                    label="Tổng đã chi"
                    value={`${Number(wallet.total_spent).toLocaleString("vi-VN")}đ`}
                  />
                </div>
                <Note>
                  Ví trả trước dùng để mua hàng tại quầy Pro-Shop, thuê tủ cố định và các dịch vụ
                  khác mà không cần tiền mặt.
                </Note>
                <SectionTitle>Lịch sử giao dịch</SectionTitle>
                {wallet.transactions.length === 0 ? (
                  <div className="hg-empty">Chưa có giao dịch nào.</div>
                ) : (
                  wallet.transactions.map((t: any) => (
                    <div key={t.id} className="hg-kv">
                      <span>
                        <strong>{t.note ?? t.kind}</strong>
                        <div className="hg-exercise-muscle">
                          {new Date(t.created_at).toLocaleString("vi-VN")}
                        </div>
                      </span>
                      <span
                        className="hg-num-mono"
                        style={{
                          fontWeight: 600,
                          color: t.amount >= 0 ? "#0f7a52" : "#b01c2e",
                        }}
                      >
                        {t.amount >= 0 ? "+" : ""}
                        {Number(t.amount).toLocaleString("vi-VN")}đ
                      </span>
                    </div>
                  ))
                )}
              </>
            ) : (
              <div className="hg-empty">Đang tải...</div>
            )}
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Lịch thanh toán</div>
            {installments && (
              <>
                {Number(installments.outstanding_debt) > 0 && (
                  <Note tone={installments.is_blocked ? "danger" : "warn"}>
                    Còn nợ:{" "}
                    <strong className="hg-num-mono">
                      {Number(installments.outstanding_debt).toLocaleString("vi-VN")}đ
                    </strong>
                    {installments.block_warning && (
                      <div style={{ marginTop: "6px" }}>{installments.block_warning}</div>
                    )}
                  </Note>
                )}
                {installments.installments.length === 0 ? (
                  <div className="hg-empty">Không có kỳ thanh toán nào.</div>
                ) : (
                  installments.installments.map((i: Installment) => (
                    <div key={i.id} className="hg-kv">
                      <span>
                        <strong>Kỳ {i.sequence}</strong>
                        <div className="hg-exercise-muscle">Hạn: {i.due_date}</div>
                      </span>
                      <span style={{ textAlign: "right" }}>
                        <span className="hg-num-mono" style={{ fontWeight: 600 }}>
                          {Number(i.amount).toLocaleString("vi-VN")}đ
                        </span>
                        <div>
                          <Chip
                            tone={
                              i.status === "paid"
                                ? "ok"
                                : i.status === "overdue"
                                ? "danger"
                                : "warn"
                            }
                          >
                            {i.status === "paid"
                              ? "ĐÃ THANH TOÁN"
                              : i.status === "overdue"
                              ? `QUÁ HẠN ${i.days_overdue} NGÀY`
                              : i.status === "partial"
                              ? "THANH TOÁN MỘT PHẦN"
                              : "CHƯA THANH TOÁN"}
                          </Chip>
                        </div>
                      </span>
                    </div>
                  ))
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* ================= GÓI PT ================= */}
      {tab === "pt" && (
        <div>
          {ptPackages.length === 0 ? (
            <div className="hg-empty">
              <h3>Chưa có gói tập PT</h3>
              <p>
                Gói PT tính theo số buổi. Liên hệ lễ tân hoặc xem danh mục gói PT để đăng ký tập
                1-1 với Huấn luyện viên.
              </p>
            </div>
          ) : (
            ptPackages.map((p) => (
              <div key={p.id} className="hg-chart-card">
                <div className="hg-chart-title">
                  <span>{p.package_name}</span>
                  <Chip tone={p.status === "active" ? "ok" : "warn"}>{p.status}</Chip>
                </div>
                {p.warning && <Note tone="warn">{p.warning}</Note>}
                <div className="hg-metric-grid">
                  <Stat label="Tổng số buổi" value={p.sessions_total} />
                  <Stat label="Đã sử dụng" value={p.sessions_used} />
                  <Stat label="Còn lại" value={p.sessions_remaining} gold />
                  <Stat label="Hạn sử dụng" value={`${p.days_remaining} ngày`} />
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${p.usage_percent}%` }} />
                </div>
                <KV label="Huấn luyện viên">{p.trainer_name ?? "Chưa gán"}</KV>
                <KV label="Hiệu lực">{`${p.start_date} → ${p.expiry_date}`}</KV>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}