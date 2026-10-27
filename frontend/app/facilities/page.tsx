"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData } from "@/lib/api";

export default function FacilitiesPage() {
  const [facilities, setFacilities] = useState<any[]>([]);
  const [trainers, setTrainers] = useState<any[]>([]);

  useEffect(() => {
    fetchGymData("/listings/facilities").then(setFacilities).catch(() => {});
    fetchGymData("/listings/trainers").then(setTrainers).catch(() => {});
  }, []);

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">TRANG THIẾT BỊ & ĐỘI NGŨ CHUYÊN GIA</span>
          <h1 style={{ marginTop: "0.4rem" }}>Cơ Sở Vật Chất & Huấn Luyện Viên</h1>
          <p style={{ color: "#64748b" }}>
            Không gian tập luyện chuẩn quốc tế cùng đội ngũ PT giàu kinh nghiệm luôn sẵn sàng đồng hành cùng bạn.
          </p>
        </div>
      </div>

      <h2 style={{ fontSize: "1.5rem", fontWeight: 800, marginBottom: "1rem" }}>
        🏋️ Thiết Bị Tập Luyện & Tiện Ích Miễn Phí
      </h2>
      <div className="grid">
        {facilities.map((f) => (
          <div key={f.id} className="card">
            <div>
              <span className="chip">{f.category}</span>
              <h3 style={{ margin: "0.6rem 0" }}>{f.name}</h3>
              <p style={{ color: "#64748b", fontSize: "0.92rem" }}>{f.description}</p>
            </div>
            <div style={{ marginTop: "1rem", fontWeight: 700, color: "#0e6d8c" }}>
              ✓ {f.status} • Số lượng: {f.quantity}
            </div>
          </div>
        ))}
      </div>

      <h2 style={{ fontSize: "1.5rem", fontWeight: 800, marginBottom: "1rem" }}>
        🏆 Đội Ngũ Huấn Luyện Viên (Personal Trainers)
      </h2>
      <div className="grid">
        {trainers.map((t) => (
          <div key={t.id} className="card">
            <div>
              <span className="chip">{t.experience_years} năm kinh nghiệm</span>
              <h3 style={{ margin: "0.6rem 0" }}>{t.full_name}</h3>
              <p style={{ color: "#c02a3f", fontWeight: 700, fontSize: "0.92rem" }}>{t.specialty}</p>
              <p style={{ color: "#64748b", fontSize: "0.9rem", marginTop: "0.5rem" }}>{t.bio}</p>
            </div>
            <div style={{ marginTop: "1rem", fontSize: "0.88rem", color: "#475569" }}>
              📞 Liên hệ PT: <strong>{t.phone || "1900 636920"}</strong>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
