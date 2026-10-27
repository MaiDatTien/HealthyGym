"use client";
import React, { useEffect, useState } from "react";
import PropertyCard from "@/components/PropertyCard";
import { fetchGymData } from "@/lib/api";

export default function BranchesPage() {
  const [branches, setBranches] = useState<any[]>([]);
  const [city, setCity] = useState("ALL");

  useEffect(() => {
    fetchGymData("/listings/branches").then(setBranches).catch(() => {});
  }, []);

  const filtered = branches.filter((b) =>
    city === "ALL" ? true : b.name.includes(city) || b.address.includes(city)
  );

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">MỞ CỬA 24/7 TOÀN QUỐC</span>
          <h1 style={{ marginTop: "0.4rem" }}>Hệ Thống Phòng Tập HealthyGym</h1>
          <p style={{ color: "#64748b" }}>Tìm kiếm chi nhánh thuận tiện nhất cho việc đi lại của bạn.</p>
        </div>
        <select
          className="input-box"
          style={{ width: "240px", marginBottom: 0, fontWeight: 700 }}
          value={city}
          onChange={(e) => setCity(e.target.value)}
        >
          <option value="ALL">Tất cả Tỉnh / Thành phố</option>
          <option value="Hồ Chí Minh">TP. Hồ Chí Minh</option>
          <option value="Đà Nẵng">Đà Nẵng</option>
          <option value="Cần Thơ">Cần Thơ</option>
          <option value="Đồng Nai">Đồng Nai</option>
        </select>
      </div>

      <div className="grid">
        {filtered.map((b) => (
          <PropertyCard key={b.id} branch={b} />
        ))}
      </div>
    </div>
  );
}
