"use client";
import React, { useEffect, useMemo, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { Chip, Note, SectionTitle, Stat, Toast } from "@/components/ui";
import type {
  ClassScheduleDetail,
  ClassScheduleItem,
  MyClassBooking,
  PenaltyInfo,
} from "@/lib/erp-types";

/* ==========================================================================
   GROUP-X — Lịch lớp tập nhóm, chọn vị trí, danh sách chờ tự động.
   ========================================================================== */

export default function GroupXPage() {
  const [schedules, setSchedules] = useState<ClassScheduleItem[]>([]);
  const [myBookings, setMyBookings] = useState<MyClassBooking[]>([]);
  const [penalty, setPenalty] = useState<PenaltyInfo | null>(null);
  const [category, setCategory] = useState("ALL");
  const [detail, setDetail] = useState<ClassScheduleDetail | null>(null);
  const [selectedSpot, setSelectedSpot] = useState<number | null>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    fetchGymData("/groupx/schedules?days_ahead=14").then(setSchedules).catch(() => {});
    fetchGymData("/groupx/my-bookings").then(setMyBookings).catch(() => {});
    fetchGymData("/groupx/penalties/my").then(setPenalty).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  const categories = useMemo(
    () => ["ALL", ...Array.from(new Set(schedules.map((s) => s.category).filter(Boolean) as string[]))],
    [schedules]
  );

  const filtered = schedules.filter((s) => category === "ALL" || s.category === category);

  // Nhóm theo ngày
  const byDate = useMemo(() => {
    const map = new Map<string, ClassScheduleItem[]>();
    filtered.forEach((s) => {
      const key = s.start_time.slice(0, 10);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(s);
    });
    return Array.from(map.entries()).slice(0, 10);
  }, [filtered]);

  const openDetail = async (id: number) => {
    try {
      const d = await fetchGymData(`/groupx/schedules/${id}`);
      setDetail(d);
      setSelectedSpot(null);
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const book = async (scheduleId: number, spotId?: number | null) => {
    setBusy(true);
    try {
      const res = await postGymData("/groupx/book", {
        schedule_id: scheduleId,
        spot_id: spotId ?? null,
      });
      setToast({ kind: res.status === "waitlisted" ? "ok" : "ok", text: res.message });
      setDetail(null);
      setSelectedSpot(null);
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const cancel = async (bookingId: number) => {
    try {
      const res = await postGymData(`/groupx/bookings/${bookingId}/cancel`);
      setToast({ kind: "ok", text: res.message });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const dayLabel = (iso: string) => {
    const dt = new Date(iso + "T00:00:00");
    const days = ["Chủ Nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"];
    return `${days[dt.getDay()]} ${dt.getDate()}/${dt.getMonth() + 1}`;
  };

  const timeLabel = (iso: string) => iso.slice(11, 16);

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <Chip>GROUP-X</Chip>
          <h1>Lịch Lớp Tập Nhóm</h1>
          <p>
            Yoga, HIIT, Boxing, Strength. Lớp đầy chỗ sẽ tự động vào danh sách chờ — hệ thống
            đôn bạn lên ngay khi có người hủy.
          </p>
        </div>
        <div className="hg-flex">
          <Chip tone="gold">{schedules.length} buổi học</Chip>
          <Chip>{myBookings.length} lượt đặt</Chip>
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      {/* Cảnh báo hình phạt no-show */}
      {penalty?.warning && (
        <div className={penalty.is_blocked ? "hg-warning-box" : "hg-note"}>
          <strong>{penalty.is_blocked ? "QUYỀN ĐẶT LỚP ĐANG BỊ KHÓA" : "LƯU Ý"}</strong>
          <p style={{ marginTop: "6px" }}>{penalty.warning}</p>
          {!penalty.is_blocked && (
            <p className="hg-muted" style={{ marginTop: "4px" }}>{penalty.advice}</p>
          )}
        </div>
      )}

      {/* Bộ lọc */}
      <div className="hg-flex" style={{ marginBottom: "20px" }}>
        {categories.map((cat) => (
          <button
            key={cat}
            className={category === cat ? "hg-btn-primary" : "hg-btn-ghost"}
            onClick={() => setCategory(cat)}
          >
            {cat === "ALL" ? "Tất cả" : cat}
          </button>
        ))}
      </div>

      {/* Danh sách theo ngày */}
      {byDate.length === 0 ? (
        <div className="hg-empty">
          <h3>Không có lớp học nào</h3>
          <p>Chưa có lịch lớp trong 14 ngày tới cho bộ môn này.</p>
        </div>
      ) : (
        byDate.map(([date, items]) => (
          <div key={date}>
            <SectionTitle>{dayLabel(date)}</SectionTitle>
            <div className="grid">
              {items.map((s) => {
                const booked = myBookings.find(
                  (b) => b.class_name === s.class_name && b.start_time === s.start_time
                );
                return (
                  <div key={s.id} className="card" style={{ gap: "10px" }}>
                    <div className="hg-flex" style={{ justifyContent: "space-between" }}>
                      <span
                        style={{
                          fontFamily: "IBM Plex Mono, monospace",
                          fontSize: "17px",
                          fontWeight: 600,
                          color: "#0d1f26",
                        }}
                      >
                        {timeLabel(s.start_time)}
                      </span>
                      <Chip tone={s.is_full ? "warn" : "ok"}>
                        {s.available_spots}/{s.capacity} chỗ
                      </Chip>
                    </div>

                    <div>
                      <div style={{ fontWeight: 600, fontSize: "14px" }}>{s.class_name}</div>
                      <div className="hg-exercise-muscle">
                        {s.category} · {s.studio} · {s.difficulty}
                      </div>
                    </div>

                    <div className="hg-flex">
                      <Chip>HLV {s.trainer_name.replace(/^HLV\s+/, "")}</Chip>
                      {s.is_substituted && <Chip tone="warn">Dạy thay</Chip>}
                      {s.requires_spot_selection && <Chip tone="gold">Chọn vị trí</Chip>}
                      {s.waitlist_count > 0 && <Chip tone="warn">{s.waitlist_count} chờ</Chip>}
                    </div>

                    {/* Thanh lấp đầy */}
                    <div className="progress-bar" style={{ margin: 0 }}>
                      <div
                        className="progress-fill"
                        style={{
                          width: `${s.fill_percent}%`,
                          background: s.is_full ? "#b45309" : "#0b6e8f",
                        }}
                      />
                    </div>

                    {booked ? (
                      <div className="hg-flex" style={{ marginTop: "auto" }}>
                        <Chip tone="ok">
                          {booked.status === "waitlisted"
                            ? "ĐANG CHỜ"
                            : booked.spot_code
                            ? `ĐÃ ĐẶT · ${booked.spot_code}`
                            : "ĐÃ ĐẶT"}
                        </Chip>
                        <button className="hg-btn-ghost hg-btn-sm" onClick={() => cancel(booked.booking_id)}>
                          Hủy
                        </button>
                      </div>
                    ) : s.requires_spot_selection ? (
                      <button
                        className="hg-btn-primary"
                        style={{ marginTop: "auto" }}
                        onClick={() => openDetail(s.id)}
                        disabled={penalty?.is_blocked}
                      >
                        Chọn vị trí và đặt chỗ
                      </button>
                    ) : (
                      <button
                        className={s.is_full ? "hg-btn-ghost" : "hg-btn-primary"}
                        style={{ marginTop: "auto" }}
                        onClick={() => book(s.id)}
                        disabled={busy || penalty?.is_blocked}
                      >
                        {s.is_full ? "Vào danh sách chờ" : "Đặt chỗ"}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))
      )}

      {/* Modal chọn vị trí */}
      {detail && (
        <div className="modal-backdrop" onClick={() => setDetail(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="hg-flex" style={{ justifyContent: "space-between" }}>
              <div>
                <Chip tone="gold">SƠ ĐỒ PHÒNG</Chip>
                <h3 style={{ marginTop: "8px", fontSize: "16px" }}>{detail.class_name}</h3>
                <p className="hg-muted">
                  {dayLabel(detail.start_time.slice(0, 10))} · {timeLabel(detail.start_time)} ·{" "}
                  {detail.studio}
                </p>
              </div>
              <button className="hg-btn-ghost hg-btn-sm" onClick={() => setDetail(null)}>
                Đóng
              </button>
            </div>

            <div className="hg-metric-grid" style={{ marginTop: "16px" }}>
              <Stat label="Sức chứa" value={detail.capacity} />
              <Stat label="Đã đặt" value={detail.enrolled_count} />
              <Stat label="Còn trống" value={detail.available_spots} gold />
            </div>

            {detail.spot_map.length === 0 ? (
              <Note>Chưa có sơ đồ vị trí cho buổi học này.</Note>
            ) : (
              detail.spot_map.map((zone) => (
                <div key={zone.zone} style={{ marginBottom: "16px" }}>
                  <div className="hg-metric-label" style={{ marginBottom: "8px" }}>
                    {zone.zone} — {zone.spots.filter((s) => s.is_available).length}/
                    {zone.spots.length} trống
                  </div>
                  <div className="hg-slot-grid">
                    {zone.spots.map((sp) => (
                      <button
                        key={sp.id}
                        className={`hg-slot ${selectedSpot === sp.id ? "selected" : ""}`}
                        disabled={!sp.is_available}
                        onClick={() => setSelectedSpot(sp.id)}
                      >
                        <div className="hg-slot-time">{sp.spot_code}</div>
                        <div className="hg-slot-sub">{sp.is_available ? "Trống" : "Đã đặt"}</div>
                      </button>
                    ))}
                  </div>
                </div>
              ))
            )}

            <div className="hg-flex" style={{ marginTop: "16px" }}>
              <button
                className="hg-btn-primary"
                onClick={() => book(detail.id, selectedSpot)}
                disabled={busy || (detail.requires_spot_selection && !selectedSpot)}
              >
                {selectedSpot ? "Xác nhận đặt chỗ" : "Chọn một vị trí"}
              </button>
              {detail.available_spots === 0 && (
                <button className="hg-btn-ghost" onClick={() => book(detail.id, null)} disabled={busy}>
                  Vào danh sách chờ
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Lịch sử đặt lớp */}
      <SectionTitle>Lịch sử đặt lớp của bạn</SectionTitle>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Lớp</th>
              <th>Thời gian</th>
              <th>Vị trí</th>
              <th>Trạng thái</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {myBookings.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: "center" }}>
                  Bạn chưa đặt lớp nào.
                </td>
              </tr>
            ) : (
              myBookings.map((b) => (
                <tr key={b.booking_id}>
                  <td>
                    <strong>{b.class_name}</strong>
                    <div className="hg-exercise-muscle">{b.studio}</div>
                  </td>
                  <td className="hg-num">
                    {b.start_time
                      ? `${dayLabel(b.start_time.slice(0, 10))} ${timeLabel(b.start_time)}`
                      : "—"}
                  </td>
                  <td className="hg-num-mono">{b.spot_code ?? "—"}</td>
                  <td>
                    <Chip
                      tone={
                        b.status === "attended"
                          ? "ok"
                          : b.status === "no_show"
                          ? "danger"
                          : b.status === "cancelled"
                          ? "warn"
                          : "default"
                      }
                    >
                      {b.status === "attended"
                        ? "Đã tập"
                        : b.status === "no_show"
                        ? "Vắng mặt"
                        : b.status === "cancelled"
                        ? "Đã hủy"
                        : b.promoted_from_waitlist
                        ? "Đôn từ chờ"
                        : "Đã đặt"}
                    </Chip>
                  </td>
                  <td>
                    {(b.status === "confirmed" || b.status === "waitlisted") && (
                      <button className="hg-btn-ghost hg-btn-sm" onClick={() => cancel(b.booking_id)}>
                        Hủy chỗ
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}