"use client";
import React from "react";

/* ==========================================================================
   Bộ thành phần UI Sneat Design System:
   - Bo góc mềm (8px / 6px)
   - Bóng đổ nhẹ, phẳng, tinh tế
   - Màu chủ đạo tím Sneat (#696cff), xanh lá (#71dd37), xanh ngọc (#03c3ec), cam (#ffab00), đỏ (#ff3e1d)
   - Biểu đồ SVG thuần, bo tròn đầu cột và nét cong mềm mại
   ========================================================================== */

export function Metric({
  label,
  value,
  unit,
  note,
  gold,
}: {
  label: string;
  value: React.ReactNode;
  unit?: string;
  note?: string;
  gold?: boolean;
}) {
  return (
    <div className={`sneat-metric ${gold ? "primary" : ""}`}>
      <div className="sneat-metric-label">{label}</div>
      <div className="sneat-metric-value">
        {value}
        {unit && <span className="sneat-metric-unit">{unit}</span>}
      </div>
      {note && <div className="sneat-metric-note">{note}</div>}
    </div>
  );
}

export function Toast({
  kind,
  children,
}: {
  kind: "ok" | "err";
  children: React.ReactNode;
}) {
  return <div className={`sneat-toast ${kind}`}>{children}</div>;
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="sneat-section-title">{children}</h2>;
}

/** Nhãn trạng thái dạng chip Sneat */
export function Chip({
  children,
  tone = "default",
}: {
  children: React.ReactNode;
  tone?: "default" | "gold" | "ok" | "warn" | "danger";
}) {
  const cls =
    tone === "gold"
      ? "badge-primary"
      : tone === "ok"
      ? "badge-success"
      : tone === "warn"
      ? "badge-warning"
      : tone === "danger"
      ? "badge-danger"
      : "badge-secondary";
  return <span className={`badge ${cls}`}>{children}</span>;
}

/** Khối ghi chú / cảnh báo phong cách Sneat alert */
export function Note({
  tone = "default",
  children,
}: {
  tone?: "default" | "gold" | "ok" | "warn" | "danger";
  children: React.ReactNode;
}) {
  const cls =
    tone === "gold"
      ? "alert-primary"
      : tone === "ok"
      ? "alert-success"
      : tone === "warn"
      ? "alert-warning"
      : tone === "danger"
      ? "alert-danger"
      : "alert-secondary";
  return <div className={`sneat-alert ${cls}`}>{children}</div>;
}

/* --------------------------------------------------------------------------
   BIỂU ĐỒ ĐƯỜNG — SVG thuần với nét cong mềm & gradient đổ bóng Sneat
   -------------------------------------------------------------------------- */
