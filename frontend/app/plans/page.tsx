"use client";
import React, { useEffect, useState } from "react";
import ListingCard from "@/components/ListingCard";
import { fetchGymData, postGymData } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default function PlansPage() {
  const [plans, setPlans] = useState<any[]>([]);
  const [checkoutPlan, setCheckoutPlan] = useState<any>(null);
  const [voucherCode, setVoucherCode] = useState("GIAM10");
  const [voucherPreview, setVoucherPreview] = useState<any>(null);
  const [paymentMethod, setPaymentMethod] = useState("Chuyển khoản QR");
  const [msg, setMsg] = useState<{ type: string; text: string } | null>(null);

  useEffect(() => {
    fetchGymData("/listings/plans").then(setPlans).catch(() => {});
  }, []);

  const handlePreviewVoucher = async () => {
    if (!checkoutPlan || !voucherCode.trim()) return;
    try {
      const res = await fetchGymData(
        `/interactions/vouchers/validate?code=${encodeURIComponent(voucherCode)}&plan_id=${checkoutPlan.id}`
      );
      setVoucherPreview(res);
    } catch (err: any) {
      setVoucherPreview(null);
      setMsg({ type: "err", text: err.message });
    }
  };

  const handleConfirmCheckout = async () => {
    if (!checkoutPlan) return;
    try {
      const res = await postGymData("/interactions/orders", {
        plan_id: checkoutPlan.id,
        voucher_code: voucherCode,
        payment_method: paymentMethod,
      });
      setMsg({ type: "ok", text: res.message });
      setCheckoutPlan(null);
      setVoucherPreview(null);
    } catch (err: any) {
      setMsg({ type: "err", text: err.message });
    }
  };

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">LINH HOẠT & MINH BẠCH</span>
          <h1 style={{ marginTop: "0.4rem" }}>Bảng Giá Gói Hội Viên HealthyGym</h1>
          <p style={{ color: "#64748b" }}>
            Nhập mã ưu đãi <strong>GIAM10</strong> (giảm 10%) hoặc <strong>HEALTHY20</strong> (giảm 20%) khi thanh toán.
          </p>
        </div>
      </div>

      {msg && (
        <div
          style={{
            background: msg.type === "ok" ? "#0e6d8c" : "#c02a3f",
            color: "#fff",
            padding: "1rem 1.4rem",
            borderRadius: "14px",
            marginBottom: "1.5rem",
            fontWeight: 700,
          }}
        >
          {msg.text}
        </div>
      )}

      <div className="grid">
        {plans.map((plan) => (
          <ListingCard
            key={plan.id}
            plan={plan}
            onSelectPlan={(p) => {
              setCheckoutPlan(p);
              setVoucherPreview(null);
            }}
          />
        ))}
      </div>

      {checkoutPlan && (
        <div className="modal-backdrop" onClick={() => setCheckoutPlan(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: "1.35rem", fontWeight: 800 }}>Đăng Ký: {checkoutPlan.name}</h3>
            <p style={{ color: "#64748b", marginBottom: "1rem" }}>
              Thời hạn cộng thêm vào thẻ: <strong>{checkoutPlan.duration_days} ngày</strong>
            </p>
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Mã giảm giá</label>
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.3rem" }}>
              <input
                className="input-box"
                value={voucherCode}
                onChange={(e) => setVoucherCode(e.target.value.toUpperCase())}
              />
              <button type="button" className="hg-btn-emerald" style={{ height: "44px" }} onClick={handlePreviewVoucher}>
                Áp dụng
              </button>
            </div>
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Phương thức thanh toán</label>
            <select className="input-box" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
              <option value="Chuyển khoản QR">Chuyển khoản ngân hàng (VietQR)</option>
              <option value="Thẻ quốc tế VISA/Mastercard">Thẻ JCB / VISA / Mastercard</option>
              <option value="Ví MoMo">Ví điện tử MoMo</option>
            </select>

            <div style={{ background: "#f8fafc", padding: "1rem", borderRadius: "14px", margin: "1rem 0" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Giá niêm yết:</span>
                <strong>{formatCurrency(checkoutPlan.price)}</strong>
              </div>
              {voucherPreview && (
                <div style={{ display: "flex", justifyContent: "space-between", color: "#0e6d8c" }}>
                  <span>Giảm giá ({voucherPreview.code}):</span>
                  <strong>- {formatCurrency(voucherPreview.discount_amount)}</strong>
                </div>
              )}
              <div className="divider" />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "1.2rem", fontWeight: 800 }}>
                <span>Thành tiền:</span>
                <span style={{ color: "#c02a3f" }}>
                  {formatCurrency(voucherPreview ? voucherPreview.final_price : checkoutPlan.price)}
                </span>
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button className="hg-btn-ghost" style={{ flex: 1 }} onClick={() => setCheckoutPlan(null)}>
                Đóng
              </button>
              <button className="hg-btn-emerald" style={{ flex: 2 }} onClick={handleConfirmCheckout}>
                Xác Nhận Thanh Toán
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
