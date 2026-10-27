"use client";
import React from "react";
import { LocationIcon } from "./Icons";

interface BranchProps {
  branch: {
    id: number;
    name: string;
    address: string;
    phone?: string;
    opening_hours: string;
  };
}

export default function PropertyCard({ branch }: BranchProps) {
  return (
    <div className="card">
      <h3>{branch.name}</h3>
      <p>
        <LocationIcon /> {branch.address}
      </p>
      <p>📞 Hotline: {branch.phone || "1900 6868"}</p>
      <p>⏰ Giờ mở cửa: {branch.opening_hours}</p>
    </div>
  );
}
