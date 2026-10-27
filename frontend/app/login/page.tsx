"use client";
import React, { useState } from "react";
import { postGymData } from "@/lib/api";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  // MẶC ĐỊNH ĐIỀN SẴN TÀI KHOẢN ADMIN GỐC: tk: admin / mk: 123
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("123");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const payload =
        mode === "login"
          ? { username, password }
          : { username, password, full_name: fullName, email, phone };
      const data = await postGymData(endpoint, payload);
      localStorage.setItem("hg_token", data.access_token);
      localStorage.setItem("hg_user", JSON.stringify(data.user));
      // Điều hướng theo vai trò: HLV vào Coach Dashboard, Nhân viên/Admin vào Quản trị
      const role = data.user?.role;
      if (role === "trainer") window.location.href = "/coach";
      else if (role === "admin" || role === "staff") window.location.href = "/admin";
      else window.location.href = "/progress";
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div style={{ maxWidth: "460px", margin: "2.5rem auto" }} className="card">
      <h2 style={{ color: "#0a3d55", textAlign: "center", fontWeight: 900, marginBottom: "1rem" }}>
        CHÀO MỪNG ĐẾN VỚI HEALTHYGYM
      </h2>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.2rem" }}>
        <button
          type="button"
          className={mode === "login" ? "btn-cyan" : "btn-outline-sm"}
          style={{ flex: 1 }}
          onClick={() => setMode("login")}
        >
          Đăng Nhập
        </button>
        <button
          type="button"
          className={mode === "register" ? "btn-cyan" : "btn-outline-sm"}
          style={{ flex: 1 }}
          onClick={() => setMode("register")}
        >
          Đăng Ký Hội Viên
        </button>
      </div>

      {mode === "login" && (
        <div
          style={{
            fontSize: "0.85rem",
            background: "#f0f9ff",
            border: "1px solid #bae6fd",
            padding: "0.85rem",
            borderRadius: "12px",
            marginBottom: "1rem",
          }}
        >
          <div>🔑 <strong>Chọn nhanh tài khoản (Mật khẩu chung: <code>123</code>):</strong></div>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem", flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn-outline-sm"
              onClick={() => { setUsername("admin"); setPassword("123"); }}
            >
              👑 Admin gốc (admin / 123)
            </button>
            <button
              type="button"
              className="btn-outline-sm"
              onClick={() => { setUsername("staff"); setPassword("123"); }}
            >
              💼 Lễ tân (staff / 123)
            </button>
            <button
              type="button"
              className="btn-outline-sm"
              onClick={() => { setUsername("hoivien"); setPassword("123"); }}
            >
              🏃 Hội viên (hoivien / 123)
            </button>
            <button
              type="button"
              className="btn-outline-sm"
              onClick={() => { setUsername("hlv"); setPassword("123"); }}
            >
              🎓 Huấn luyện viên (hlv / 123)
            </button>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Tên tài khoản</label>
        <input className="input-box" value={username} onChange={(e) => setUsername(e.target.value)} required />

        {mode === "register" && (
          <>
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Họ và tên</label>
            <input className="input-box" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Số điện thoại</label>
            <input className="input-box" value={phone} onChange={(e) => setPhone(e.target.value)} required />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Email</label>
            <input type="email" className="input-box" value={email} onChange={(e) => setEmail(e.target.value)} />
          </>
        )}

        <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Mật khẩu</label>
        <input
          type="password"
          className="input-box"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button type="submit" className="btn-orange" style={{ width: "100%", padding: "0.85rem", marginTop: "0.5rem" }}>
          {mode === "login" ? "ĐĂNG NHẬP NGAY" : "ĐĂNG KÝ TÀI KHOẢN"}
        </button>
      </form>

      {error && <p style={{ color: "#c02a3f", marginTop: "1rem", fontWeight: 700 }}>⚠️ {error}</p>}
    </div>
  );
}
