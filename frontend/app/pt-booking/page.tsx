"use client";
import React, { useEffect, useMemo, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { SectionTitle, Toast } from "@/components/ui";
import type { TrainerSlotItem } from "@/lib/types";

/* ==========================================================================
   ĐẶT LỊCH TẬP 1-1 VỚI HUẤN LUYỆN VIÊN (Real-time Slot)
   ========================================================================== */

export default function PTBookingPage() {
  const [trainers, setTrainers] = useState<any[]>([]);
  const [slots, setSlots] = useState<TrainerSlotItem[]>([]);
  const [bookings, setBookings] = useState<any[]>([]);
  const [selectedTrainer, setSelectedTrainer] = useState<number | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const [goalNote, setGoalNote] = useState("");
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const loadTrainers = () => fetchGymData("/pt/trainers").then(setTrainers).catch(() => {});
  const loadSlots = () =>
    fetchGymData("/pt/slots?only_available=true&days_ahead=14")
      .then(setSlots)
      .catch(() => {});
  const loadBookings = () =>
    fetchGymData("/pt/bookings/my").then(setBookings).catch(() => {});

  useEffect(() => {
    loadTrainers();
    loadSlots();
    loadBookings();
  }, []);

  // Nhóm khung giờ theo NGÀY để giao diện dễ chọn
  const slotsByDate = useMemo(() => {
    const filtered = selectedTrainer
      ? slots.filter((s) => s.trainer_id === selectedTrainer)
      : slots;
    const map = new Map<string, TrainerSlotItem[]>();
    filtered.forEach((s) => {
      const key = s.session_date;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(s);
    });
    return Array.from(map.entries()).slice(0, 10);
  }, [slots, selectedTrainer]);

  const dayLabel = (iso: string) => {
    const dt = new Date(iso + "T00:00:00");
    const days = ["Chủ Nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"];
    return `${days[dt.getDay()]}, ${dt.getDate()}/${dt.getMonth() + 1}`;
  };

  const book = async () => {
    if (!selectedSlot) {
      setToast({ kind: "err", text: "Vui lòng chọn một khung giờ trống." });
      return;
    }
    setLoading(true);
    try {
      const res = await postGymData("/pt/bookings", {
        slot_id: selectedSlot,
        goal_note: goalNote || null,
      });
      setToast({ kind: "ok", text: res.message });
      setSelectedSlot(null);
      setGoalNote("");
      loadSlots();
      loadBookings();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
      loadSlots();
    } finally {
      setLoading(false);
    }
  };

  const cancel = async (id: number) => {
    try {
      const res = await postGymData(`/pt/bookings/${id}/cancel`);
      setToast({ kind: "ok", text: res.message });
      loadSlots();
      loadBookings();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  // --- BƯỚC 2 của xác nhận kép: hội viên xác nhận cuối buổi kèm đánh giá sao ---
  const [confirming, setConfirming] = useState<number | null>(null);
  const [rating, setRating] = useState(5);
  const [feedback, setFeedback] = useState("");

  const confirmSession = async (bookingId: number) => {
    try {
      const res = await postGymData("/pt-ops/burn/confirm", {
        booking_id: bookingId,
        method: "app_button",
        rating,
        feedback: feedback || null,
      });
      setToast({ kind: res.both_confirmed ? "ok" : "err", text: res.message });
      if (!res.both_confirmed && res.how_to_fix) {
        setTimeout(() => setToast({ kind: "err", text: res.how_to_fix }), 1500);
      }
      setConfirming(null);
      setFeedback("");
      setRating(5);
      loadBookings();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">HUẤN LUYỆN CÁ NHÂN 1-1</span>
          <h1 style={{ marginTop: "0.4rem" }}>Đặt Lịch Tập Với PT</h1>
          <p className="hg-muted">
            Chọn huấn luyện viên và khung giờ trống theo thời gian thực. Thời lượng mỗi buổi 60 phút.
          </p>
        </div>
        <div className="hg-flex">
          <span className="chip chip-gold">{slots.length} khung giờ trống</span>
          <span className="chip">{trainers.length} huấn luyện viên</span>
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      {/* ---------- DANH SÁCH HLV ---------- */}
      <SectionTitle>Chọn Huấn Luyện Viên</SectionTitle>
      <div className="grid" style={{ marginBottom: "2rem" }}>
        <button
          className="hg-trainer-card"
          style={{
            cursor: "pointer",
            textAlign: "left",
            fontFamily: "inherit",
            border: selectedTrainer === null ? "2px solid #1391b4" : undefined,
            background: selectedTrainer === null ? "#eef7fb" : undefined,
          }}
          onClick={() => setSelectedTrainer(null)}
        >
          <div className="hg-trainer-avatar">ALL</div>
          <strong style={{ color: "#0a3d55" }}>Tất cả huấn luyện viên</strong>
          <span className="hg-muted">Hiển thị mọi khung giờ còn trống</span>
        </button>

        {trainers.map((t) => (
          <button
            key={t.id}
            className="hg-trainer-card"
            style={{
              cursor: "pointer",
              textAlign: "left",
              fontFamily: "inherit",
              border: selectedTrainer === t.id ? "2px solid #c9a227" : undefined,
              background: selectedTrainer === t.id ? "#fdf7e3" : undefined,
            }}
            onClick={() => setSelectedTrainer(t.id)}
          >
            <div className="hg-trainer-avatar">
              {t.full_name.replace(/^HLV\s+/, "").charAt(0)}
            </div>
            <strong style={{ color: "#0a3d55", fontSize: "1rem" }}>{t.full_name}</strong>
            <span className="chip" style={{ alignSelf: "flex-start" }}>
              {t.specialty}
            </span>
            <div className="hg-flex" style={{ gap: "0.4rem" }}>
              <span className="chip chip-gold">★ {t.rating}</span>
              <span className="chip">{t.experience_years} năm kinh nghiệm</span>
            </div>
            <span className="hg-muted" style={{ fontSize: "0.84rem" }}>{t.bio}</span>
            {t.certifications && (
              <span className="hg-muted" style={{ fontSize: "0.78rem", fontStyle: "italic" }}>
                🎓 {t.certifications}
              </span>
            )}
            <span className={`chip ${t.available_slots > 0 ? "chip-ok" : "chip-warn"}`}>
              {t.available_slots > 0 ? `${t.available_slots} khung giờ trống` : "Tạm hết khung giờ"}
            </span>
          </button>
        ))}
      </div>

      {/* ---------- CHỌN KHUNG GIỜ ---------- */}
      <SectionTitle>Chọn Khung Giờ Trống</SectionTitle>
      {slotsByDate.length === 0 ? (
        <div className="hg-empty">
          Hiện không có khung giờ trống trong 14 ngày tới. Vui lòng chọn huấn luyện viên khác.
        </div>
      ) : (
        slotsByDate.map(([date, daySlots]) => (
          <div key={date} className="hg-chart-card">
            <div className="hg-chart-title">
              <span>📅 {dayLabel(date)}</span>
              <span className="chip">{daySlots.length} khung giờ</span>
            </div>
            <div className="hg-slot-grid">
              {daySlots.map((s) => (
                <button
                  key={s.id}
                  className={`hg-slot ${selectedSlot === s.id ? "selected" : ""}`}
                  onClick={() => setSelectedSlot(s.id)}
                >
                  <div className="hg-slot-time">{s.time_label}</div>
                  <div className="hg-slot-sub">
                    {s.trainer_name.replace(/^HLV\s+/, "")}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ))
      )}

      {/* ---------- XÁC NHẬN ---------- */}
      {selectedSlot && (
        <div className="hg-chart-card" style={{ borderColor: "#c9a227", borderWidth: 2 }}>
          <div className="hg-chart-title">Xác nhận đặt lịch</div>
          {(() => {
            const s = slots.find((x) => x.id === selectedSlot);
            if (!s) return null;
            return (
              <div className="hg-verdict" style={{ marginBottom: "1rem" }}>
                <p>
                  <strong>{s.trainer_name}</strong> · {dayLabel(s.session_date)} lúc{" "}
                  <strong>{s.time_label}</strong> ({s.duration_minutes} phút)
                </p>
                <p className="hg-muted">{s.trainer_specialty}</p>
              </div>
            );
          })()}
          <input
            className="input-box"
            placeholder="Mục tiêu buổi tập (VD: Sửa kỹ thuật Squat, đau lưng dưới)"
            value={goalNote}
            onChange={(e) => setGoalNote(e.target.value)}
          />
          <div className="hg-flex">
            <button className="hg-btn-gold" onClick={book} disabled={loading}>
              {loading && <span className="hg-spinner" />}
              Xác nhận đặt lịch 1-1
            </button>
            <button className="hg-btn-ghost" onClick={() => setSelectedSlot(null)}>
              Hủy chọn
            </button>
          </div>
          <p className="hg-muted" style={{ marginTop: "0.7rem" }}>
            Lưu ý: chỉ có thể hủy lịch trước giờ tập ít nhất 12 giờ.
          </p>
        </div>
      )}

      {/* ---------- BUỔI TẬP CHỜ HỘI VIÊN XÁC NHẬN (XÁC NHẬN KÉP) ---------- */}
      {(() => {
        const pending = bookings.filter((b: any) => b.needs_confirmation);
        if (pending.length === 0) return null;
        return (
          <div className="hg-chart-card" style={{ borderColor: "#b8860b", borderWidth: 2 }}>
            <div className="hg-chart-title">
              Buổi tập chờ bạn xác nhận ({pending.length})
            </div>
            <p className="hg-chart-sub">
              Huấn luyện viên đã đánh dấu hoàn thành buổi tập. Để buổi được trừ khỏi gói, bạn cần
              xác nhận tại đây. Cơ chế xác nhận kép này bảo vệ quyền lợi của bạn.
            </p>

            {pending.map((b: any) => (
              <div
                key={b.id}
                style={{
                  border: "1px solid #d4e0e5",
                  padding: "12px",
                  marginBottom: "10px",
                  background: "#fafcfd",
                }}
              >
                <div className="hg-flex" style={{ justifyContent: "space-between" }}>
                  <span>
                    <strong>{b.trainer_name}</strong>
                    <div className="hg-exercise-muscle">
                      {b.start_time
                        ? new Date(b.start_time).toLocaleString("vi-VN", {
                            weekday: "short",
                            day: "2-digit",
                            month: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "—"}{" "}
                      · Buổi #{b.id}
                    </div>
                  </span>
                  <span>
                    <span className={`chip ${b.member_checked_in ? "chip-ok" : "chip-danger"}`}>
                      {b.member_checked_in ? "ĐÃ CHECK-IN" : "CHƯA CHECK-IN CỔNG"}
                    </span>
                  </span>
                </div>

                {!b.member_checked_in && (
                  <div className="hg-note danger" style={{ marginTop: "8px" }}>
                    Bạn chưa check-in tại cổng phòng gym hôm nay. Theo quy định chống gian lận, cần
                    đủ cả 2 điều kiện mới trừ buổi. Hãy check-in tại quầy lễ tân rồi xác nhận lại.
                  </div>
                )}

                {confirming === b.id ? (
                  <div style={{ marginTop: "10px" }}>
                    <label>Đánh giá buổi tập</label>
                    <div className="hg-flex" style={{ gap: "4px", marginBottom: "10px" }}>
                      {[1, 2, 3, 4, 5].map((r) => (
                        <button
                          key={r}
                          className={rating === r ? "hg-btn-gold hg-btn-sm" : "hg-btn-ghost hg-btn-sm"}
                          onClick={() => setRating(r)}
                        >
                          {r} sao
                        </button>
                      ))}
                    </div>
                    <input
                      className="input-box"
                      placeholder="Nhận xét về buổi tập (không bắt buộc)"
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                    />
                    <div className="hg-flex">
                      <button className="hg-btn-gold" onClick={() => confirmSession(b.id)}>
                        Xác nhận hoàn thành buổi tập
                      </button>
                      <button className="hg-btn-ghost" onClick={() => setConfirming(null)}>
                        Để sau
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    className="hg-btn-primary hg-btn-sm"
                    style={{ marginTop: "10px" }}
                    onClick={() => {
                      setConfirming(b.id);
                      setRating(5);
                    }}
                  >
                    Xác nhận &amp; đánh giá
                  </button>
                )}
              </div>
            ))}
          </div>
        );
      })()}

      {/* ---------- LỊCH ĐÃ ĐẶT ---------- */}
      <SectionTitle>Lịch 1-1 của bạn ({bookings.length})</SectionTitle>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Huấn luyện viên</th>
              <th>Thời gian</th>
              <th>Trạng thái</th>
              <th>Đánh giá</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {bookings.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "#6b8598" }}>
                  Bạn chưa có lịch tập 1-1 nào.
                </td>
              </tr>
            ) : (
              bookings.map((b) => (
                <tr key={b.id}>
                  <td>
                    <div className="hg-exercise-name">{b.trainer_name}</div>
                    <div className="hg-exercise-muscle">{b.trainer_specialty}</div>
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {b.start_time
                      ? new Date(b.start_time).toLocaleString("vi-VN", {
                          weekday: "short",
                          day: "2-digit",
                          month: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : "—"}
                  </td>
                  <td>
                    <span
                      className={`chip ${
                        b.status === "confirmed"
                          ? "chip-ok"
                          : b.status === "completed"
                          ? ""
                          : "chip-danger"
                      }`}
                    >
                      {b.status === "confirmed"
                        ? "Đã xác nhận"
                        : b.status === "completed"
                        ? "Hoàn thành"
                        : b.status === "cancelled"
                        ? "Đã hủy"
                        : b.status}
                    </span>
                  </td>
                  <td>{b.rating ? `★ ${b.rating}/5` : "—"}</td>
                  <td>
                    {b.status === "confirmed" && (
                      <button className="hg-btn-ghost" onClick={() => cancel(b.id)}>
                        Hủy lịch
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