"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default function ProfilePage() {
  const [user, setUser] = useState<any>(null);
  const [bookings, setBookings] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [freezeDays, setFreezeDays] = useState(14);
  const [msg, setMsg] = useState("");

  const loadProfile = () => {
    fetchGymData("/auth/me").then(setUser).catch(() => {});
    fetchGymData("/interactions/bookings/my").then(setBookings).catch(() => {});
    fetchGymData("/interactions/orders/my").then(setOrders).catch(() => {});
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleFreeze = async () => {
    try {
      const res = await postGymData("/interactions/freeze", { days: freezeDays });
      setMsg(res.message);
      loadProfile();
    } catch (err: any) {
      setMsg(err.message);
    }
  };

  const handleUnfreeze = async () => {
    try {
      const res = await postGymData("/interactions/unfreeze");
      setMsg(res.message);
      loadProfile();
    } catch (err: any) {
      setMsg(err.message);
    }
  };

  const handleCancelBooking = async (id: number) => {
    try {
      const res = await postGymData(`/interactions/bookings/${id}/cancel`);
      setMsg(res.message);
      loadProfile();
    } catch (err: any) {
      setMsg(err.message);
    }
  };

  if (!user) {
    return (
      <div className="card" style={{ maxWidth: "480px", margin: "2rem auto", textAlign: "center" }}>
        <h3>Vui lòng đăng nhập để xem Thẻ Hội Viên</h3>
        <a href="/login" className="hg-btn-emerald" style={{ marginTop: "1rem" }}>
          Đi tới trang Đăng nhập
        </a>
      </div>
    );
  }

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">HỒ SƠ CÁ NHÂN</span>
          <h1 style={{ marginTop: "0.4rem" }}>Xin chào, {user.full_name}</h1>
          <p style={{ color: "#64748b" }}>
            Gói hiện tại: <strong>{user.plan_name}</strong> • Trạng thái:{" "}
            <strong style={{ color: "#0e6d8c" }}>{user.member_status?.toUpperCase()}</strong> • Hạn thẻ:{" "}
            <strong>{user.expire_date || "Chưa kích hoạt"}</strong>
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
          {user.member_status === "frozen" ? (
            <button className="hg-btn-coral" onClick={handleUnfreeze}>
              🔥 Mở Khóa Thẻ Tập Ngay
            </button>
          ) : (
            <>
              <input
                type="number"
                min={1}
                max={60}
                className="input-box"
                style={{ width: "85px", marginBottom: 0 }}
                value={freezeDays}
                onChange={(e) => setFreezeDays(Number(e.target.value))}
              />
              <button className="hg-btn-ghost" onClick={handleFreeze}>
                ❄️ Bảo lưu thẻ ({freezeDays} ngày)
              </button>
            </>
          )}
        </div>
      </div>

      {msg && (
        <div
          style={{
            background: "#0e6d8c",
            color: "#fff",
            padding: "1rem 1.4rem",
            borderRadius: "14px",
            marginBottom: "1.5rem",
            fontWeight: 700,
          }}
        >
          {msg}
        </div>
      )}

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="table-wrap">
          <h3 style={{ marginBottom: "1rem" }}>📅 Lịch Lớp Đã Đặt ({bookings.length})</h3>
          <table>
            <thead>
              <tr>
                <th>Lớp học</th>
                <th>Thời gian</th>
                <th>Trạng thái</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {bookings.map((b) => (
                <tr key={b.id}>
                  <td><strong>{b.class_name}</strong></td>
                  <td>{b.schedule_time}</td>
                  <td><span className="chip">{b.status}</span></td>
                  <td>
                    {b.status === "confirmed" && (
                      <button className="hg-btn-ghost" onClick={() => handleCancelBooking(b.id)}>
                        Hủy
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="table-wrap">
          <h3 style={{ marginBottom: "1rem" }}>🧾 Hóa Đơn Gói Tập ({orders.length})</h3>
          <table>
            <thead>
              <tr>
                <th>Gói đăng ký</th>
                <th>Đã giảm</th>
                <th>Thực thu</th>
                <th>Thanh toán</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td><strong>{o.plan_name}</strong></td>
                  <td>{formatCurrency(o.discount_amount || 0)}</td>
                  <td style={{ color: "#0e6d8c", fontWeight: 800 }}>{formatCurrency(o.total_amount)}</td>
                  <td>{o.payment_method}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
