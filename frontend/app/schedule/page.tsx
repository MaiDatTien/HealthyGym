"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";

export default function SchedulePage() {
  const [classes, setClasses] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [keyword, setKeyword] = useState("");
  const [msg, setMsg] = useState<{ type: string; text: string } | null>(null);

  const loadClasses = () => {
    fetchGymData("/listings/classes").then(setClasses).catch(() => {});
  };

  useEffect(() => {
    loadClasses();
  }, []);

  const handleBook = async (classId: number) => {
    try {
      const res = await postGymData("/interactions/bookings", {
        gym_class_id: classId,
        note: "Đặt lịch từ trang Schedule",
      });
      setMsg({ type: "ok", text: res.message });
      loadClasses();
    } catch (err: any) {
      setMsg({ type: "err", text: err.message });
    }
  };

  const filtered = classes.filter((c) => {
    const matchCat = selectedCategory === "ALL" || c.category === selectedCategory;
    const matchKw =
      c.name.toLowerCase().includes(keyword.toLowerCase()) ||
      c.trainer_name.toLowerCase().includes(keyword.toLowerCase());
    return matchCat && matchKw;
  });

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">GROUP X & STUDIO</span>
          <h1 style={{ marginTop: "0.4rem" }}>Lịch Lớp Tập Nhóm & Đặt Chỗ</h1>
          <p style={{ color: "#64748b" }}>
            Chủ động đặt lịch trước để giữ chỗ cho các lớp Yoga, HIIT, Boxing và Strength.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {["ALL", "Yoga", "HIIT", "Boxing", "Strength"].map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={selectedCategory === cat ? "hg-btn-emerald" : "hg-btn-ghost"}
            >
              {cat === "ALL" ? "Tất cả" : cat}
            </button>
          ))}
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

      <input
        className="input-box"
        style={{ maxWidth: "360px", marginBottom: "1.5rem" }}
        placeholder="🔍 Tìm theo tên lớp hoặc Huấn luyện viên..."
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
      />

      <div className="grid">
        {filtered.map((c) => {
          const percent = Math.min(100, Math.round((c.enrolled_count / c.capacity) * 100));
          return (
            <div key={c.id} className="card">
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="chip">{c.category}</span>
                  <strong style={{ fontSize: "0.85rem", color: c.available_spots > 0 ? "#0e6d8c" : "#c02a3f" }}>
                    Còn {c.available_spots}/{c.capacity} chỗ
                  </strong>
                </div>
                <h3 style={{ margin: "0.6rem 0", fontSize: "1.25rem" }}>{c.name}</h3>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${percent}%` }} />
                </div>
                <p style={{ fontSize: "0.9rem" }}>🕒 {c.schedule_time}</p>
                <p style={{ fontSize: "0.9rem" }}>📍 Phòng: {c.room} ({c.branch_name})</p>
                <p style={{ fontSize: "0.9rem" }}>💪 HLV: <strong>{c.trainer_name}</strong></p>
                <p style={{ color: "#64748b", fontSize: "0.88rem", marginTop: "0.5rem" }}>{c.description}</p>
              </div>
              <button
                className="hg-btn-emerald"
                style={{ width: "100%", marginTop: "1rem" }}
                disabled={c.available_spots <= 0}
                onClick={() => handleBook(c.id)}
              >
                {c.available_spots > 0 ? "Đặt Chỗ Lớp Này" : "Đã Đầy Chỗ"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
