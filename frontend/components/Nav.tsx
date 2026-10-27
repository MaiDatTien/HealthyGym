"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

/* ==========================================================================
   SNEAT SIDEBAR & TOP NAVBAR
   Thiết kế chuẩn Sneat Admin Template:
   - Sidebar trái cố định (260px) với các nhóm menu & icon
   - Top navbar nổi với ô tìm kiếm, trạng thái AI, chuyển đổi vai trò, avatar
   ========================================================================== */

interface NavItem {
  href: string;
  label: string;
  icon: string;
  badge?: string;
  badgeTone?: "primary" | "success" | "warning" | "danger";
}

interface NavSection {
  header: string;
  items: NavItem[];
}

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [aiStatus, setAiStatus] = useState<"checking" | "online" | "offline">("online");

  useEffect(() => {
    const saved = localStorage.getItem("hg_user");
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch {
        setUser(null);
      }
    } else {
      setUser(null);
    }

    // Kiểm tra kết nối AI backend
    fetch("http://127.0.0.1:8000/health", { method: "GET", cache: "no-store" })
      .then((r) => setAiStatus(r.ok ? "online" : "offline"))
      .catch(() => {
        fetch("http://localhost:8000/health", { method: "GET", cache: "no-store" })
          .then((r) => setAiStatus(r.ok ? "online" : "offline"))
          .catch(() => setAiStatus("offline"));
      });
  }, [pathname]);

  const handleLogout = () => {
    localStorage.removeItem("hg_token");
    localStorage.removeItem("hg_user");
    window.location.href = "/login";
  };

  const handleQuickRole = (role: string, name: string) => {
    const u = { username: role, role, full_name: name };
    localStorage.setItem("hg_user", JSON.stringify(u));
    setUser(u);
    window.location.reload();
  };

  const role = user?.role === "staff" ? "receptionist" : user?.role || "guest";

  // Danh mục menu phân theo nhóm chuẩn Sneat
  const sections: NavSection[] = [
    {
      header: "TỔNG QUAN",
      items: [
        { href: "/", label: "Dashboard", icon: "📊", badge: "HOT", badgeTone: "primary" },
        { href: "/chat", label: "Chat AI 24/7", icon: "💬" },
      ],
    },
    {
      header: "AI SMART FITNESS COACH",
      items: [
        { href: "/ai-coach", label: "AI Coach Phác Đồ", icon: "🧬" },
        { href: "/ai-plus", label: "AI Chuyên Sâu (PAR-Q)", icon: "🎯", badge: "PRO", badgeTone: "success" },
      ],
    },
    {
      header: "HỘI VIÊN & TẬP LUYỆN",
      items: [
        { href: "/plans", label: "Gói Tập & Giá", icon: "🏷️" },
        { href: "/groupx", label: "Lịch Lớp GroupX", icon: "🧘" },
        { href: "/pt-booking", label: "Đặt Lịch PT 1-1", icon: "🏋️" },
        { href: "/progress", label: "Tiến Độ Thể Trạng", icon: "📈" },
        { href: "/contract", label: "Hợp Đồng & Thẻ", icon: "📑" },
        { href: "/rewards", label: "Điểm Thưởng & Quà", icon: "🎁" },
      ],
    },
    {
      header: "VẬN HÀNH & KINH DOANH",
      items: [
        { href: "/front-desk", label: "Quầy Lễ Tân (Gate)", icon: "🚪" },
        { href: "/leads", label: "Khách Tập Thử CRM", icon: "👥" },
        { href: "/pos", label: "Bán Hàng POS", icon: "🛒" },
        { href: "/pt-ops", label: "Nghiệp Vụ HLV (PT)", icon: "⏱️" },
        { href: "/facility", label: "CSVC & Bảo Trì", icon: "🔧" },
        { href: "/equipment", label: "Quét QR Máy Tập", icon: "📱" },
        { href: "/coach", label: "Coach Dashboard", icon: "👨‍🏫" },
        { href: "/admin", label: "Quản Trị Hệ Thống", icon: "⚙️" },
      ],
    },
  ];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    const q = searchQuery.toLowerCase().trim();
    if (q.includes("chat") || q.includes("hỏi")) router.push("/chat");
    else if (q.includes("ai") || q.includes("phác đồ")) router.push("/ai-coach");
    else if (q.includes("parq") || q.includes("inbody")) router.push("/ai-plus");
    else if (q.includes("pt") || q.includes("huấn luyện")) router.push("/pt-booking");
    else if (q.includes("giá") || q.includes("gói")) router.push("/plans");
    else if (q.includes("lớp") || q.includes("group")) router.push("/groupx");
    else if (q.includes("pos") || q.includes("bán")) router.push("/pos");
    else if (q.includes("lễ tân") || q.includes("cổng")) router.push("/front-desk");
    else if (q.includes("leads") || q.includes("tập thử")) router.push("/leads");
    else router.push(`/?search=${encodeURIComponent(searchQuery)}`);
  };

  return (
    <>
      {/* ================= SIDEBAR TRÁI SNEAT ================= */}
      <aside className={`sneat-sidebar ${sidebarOpen ? "open" : ""}`}>
        <Link href="/" className="sneat-brand" onClick={() => setSidebarOpen(false)}>
          <div className="sneat-brand-icon">HG</div>
          <div className="sneat-brand-name">
            Healthy<strong>Gym</strong>
          </div>
        </Link>

        <div className="sneat-menu">
          {sections.map((sec, sidx) => (
            <div key={sidx}>
              <div className="sneat-menu-header">{sec.header}</div>
              {sec.items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`sneat-menu-item ${isActive ? "active" : ""}`}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <span className="sneat-menu-icon">{item.icon}</span>
                    <span style={{ flex: 1 }}>{item.label}</span>
                    {item.badge && (
                      <span
                        className={`badge ${
                          item.badgeTone === "success"
                            ? "badge-success"
                            : item.badgeTone === "warning"
                            ? "badge-warning"
                            : "badge-primary"
                        }`}
                        style={{ fontSize: "10px", padding: "2px 6px" }}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </div>
      </aside>

      {/* Backdrop cho mobile */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(67, 89, 113, 0.5)",
            zIndex: 1040,
          }}
        />
      )}

      {/* ================= TOP NAVBAR SNEAT ================= */}
      <div className="sneat-topbar-wrapper">
        <header className="sneat-topbar">
          <div style={{ display: "flex", alignItems: "center", gap: "12px", flex: 1 }}>
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="hg-btn-ghost hg-btn-sm"
              style={{ padding: "6px 10px", display: "inline-flex" }}
              aria-label="Toggle sidebar"
            >
              ☰
            </button>

            <form onSubmit={handleSearch} className="sneat-search">
              <span>🔍</span>
              <input
                type="text"
                placeholder="Tìm kiếm chức năng, gói tập, AI (Ctrl+K)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <span className="sneat-search-shortcut">⌘K</span>
            </form>
          </div>

          <div className="sneat-topbar-actions">
            {/* Trạng thái kết nối AI Backend */}
            <div
              className={`badge ${
                aiStatus === "online"
                  ? "badge-success"
                  : aiStatus === "offline"
                  ? "badge-danger"
                  : "badge-warning"
              }`}
              title={
                aiStatus === "online"
                  ? "Máy chủ AI Backend đang kết nối tốt (cổng 8000)"
                  : "Không kết nối được API Backend"
              }
            >
              {aiStatus === "online" ? "🟢 AI Trực Tuyến" : "🔴 AI Mất Kết Nối"}
            </div>

            {/* Quick role switch for convenience */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "12px", color: "var(--muted-color)", fontWeight: 500 }}>
                Vai trò:
              </span>
              <select
                value={role}
                onChange={(e) => {
                  const r = e.target.value;
                  const nameMap: Record<string, string> = {
                    member: "Nguyễn Văn Hội Viên",
                    trainer: "HLV Trần Quốc Tuấn",
                    receptionist: "Lê Thị Lễ Tân",
                    facility_manager: "Ngô Văn Kỹ Thuật",
                    admin: "Quản Trị Viên",
                    guest: "Khách Vãng Lai",
                  };
                  handleQuickRole(r, nameMap[r] || "Người dùng");
                }}
                className="input-box"
                style={{
                  padding: "4px 8px",
                  fontSize: "12.5px",
                  marginBottom: 0,
                  width: "auto",
                  height: "32px",
                }}
              >
                <option value="guest">Khách (Guest)</option>
                <option value="member">Hội viên (Member)</option>
                <option value="trainer">Huấn luyện viên (PT)</option>
                <option value="receptionist">Lễ tân (Reception)</option>
                <option value="facility_manager">CSVC (Facility)</option>
                <option value="admin">Quản trị (Admin)</option>
              </select>
            </div>

            {/* User chip */}
            {user ? (
              <div className="sneat-user-dropdown" title={`${user.full_name} (${role})`}>
                <div className="sneat-avatar">
                  {user.full_name?.charAt(0) || "U"}
                </div>
                <div style={{ display: "flex", flexDirection: "column", textAlign: "left" }}>
                  <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--heading-color)" }}>
                    {user.full_name}
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--muted-color)", textTransform: "capitalize" }}>
                    {role}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="hg-btn-ghost hg-btn-sm"
                  style={{ padding: "3px 8px", fontSize: "11px", marginLeft: "4px" }}
                >
                  Thoát
                </button>
              </div>
            ) : (
              <Link href="/login" className="hg-btn-primary hg-btn-sm">
                Đăng nhập
              </Link>
            )}
          </div>
        </header>
      </div>
    </>
  );
}