export function LineChart({
  labels,
  series,
  height = 240,
  unit = "",
  colors = ["#696cff", "#ffab00", "#71dd37"],
  yLabelFormatter,
}: {
  labels: string[];
  series: { name: string; data: (number | null)[] }[];
  height?: number;
  unit?: string;
  colors?: string[];
  yLabelFormatter?: (v: number) => string;
}) {
  const width = 760;
  const padL = 50;
  const padR = 20;
  const padT = 20;
  const padB = 40;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const all = series
    .flatMap((s) => s.data)
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));

  if (all.length === 0) {
    return <div className="hg-empty">Chưa có dữ liệu để vẽ biểu đồ.</div>;
  }

  const rawMin = Math.min(...all);
  const rawMax = Math.max(...all);
  const span = rawMax - rawMin || Math.max(1, Math.abs(rawMax) * 0.1 || 1);
  const min = Math.max(0, rawMin - span * 0.15);
  const max = rawMax + span * 0.15;

  const n = labels.length;
  const xAt = (i: number) => (n <= 1 ? padL + plotW / 2 : padL + (plotW * i) / (n - 1));
  const yAt = (v: number) => padT + plotH - ((v - min) / (max - min)) * plotH;

  const labelStep = Math.max(1, Math.ceil(n / 8));
  const grid = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div className="hg-scroll-x" style={{ overflowX: "auto" }}>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img">
        <defs>
          {series.map((s, si) => {
            const color = colors[si % colors.length];
            return (
              <linearGradient
                key={`grad-${si}`}
                id={`line-grad-${si}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="0%" stopColor={color} stopOpacity="0.25" />
                <stop offset="100%" stopColor={color} stopOpacity="0.0" />
              </linearGradient>
            );
          })}
        </defs>

        {/* Lưới ngang */}
        {grid.map((g, gi) => {
          const value = min + (max - min) * (1 - g);
          const y = padT + plotH * g;
          return (
            <g key={gi}>
              <line
                x1={padL}
                y1={y}
                x2={width - padR}
                y2={y}
                stroke="#eceef1"
                strokeWidth="1"
                strokeDasharray={gi === grid.length - 1 ? "0" : "4 4"}
              />
              <text
                x={padL - 10}
                y={y + 4}
                textAnchor="end"
                fontSize="11"
                fill="#a1acb8"
                fontFamily="Public Sans, sans-serif"
                fontWeight="500"
              >
                {yLabelFormatter ? yLabelFormatter(value) : Math.round(value * 10) / 10}
              </text>
            </g>
          );
        })}

        {/* Nhãn trục X */}
        {labels.map((lb, i) =>
          i % labelStep === 0 ? (
            <text
              key={i}
              x={xAt(i)}
              y={height - 12}
              textAnchor="middle"
              fontSize="11"
              fill="#a1acb8"
              fontFamily="Public Sans, sans-serif"
            >
              {lb.length > 10 ? lb.slice(5) : lb}
            </text>
          ) : null
        )}

        {/* Vùng màu bên dưới và Đường dữ liệu */}
        {series.map((s, si) => {
          const color = colors[si % colors.length];
          const validPoints: { x: number; y: number; val: number; idx: number }[] = [];

          s.data.forEach((v, i) => {
            if (typeof v === "number" && Number.isFinite(v)) {
              validPoints.push({ x: xAt(i), y: yAt(v), val: v, idx: i });
            }
          });

          if (validPoints.length === 0) return null;

          // Tạo chuỗi đường gấp khúc
          const lineD = validPoints
            .map((p, idx) => `${idx === 0 ? "M" : "L"} ${p.x} ${p.y}`)
            .join(" ");

          const first = validPoints[0];
          const last = validPoints[validPoints.length - 1];
          const areaD = `${lineD} L ${last.x} ${padT + plotH} L ${first.x} ${padT + plotH} Z`;

          return (
            <g key={s.name}>
              <path d={areaD} fill={`url(#line-grad-${si})`} />
              <path
                d={lineD}
                fill="none"
                stroke={color}
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              {validPoints.map((p, i) => (
                <circle
                  key={i}
                  cx={p.x}
                  cy={p.y}
                  r="4.5"
                  fill="#ffffff"
                  stroke={color}
                  strokeWidth="2.5"
                >
                  <title>{`${s.name}: ${p.val}${unit} (${labels[p.idx]})`}</title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>

      {series.length > 1 && (
        <div className="hg-flex" style={{ justifyContent: "center", marginTop: "10px", gap: "16px" }}>
          {series.map((s, si) => (
            <span key={s.name} className="hg-flex" style={{ gap: "6px" }}>
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  background: colors[si % colors.length],
                  display: "inline-block",
                }}
              />
              <span style={{ fontSize: "12px", color: "#566a7f", fontWeight: 500 }}>
                {s.name}
              </span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* --------------------------------------------------------------------------
   BIỂU ĐỒ CỘT — Sneat Bar Chart với bo góc đầu cột
   -------------------------------------------------------------------------- */
export function BarChart({
  labels,
  data,
  height = 200,
  color = "#696cff",
  goal,
  unit = "",
}: {
  labels: string[];
  data: (number | null)[];
  height?: number;
  color?: string;
  goal?: number | null;
  unit?: string;
}) {
  const nums = data.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (nums.length === 0) return <div className="hg-empty">Chưa có dữ liệu.</div>;

  const max = Math.max(...nums, goal ?? 0) * 1.15 || 1;

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: "8px",
          height,
          borderBottom: "1px solid #d9dee3",
          position: "relative",
          paddingTop: "24px",
        }}
      >
        {goal ? (
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: `${(goal / max) * 100}%`,
              borderTop: "1.5px dashed #ffab00",
            }}
          >
            <span
              style={{
                position: "absolute",
                right: 0,
                top: -18,
                fontSize: "10px",
                fontWeight: 600,
                color: "#ffab00",
                background: "#fff",
                padding: "2px 6px",
                borderRadius: "4px",
                boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              }}
            >
              MỤC TIÊU {goal}
              {unit}
            </span>
          </div>
        ) : null}

        {data.map((v, i) => {
          const h = typeof v === "number" && Number.isFinite(v) ? (v / max) * 100 : 0;
          return (
            <div
              key={i}
              title={`${labels[i]}: ${v ?? "—"}${unit}`}
              style={{
                flex: 1,
                minWidth: 8,
                height: `${Math.max(4, h)}%`,
                background: color,
                borderRadius: "6px 6px 0 0",
                transition: "height 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
                opacity: 0.9,
              }}
            />
          );
        })}
      </div>
      <div
        style={{
          display: "flex",
          gap: "8px",
          marginTop: "8px",
          fontSize: "11px",
          color: "#a1acb8",
          fontWeight: 500,
        }}
      >
        {labels.map((lb, i) => (
          <div key={i} style={{ flex: 1, textAlign: "center", overflow: "hidden" }}>
            {labels.length <= 12 || i % Math.ceil(labels.length / 12) === 0
              ? lb.length > 10
                ? lb.slice(5)
                : lb
              : ""}
          </div>
        ))}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------------------
   VÒNG TIẾN ĐỘ TRÒN (Circular Progress Gauge)
   -------------------------------------------------------------------------- */
export function ProgressRing({
  percent,
  size = 96,
  label,
  color = "#696cff",
}: {
  percent: number;
  size?: number;
  label?: string;
  color?: string;
}) {
  const safe = Math.max(0, Math.min(100, percent));
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (safe / 100) * c;

  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#f5f5f9"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={c}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.6s cubic-bezier(0.4, 0, 0.2, 1)" }}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <strong
          style={{
            fontSize: "18px",
            fontWeight: 700,
            color: "#566a7f",
            lineHeight: 1,
          }}
        >
          {Math.round(safe)}%
        </strong>
        {label && (
          <span
            style={{
              fontSize: "10px",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
              color: "#a1acb8",
              marginTop: "4px",
              fontWeight: 600,
            }}
          >
            {label}
          </span>
        )}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------------------
   THANH PHÂN BỔ MACROS
   -------------------------------------------------------------------------- */
export function MacroBar({
  protein,
  carbs,
  fat,
}: {
  protein: number;
  carbs: number;
  fat: number;
}) {
  const pKcal = protein * 4;
  const cKcal = carbs * 4;
  const fKcal = fat * 9;
  const total = pKcal + cKcal + fKcal || 1;

  const seg = [
    { label: "ĐẠM", kcal: pKcal, color: "#696cff", grams: protein },
    { label: "TINH BỘT", kcal: cKcal, color: "#03c3ec", grams: carbs },
    { label: "CHẤT BÉO", kcal: fKcal, color: "#ffab00", grams: fat },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          height: 18,
          borderRadius: "9px",
          overflow: "hidden",
          background: "#eceef1",
        }}
      >
        {seg.map((s) => (
          <div
            key={s.label}
            title={`${s.label}: ${s.grams}g (${Math.round((s.kcal / total) * 100)}%)`}
            style={{
              width: `${(s.kcal / total) * 100}%`,
              background: s.color,
              transition: "width 0.4s ease",
            }}
          />
        ))}
      </div>
      <div className="hg-flex" style={{ marginTop: "12px", gap: "20px" }}>
        {seg.map((s) => (
          <span key={s.label} className="hg-flex" style={{ gap: "8px" }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: s.color,
                display: "inline-block",
              }}
            />
            <span style={{ fontSize: "13px", color: "#566a7f" }}>
              {s.label} <strong>{s.grams}g</strong>{" "}
              <small style={{ color: "#a1acb8" }}>
                ({Math.round((s.kcal / total) * 100)}%)
              </small>
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------------------
   NHÃN CHÊNH LỆCH DELTA
   -------------------------------------------------------------------------- */
export function Delta({
  value,
  unit,
  invert = false,
}: {
  value: number;
  unit: string;
  invert?: boolean;
}) {
  const flat = Math.abs(value) < 0.05;
  const good = invert ? value < 0 : value > 0;
  const cls = flat ? "flat" : good ? "positive" : "negative";
  const arrow = flat ? "•" : value > 0 ? "▲ +" : "▼ ";
  return (
    <span className={`sneat-delta ${cls}`}>
      {arrow}
      {Math.abs(value)}
      {unit}
    </span>
  );
}

/* --------------------------------------------------------------------------
   HÀNG NHÃN – GIÁ TRỊ (KV)
   -------------------------------------------------------------------------- */
export function KV({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="sneat-kv">
      <span className="sneat-kv-label">{label}</span>
      <span className="sneat-kv-value">{children}</span>
    </div>
  );
}

/** Ô số liệu lớn dùng trong dải thống kê Sneat */
export function Stat({
  label,
  value,
  gold,
}: {
  label: string;
  value: React.ReactNode;
  gold?: boolean;
}) {
  return (
    <div className={`sneat-stat-item ${gold ? "primary" : ""}`}>
      <div className="sneat-stat-label">{label}</div>
      <div className="sneat-stat-val">{value}</div>
    </div>
  );
}
