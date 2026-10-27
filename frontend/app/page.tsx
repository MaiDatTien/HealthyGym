"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchGymData, postGymData } from "@/lib/api";

/* ==========================================================================
   SNEAT DASHBOARD — Trang chủ Dashboard HealthyGym
   Tái hiện chính xác bố cục và thành phần từ Sneat Admin Template:
   - Row 1: Congratulations Welcome Banner + Profit Mini Stat + Sales Mini Stat
   - Row 2: Total Revenue Chart (dual-bar + radial gauge) + Payments / Transactions Mini Stats + Profile Report Sparkline
   - Row 3: Order Statistics (Donut chart) + Income/Expense Tabs + Recent Transactions
   - Row 4: Công cụ tính nhanh TDEE & Thể trạng AI
   ========================================================================== */

export default function SneatDashboardPage() {
  const [user, setUser] = useState<any>(null);
  const [reports, setReports] = useState<any>(null);
  const [incomeTab, setIncomeTab] = useState<"income" | "expenses" | "profit">("income");

  // Quick TDEE Calc
  const [calc, setCalc] = useState({
    gender: "male",
    age: "29",
    height_cm: "172",
    weight_kg: "75",
    body_fat_percentage: "",
    activity_level: "moderate",
    goal: "cutting",
  });
  const [calcResult, setCalcResult] = useState<any>(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [calcError, setCalcError] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("hg_user");
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch {
        setUser(null);
      }
    }
    fetchGymData("/admin/reports").then(setReports).catch(() => {});
  }, []);

  const runQuickCalc = async (e: React.FormEvent) => {
    e.preventDefault();
    setCalcError("");
    setCalcLoading(true);
    try {
      const res = await postGymData("/ai/quick-calc", {
        gender: calc.gender,
        age: calc.age ? Number(calc.age) : null,
        height_cm: Number(calc.height_cm),
        weight_kg: Number(calc.weight_kg),
        body_fat_percentage: calc.body_fat_percentage ? Number(calc.body_fat_percentage) : null,
        activity_level: calc.activity_level,
        goal: calc.goal,
      });
      setCalcResult(res);
    } catch (err: any) {
      setCalcError(err.message);
      setCalcResult(null);
    } finally {
      setCalcLoading(false);
    }
  };

  const userName = user?.full_name || "Hội Viên";
  const revenueTotal = reports?.revenue_total ? (reports.revenue_total / 1000000).toFixed(1) : "126.8";
  const activeMembers = reports?.active_members || 4679;

  // Dữ liệu biểu đồ cột so sánh tháng (Doanh thu & Lượt tập)
  const barMonths = [
    { m: "Tháng 1", y26: 28, y25: 18 },
    { m: "Tháng 2", y26: 35, y25: 22 },
    { m: "Tháng 3", y26: 42, y25: 30 },
    { m: "Tháng 4", y26: 68, y25: 45 },
    { m: "Tháng 5", y26: 54, y25: 38 },
    { m: "Tháng 6", y26: 62, y25: 41 },
    { m: "Tháng 7", y26: 75, y25: 50 },
  ];

  return (
    <div>
      {/* ================= ROW 1 ================= */}
      <div className="sneat-grid-12">
        {/* Card 1: Congratulations John! (8 cols) */}
        <div className="col-8">
          <div className="card sneat-welcome-card" style={{ height: "100%", padding: "28px" }}>
            <div className="sneat-welcome-content">
              <div className="sneat-welcome-title">
                Chúc mừng {userName}! 🎉
              </div>
              <p className="sneat-welcome-desc">
                Hôm nay hệ thống ghi nhận <strong>78%</strong> học viên hoàn thành mục tiêu tập luyện.
                Phác đồ AI Smart Coach và các chỉ số thể trạng của bạn đang tiến triển rất tốt!
              </p>
              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                <Link href="/ai-coach" className="hg-btn-primary">
                  🧬 Khám Phá AI Coach
                </Link>
                <Link href="/pt-booking" className="hg-btn-ghost">
                  🏋️ Đặt Lịch PT 1-1
                </Link>
              </div>
            </div>

            {/* Sneat illustration SVG */}
            <div className="sneat-welcome-art">
              <svg width="160" height="130" viewBox="0 0 160 130" fill="none">
                <circle cx="80" cy="65" r="55" fill="#e7e7ff" opacity="0.6" />
                {/* Character body */}
                <rect x="55" y="55" width="50" height="60" rx="10" fill="#696cff" />
                {/* Head */}
                <circle cx="80" cy="38" r="18" fill="#ffab00" opacity="0.3" />
                <circle cx="80" cy="36" r="16" fill="#ffd1a4" />
                {/* Hair */}
                <path d="M66 32 C 68 20, 92 20, 94 32 C 90 24, 70 24, 66 32 Z" fill="#435971" />
                {/* Glasses / eyes */}
                <circle cx="75" cy="36" r="2.5" fill="#435971" />
                <circle cx="85" cy="36" r="2.5" fill="#435971" />
                <path d="M76 43 Q 80 47 84 43" stroke="#435971" strokeWidth="1.5" strokeLinecap="round" />
                {/* Laptop */}
                <polygon points="40,95 120,95 110,75 50,75" fill="#e7e7ff" />
                <rect x="48" y="70" width="64" height="24" rx="3" fill="#566a7f" />
                <rect x="52" y="73" width="56" height="18" rx="2" fill="#fff" />
                <rect x="58" y="77" width="20" height="3" rx="1" fill="#696cff" />
                <rect x="58" y="82" width="35" height="3" rx="1" fill="#71dd37" />
                <rect x="36" y="95" width="88" height="4" rx="2" fill="#cbd4db" />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 2: Profit Mini Stat (2 cols) */}
        <div className="col-2" style={{ gridColumn: "span 2" }}>
          <div className="card sneat-mini-stat" style={{ height: "100%" }}>
            <div className="sneat-stat-top">
              <div className="sneat-icon-badge success">📈</div>
              <span className="badge badge-success">▲ +72.8%</span>
            </div>
            <div>
              <div className="sneat-mini-stat-label">Lợi Nhuận / Doanh Thu</div>
              <div className="sneat-mini-stat-value">{revenueTotal}M <small style={{ fontSize: "14px", color: "var(--muted-color)" }}>đ</small></div>
            </div>
          </div>
        </div>

        {/* Card 3: Sales Mini Stat (2 cols) */}
        <div className="col-2" style={{ gridColumn: "span 2" }}>
          <div className="card sneat-mini-stat" style={{ height: "100%" }}>
            <div className="sneat-stat-top">
              <div className="sneat-icon-badge info">👥</div>
              <span className="badge badge-info">▲ +28.4%</span>
            </div>
            <div>
              <div className="sneat-mini-stat-label">Hội Viên Hoạt Động</div>
              <div className="sneat-mini-stat-value">{activeMembers.toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>

      {/* ================= ROW 2 ================= */}
      <div className="sneat-grid-12">
        {/* Card 4: Total Revenue (8 cols) */}
        <div className="col-8">
          <div className="card" style={{ height: "100%" }}>
            <div className="hg-chart-title">
              <div>
                <span>Doanh Thu &amp; Hoạt Động Phòng Gym</span>
                <div className="sneat-card-sub" style={{ marginTop: "4px" }}>
                  So sánh tiến độ năm 2026 và năm 2025
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span className="badge badge-primary">NĂM 2026</span>
                <span style={{ fontSize: "12px", color: "var(--muted-color)" }}>⋮</span>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: "24px", marginTop: "12px" }}>
              {/* Dual Bar Chart */}
              <div>
                <div style={{ display: "flex", gap: "14px", marginBottom: "16px", fontSize: "12.5px" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#696cff", display: "inline-block" }} />
                    <span style={{ color: "var(--heading-color)", fontWeight: 500 }}>2026 (Hiện tại)</span>
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#03c3ec", display: "inline-block" }} />
                    <span style={{ color: "var(--heading-color)", fontWeight: 500 }}>2025 (Năm trước)</span>
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "flex-end", height: "180px", gap: "12px", borderBottom: "1px solid var(--border-light)", paddingBottom: "6px" }}>
                  {barMonths.map((bm, idx) => (
                    <div key={idx} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", height: "100%", justifyContent: "flex-end", gap: "4px" }}>
                      <div style={{ display: "flex", alignItems: "flex-end", gap: "3px", height: "100%", width: "100%", justifyContent: "center" }}>
                        <div
                          title={`2026: ${bm.y26}M đ`}
                          style={{
                            width: "40%",
                            height: `${(bm.y26 / 80) * 100}%`,
                            background: "#696cff",
                            borderRadius: "4px 4px 0 0",
                            transition: "height 0.4s ease",
                          }}
                        />
                        <div
                          title={`2025: ${bm.y25}M đ`}
                          style={{
                            width: "40%",
                            height: `${(bm.y25 / 80) * 100}%`,
                            background: "#03c3ec",
                            borderRadius: "4px 4px 0 0",
                            transition: "height 0.4s ease",
                          }}
                        />
                      </div>
                      <span style={{ fontSize: "11px", color: "var(--muted-color)", marginTop: "4px" }}>
                        {bm.m.replace("Tháng ", "T")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Radial Growth Gauge & Mini Stats */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", borderLeft: "1px solid var(--border-light)", paddingLeft: "20px" }}>
                <div style={{ position: "relative", width: "120px", height: "120px" }}>
                  <svg width="120" height="120" viewBox="0 0 120 120" style={{ transform: "rotate(-90deg)" }}>
                    <circle cx="60" cy="60" r="50" fill="none" stroke="#f5f5f9" strokeWidth="10" />
                    <circle
                      cx="60"
                      cy="60"
                      r="50"
                      fill="none"
                      stroke="#696cff"
                      strokeWidth="10"
                      strokeDasharray="314"
                      strokeDashoffset="69"
                      strokeLinecap="round"
                    />
                  </svg>
                  <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                    <strong style={{ fontSize: "22px", fontWeight: 700, color: "var(--heading-color)" }}>78%</strong>
                    <span style={{ fontSize: "10px", color: "var(--muted-color)", fontWeight: 600 }}>TĂNG TRƯỞNG</span>
                  </div>
                </div>

                <div style={{ textAlign: "center", marginTop: "12px", fontSize: "13px", fontWeight: 600, color: "var(--heading-color)" }}>
                  62% Mục tiêu doanh số hoàn thành
                </div>

                <div style={{ display: "flex", gap: "16px", marginTop: "16px", width: "100%", justifyContent: "space-around" }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "11px", color: "var(--muted-color)" }}>2026 Hiện tại</div>
                    <div style={{ fontSize: "14px", fontWeight: 700, color: "#696cff" }}>32.5M đ</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "11px", color: "var(--muted-color)" }}>2025 Năm trước</div>
                    <div style={{ fontSize: "14px", fontWeight: 700, color: "#03c3ec" }}>41.2M đ</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Column right: Payments & Transactions Mini Stats + Profile Report (4 cols) */}
        <div className="col-4" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Mini row with 2 small cards */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
            {/* Payments */}
            <div className="card sneat-mini-stat" style={{ padding: "18px", margin: 0 }}>
              <div className="sneat-stat-top">
                <div className="sneat-icon-badge warning" style={{ width: "36px", height: "36px", fontSize: "16px" }}>💳</div>
                <span className="badge badge-warning" style={{ fontSize: "10px" }}>▼ -14.8%</span>
              </div>
              <div>
                <div className="sneat-mini-stat-label">Chi Phí Vận Hành</div>
                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--heading-color)" }}>24.6M đ</div>
              </div>
            </div>

            {/* Transactions */}
            <div className="card sneat-mini-stat" style={{ padding: "18px", margin: 0 }}>
              <div className="sneat-stat-top">
                <div className="sneat-icon-badge primary" style={{ width: "36px", height: "36px", fontSize: "16px" }}>🎫</div>
                <span className="badge badge-primary" style={{ fontSize: "10px" }}>▲ +28.1%</span>
              </div>
              <div>
                <div className="sneat-mini-stat-label">Lượt Check-in</div>
                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--heading-color)" }}>14,857</div>
              </div>
            </div>
          </div>

          {/* Profile Report Sparkline Card */}
          <div className="card" style={{ flex: 1, margin: 0, padding: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--heading-color)" }}>
                  Báo Cáo Thể Trạng (InBody)
                </div>
                <span className="badge badge-warning" style={{ marginTop: "6px" }}>NĂM 2026</span>
              </div>
              <div style={{ textAlign: "right" }}>
                <span style={{ fontSize: "12px", color: "var(--success)", fontWeight: 600 }}>▲ +68.2%</span>
                <div style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--heading-color)", marginTop: "2px" }}>
                  68.5 <small style={{ fontSize: "13px" }}>kg</small>
                </div>
              </div>
            </div>

            {/* Smooth Orange Sparkline Wave */}
            <div style={{ marginTop: "14px" }}>
              <svg width="100%" height="60" viewBox="0 0 300 60" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ffab00" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="#ffab00" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <path
                  d="M0,45 Q 40,10 80,35 T 160,20 T 240,40 T 300,15 L 300,60 L 0,60 Z"
                  fill="url(#sparkGrad)"
                />
                <path
                  d="M0,45 Q 40,10 80,35 T 160,20 T 240,40 T 300,15"
                  fill="none"
                  stroke="#ffab00"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--muted-color)", marginTop: "4px" }}>
              <span>Tháng 1</span>
              <span>Tháng 3</span>
              <span>Tháng 5</span>
              <span>Hiện tại</span>
            </div>
          </div>
        </div>
      </div>

      {/* ================= ROW 3 ================= */}
      <div className="sneat-grid-12">
        {/* Card 8: Order Statistics / Donut (4 cols) */}
        <div className="col-4">
          <div className="card" style={{ height: "100%" }}>
            <div className="hg-chart-title">
              <div>
                <span>Phân Bổ Dịch Vụ &amp; Lớp Học</span>
                <div className="sneat-card-sub" style={{ marginTop: "4px" }}>
                  42.82k Lượt tham gia tổng
                </div>
              </div>
              <span style={{ color: "var(--muted-color)", fontSize: "12px" }}>⋮</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", margin: "16px 0" }}>
              <div>
                <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "var(--heading-color)" }}>
                  8,258
                </div>
                <div style={{ fontSize: "12.5px", color: "var(--muted-color)" }}>Tổng lượt tháng này</div>
              </div>

              {/* Donut Chart SVG */}
              <div style={{ position: "relative", width: "95px", height: "95px" }}>
                <svg width="95" height="95" viewBox="0 0 95 95" style={{ transform: "rotate(-90deg)" }}>
                  <circle cx="47.5" cy="47.5" r="38" fill="none" stroke="#696cff" strokeWidth="12" strokeDasharray="238" strokeDashoffset="100" />
                  <circle cx="47.5" cy="47.5" r="38" fill="none" stroke="#71dd37" strokeWidth="12" strokeDasharray="238" strokeDashoffset="170" />
                  <circle cx="47.5" cy="47.5" r="38" fill="none" stroke="#03c3ec" strokeWidth="12" strokeDasharray="238" strokeDashoffset="210" />
                  <circle cx="47.5" cy="47.5" r="38" fill="none" stroke="#ffab00" strokeWidth="12" strokeDasharray="238" strokeDashoffset="230" />
                </svg>
                <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                  <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--heading-color)" }}>38%</span>
                  <span style={{ fontSize: "8.5px", color: "var(--muted-color)", fontWeight: 600 }}>TUẦN NÀY</span>
                </div>
              </div>
            </div>

            {/* List Breakdown */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {[
                { icon: "🏋️", name: "Gym & Kháng Lực", sub: "Tạ tự do & máy khối", val: "3,716", pct: "45%", color: "primary" },
                { icon: "🧘", name: "Lớp Yoga & Pilates", sub: "GroupX Studio A", val: "2,312", pct: "28%", color: "success" },
                { icon: "🏃", name: "Cardio & HIIT", sub: "Máy chạy & máy trượt tuyết", val: "1,486", pct: "18%", color: "info" },
                { icon: "🥊", name: "PT Kèm 1-1", sub: "Huấn luyện cá nhân hóa", val: "744", pct: "9%", color: "warning" },
              ].map((item, idx) => (
                <div key={idx} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div className={`sneat-icon-badge ${item.color}`} style={{ width: "34px", height: "34px", fontSize: "15px" }}>
                      {item.icon}
                    </div>
                    <div>
                      <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--heading-color)" }}>{item.name}</div>
                      <div style={{ fontSize: "11px", color: "var(--muted-color)" }}>{item.sub}</div>
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--heading-color)" }}>{item.val}</div>
                    <div style={{ fontSize: "11px", color: "var(--muted-color)" }}>{item.pct}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Card 9: Income / Expenses / Profit Tabs (4 cols) */}
        <div className="col-4">
          <div className="card" style={{ height: "100%" }}>
            <div style={{ display: "flex", gap: "6px", marginBottom: "16px", background: "#f5f5f9", padding: "4px", borderRadius: "6px" }}>
              <button
                className={`hg-btn-ghost hg-btn-sm ${incomeTab === "income" ? "active" : ""}`}
                style={{
                  flex: 1,
                  background: incomeTab === "income" ? "#696cff" : "transparent",
                  color: incomeTab === "income" ? "#fff" : "var(--body-color)",
                  border: "none",
                  boxShadow: incomeTab === "income" ? "0 2px 4px rgba(105,108,255,0.4)" : "none",
                }}
                onClick={() => setIncomeTab("income")}
              >
                DOANH THU
              </button>
              <button
                className={`hg-btn-ghost hg-btn-sm ${incomeTab === "expenses" ? "active" : ""}`}
                style={{
                  flex: 1,
                  background: incomeTab === "expenses" ? "#696cff" : "transparent",
                  color: incomeTab === "expenses" ? "#fff" : "var(--body-color)",
                  border: "none",
                  boxShadow: incomeTab === "expenses" ? "0 2px 4px rgba(105,108,255,0.4)" : "none",
                }}
                onClick={() => setIncomeTab("expenses")}
              >
                CHI PHÍ
              </button>
              <button
                className={`hg-btn-ghost hg-btn-sm ${incomeTab === "profit" ? "active" : ""}`}
                style={{
                  flex: 1,
                  background: incomeTab === "profit" ? "#696cff" : "transparent",
                  color: incomeTab === "profit" ? "#fff" : "var(--body-color)",
                  border: "none",
                  boxShadow: incomeTab === "profit" ? "0 2px 4px rgba(105,108,255,0.4)" : "none",
                }}
                onClick={() => setIncomeTab("profit")}
              >
                LỢI NHUẬN
              </button>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "12px", margin: "16px 0" }}>
              <div className="sneat-icon-badge primary" style={{ width: "42px", height: "42px" }}>
                💰
              </div>
              <div>
                <div style={{ fontSize: "12px", color: "var(--muted-color)" }}>
                  {incomeTab === "income" ? "Tổng Doanh Thu Năm" : incomeTab === "expenses" ? "Tổng Chi Phí Năm" : "Lợi Nhuận Ròng"}
                </div>
                <div style={{ fontSize: "1.45rem", fontWeight: 700, color: "var(--heading-color)" }}>
                  {incomeTab === "income" ? "459.1M đ" : incomeTab === "expenses" ? "142.5M đ" : "316.6M đ"}{" "}
                  <span style={{ fontSize: "12px", color: "var(--success)" }}>▲ +65%</span>
                </div>
              </div>
            </div>

            {/* Mini Bar Chart */}
            <div style={{ display: "flex", alignItems: "flex-end", height: "120px", gap: "8px", margin: "20px 0 16px" }}>
              {[35, 45, 60, 50, 75, 90, 80].map((v, i) => (
                <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", justifyContent: "flex-end" }}>
                  <div
                    style={{
                      height: `${v}%`,
                      background: i === 5 ? "#696cff" : "#e7e7ff",
                      borderRadius: "4px",
                      transition: "all 0.3s",
                    }}
                  />
                  <span style={{ fontSize: "10px", color: "var(--muted-color)", textAlign: "center", marginTop: "4px" }}>
                    T{i + 1}
                  </span>
                </div>
              ))}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid var(--border-light)", paddingTop: "12px", fontSize: "13px" }}>
              <span style={{ color: "var(--body-color)" }}>Gói hội viên 12T:</span>
              <strong style={{ color: "var(--heading-color)" }}>285.5M đ</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "8px", fontSize: "13px" }}>
              <span style={{ color: "var(--body-color)" }}>Huấn luyện viên PT:</span>
              <strong style={{ color: "var(--heading-color)" }}>114.2M đ</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "8px", fontSize: "13px" }}>
              <span style={{ color: "var(--body-color)" }}>Quầy Pro-Shop &amp; Nước:</span>
              <strong style={{ color: "var(--heading-color)" }}>59.4M đ</strong>
            </div>
          </div>
        </div>

        {/* Card 10: Recent Transactions (4 cols) */}
        <div className="col-4">
          <div className="card" style={{ height: "100%" }}>
            <div className="hg-chart-title">
              <div>
                <span>Hoạt Động &amp; Giao Dịch Gần Đây</span>
                <div className="sneat-card-sub" style={{ marginTop: "4px" }}>
                  Dòng tiền &amp; điểm danh mới nhất
                </div>
              </div>
              <span style={{ color: "var(--muted-color)", fontSize: "12px" }}>⋮</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "12px" }}>
              {[
                { icon: "💳", title: "Thẻ Hội Viên VIP 12T", sub: "Chuyển khoản VietQR", amount: "+12.500.000đ", positive: true, tone: "success" },
                { icon: "🥤", title: "Whey Isolate Pro-Shop", sub: "Thanh toán ví hội viên", amount: "+1.850.000đ", positive: true, tone: "info" },
                { icon: "🏋️", title: "Gia Hạn Gói PT 36 Buổi", sub: "Thẻ ngân hàng POS", amount: "+6.200.000đ", positive: true, tone: "primary" },
                { icon: "🎁", title: "Tập Thử 7 Ngày Miễn Phí", sub: "Xác thực OTP Web", amount: "0đ (Miễn phí)", positive: false, tone: "warning" },
                { icon: "🚪", title: "Check-in Cổng QR #1048", sub: "Thẻ đang hoạt động", amount: "+10 Điểm", positive: true, tone: "success" },
              ].map((tx, idx) => (
                <div key={idx} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div className={`sneat-icon-badge ${tx.tone}`} style={{ width: "38px", height: "38px", fontSize: "16px" }}>
                      {tx.icon}
                    </div>
                    <div>
                      <div style={{ fontSize: "13.5px", fontWeight: 600, color: "var(--heading-color)" }}>{tx.title}</div>
                      <div style={{ fontSize: "11.5px", color: "var(--muted-color)" }}>{tx.sub}</div>
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span style={{ fontSize: "13.5px", fontWeight: 700, color: tx.positive ? "var(--success)" : "var(--body-color)" }}>
                      {tx.amount}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ================= ROW 4: CÔNG CỤ TÍNH NHANH TDEE & THỂ TRẠNG ================= */}
      <div className="card" style={{ marginTop: "8px" }}>
        <div className="hg-chart-title">
          <div>
            <span>🧬 Công Cụ Tính Nhanh Chỉ Số Thể Trạng (TDEE &amp; Body Fat AI)</span>
            <div className="sneat-card-sub" style={{ marginTop: "4px" }}>
              Tính toán tức thì chỉ số BMR theo Katch-McArdle, TDEE và lộ trình tăng cơ giảm mỡ chuẩn khoa học
            </div>
          </div>
          <Link href="/ai-coach" className="hg-btn-primary hg-btn-sm">
            Xem Phác Đồ Toàn Diện 3 Trụ Cột →
          </Link>
        </div>

        <form onSubmit={runQuickCalc}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginTop: "14px" }}>
            <div>
              <label>Giới tính</label>
              <select
                className="input-box"
                value={calc.gender}
                onChange={(e) => setCalc({ ...calc, gender: e.target.value })}
              >
                <option value="male">Nam</option>
                <option value="female">Nữ</option>
              </select>
            </div>
            <div>
              <label>Chiều cao (cm)</label>
              <input
                className="input-box"
                type="number"
                value={calc.height_cm}
                onChange={(e) => setCalc({ ...calc, height_cm: e.target.value })}
                required
              />
            </div>
            <div>
              <label>Cân nặng (kg)</label>
              <input
                className="input-box"
                type="number"
                value={calc.weight_kg}
                onChange={(e) => setCalc({ ...calc, weight_kg: e.target.value })}
                required
              />
            </div>
            <div>
              <label>Body Fat % (nếu biết)</label>
              <input
                className="input-box"
                type="number"
                placeholder="VD: 20"
                value={calc.body_fat_percentage}
                onChange={(e) => setCalc({ ...calc, body_fat_percentage: e.target.value })}
              />
            </div>
            <div>
              <label>Tuổi</label>
              <input
                className="input-box"
                type="number"
                value={calc.age}
                onChange={(e) => setCalc({ ...calc, age: e.target.value })}
              />
            </div>
            <div>
              <label>Mục tiêu</label>
              <select
                className="input-box"
                value={calc.goal}
                onChange={(e) => setCalc({ ...calc, goal: e.target.value })}
              >
                <option value="cutting">Giảm mỡ (Cutting)</option>
                <option value="bulking">Tăng cơ (Bulking)</option>
                <option value="recomp">Tái cấu trúc (Recomp)</option>
                <option value="maintenance">Duy trì thể lực</option>
              </select>
            </div>
          </div>

          <div style={{ display: "flex", gap: "12px", alignItems: "center", marginTop: "6px" }}>
            <button type="submit" className="hg-btn-primary" disabled={calcLoading}>
              {calcLoading && <span className="hg-spinner" />}
              ⚡ Tính Nhanh Chỉ Số Của Tôi
            </button>
            <Link href="/chat" className="hg-btn-ghost">
              💬 Trò chuyện với Trợ lý AI
            </Link>
          </div>
        </form>

        {calcError && (
          <div className="sneat-alert alert-danger" style={{ marginTop: "16px" }}>
            {calcError}
          </div>
        )}

        {calcResult && (
          <div style={{ marginTop: "24px", paddingTop: "20px", borderTop: "1px solid var(--border-light)" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
              <div className="sneat-stat-item primary">
                <div className="sneat-stat-label">Chỉ Số BMI</div>
                <div className="sneat-stat-val">{calcResult.bmi}</div>
                <div style={{ fontSize: "12px", color: "var(--muted-color)", marginTop: "4px" }}>
                  {calcResult.bmi_category || "Bình thường"}
                </div>
              </div>

              <div className="sneat-stat-item primary">
                <div className="sneat-stat-label">Tỷ Lệ Body Fat</div>
                <div className="sneat-stat-val">{calcResult.body_fat_percentage}%</div>
                <div style={{ fontSize: "12px", color: "var(--muted-color)", marginTop: "4px" }}>
                  {calcResult.body_fat_category || "Chuẩn"}
                </div>
              </div>

              <div className="sneat-stat-item">
                <div className="sneat-stat-label">Khối Cơ Nạc (LBM)</div>
                <div className="sneat-stat-val">{calcResult.lean_body_mass_kg} <small style={{ fontSize: "14px" }}>kg</small></div>
                <div style={{ fontSize: "12px", color: "var(--muted-color)", marginTop: "4px" }}>
                  Khối mỡ: {calcResult.fat_mass_kg} kg
                </div>
              </div>

              <div className="sneat-stat-item">
                <div className="sneat-stat-label">BMR Katch-McArdle</div>
                <div className="sneat-stat-val">{calcResult.bmr_kcal} <small style={{ fontSize: "14px" }}>kcal</small></div>
                <div style={{ fontSize: "12px", color: "var(--muted-color)", marginTop: "4px" }}>
                  Tiêu hao tối thiểu/ngày
                </div>
              </div>

              <div className="sneat-stat-item primary">
                <div className="sneat-stat-label">TDEE Năng Lượng/Ngày</div>
                <div className="sneat-stat-val" style={{ color: "#696cff" }}>{calcResult.tdee_kcal} <small style={{ fontSize: "14px" }}>kcal</small></div>
                <div style={{ fontSize: "12px", color: "var(--muted-color)", marginTop: "4px" }}>
                  Calo duy trì thể trạng
                </div>
              </div>
            </div>

            {calcResult.timeline && (
              <div className="sneat-alert alert-primary" style={{ marginTop: "16px" }}>
                <strong>Lộ trình dự kiến từ AI:</strong> Cần khoảng <strong>{calcResult.timeline.estimated_weeks} tuần</strong> (~{calcResult.timeline.estimated_months} tháng) để đạt thể trạng mục tiêu an toàn.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
