"use client";
import React from "react";
import { formatCurrency } from "@/lib/format";
import { CheckIcon } from "./Icons";

interface PlanProps {
  plan: {
    id: number;
    name: string;
    duration_days: number;
    price: number;
    benefits?: string;
    includes_pt: boolean;
    is_popular: boolean;
  };
  onSelectPlan: (plan: any) => void;
}

export default function ListingCard({ plan, onSelectPlan }: PlanProps) {
  const benefitList = plan.benefits ? plan.benefits.split(",") : [];
  const months = Math.max(1, Math.round(plan.duration_days / 30));
  const monthlyPrice = Math.round(plan.price / months);

  return (
    <div className={`tng-plan-card ${plan.is_popular ? "tng-plan-popular" : ""}`}>
      {plan.is_popular ? (
        <div className="tng-popular-ribbon">⭐ PHỔ BIẾN NHẤT ⭐</div>
      ) : (
        <div className="tng-normal-ribbon">
          {months === 1 ? "TRẢ TỪNG THÁNG" : `GÓI ${months} THÁNG`}
        </div>
      )}

      <div className="tng-plan-body">
        <h3 className="tng-plan-title">{plan.name}</h3>
        <p className="tng-plan-scope">
          {plan.is_popular ? "Tập mọi chi nhánh trên toàn quốc" : "1 chi nhánh tự chọn"}
        </p>

        <div className="tng-price-box">
          <span className="tng-price-num">
            {new Intl.NumberFormat("vi-VN").format(monthlyPrice)}
          </span>
          <span className="tng-price-unit"> VNĐ /Tháng</span>
        </div>

        {months > 1 ? (
          <p className="tng-sub-price">
            Trọn gói <strong>{formatCurrency(plan.price)}</strong> · Tiết kiệm 25%
          </p>
        ) : (
          <p className="tng-sub-price">Thanh toán tiền mặt, QR hoặc thẻ quốc tế</p>
        )}

        <button className="tng-btn-join" onClick={() => onSelectPlan(plan)}>
          Tham gia gói
        </button>

        <div className="divider" />

        <ul className="benefit-list">
          {benefitList.map((b, idx) => (
            <li key={idx}>
              <CheckIcon /> <span>{b.trim()}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
