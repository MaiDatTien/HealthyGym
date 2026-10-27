"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { Chip, KV, Note, ProgressRing, SectionTitle, Stat, Toast } from "@/components/ui";
import type {
  ChallengeItem,
  LeaderboardRow,
  PointsInfo,
  RewardItem,
  StreakInfo,
} from "@/lib/erp-types";

/* ==========================================================================
   ĐIỂM THƯỞNG & THÀNH TÍCH — Gamification
   Streak, huy hiệu, bảng xếp hạng, thử thách, tích điểm đổi quà, giới thiệu bạn bè.
   ========================================================================== */

export default function RewardsPage() {
  const [streak, setStreak] = useState<StreakInfo | null>(null);
  const [points, setPoints] = useState<PointsInfo | null>(null);
  const [rewards, setRewards] = useState<RewardItem[]>([]);
  const [leaderboard, setLeaderboard] = useState<any>(null);
  const [challenges, setChallenges] = useState<ChallengeItem[]>([]);
  const [referrals, setReferrals] = useState<any>(null);
  const [tab, setTab] = useState<"progress" | "rewards" | "ranking" | "challenges">("progress");
  const [metric, setMetric] = useState("checkins");
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [refForm, setRefForm] = useState({ name: "", phone: "" });

  const load = () => {
    fetchGymData("/engagement/streak/my").then(setStreak).catch(() => {});
    fetchGymData("/engagement/points/my").then(setPoints).catch(() => {});
    fetchGymData("/engagement/rewards").then(setRewards).catch(() => {});
    fetchGymData("/engagement/challenges").then(setChallenges).catch(() => {});
    fetchGymData("/engagement/referrals/my").then(setReferrals).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    fetchGymData(`/engagement/leaderboard?period=month&metric=${metric}`)
      .then(setLeaderboard)
      .catch(() => {});
  }, [metric]);

  const redeem = async (rewardId: number, name: string, cost: number) => {
    try {
      const res = await postGymData("/engagement/rewards/redeem", { reward_id: rewardId });
      setToast({ kind: "ok", text: res.message });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const joinChallenge = async (challengeId: number) => {
    try {
      const res = await postGymData("/engagement/challenges/join", { challenge_id: challengeId });
      setToast({ kind: "ok", text: res.message });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  const sendReferral = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await postGymData("/engagement/referrals", {
        referred_name: refForm.name,
        referred_phone: refForm.phone,
      });
      setToast({ kind: "ok", text: res.message });
      setRefForm({ name: "", phone: "" });
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    }
  };

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <Chip>THÀNH TÍCH &amp; ĐIỂM THƯỞNG</Chip>
          <h1>Điểm Thưởng Của Tôi</h1>
          <p>Tích điểm khi tập luyện, đổi quà, thi đua cùng cộng đồng hội viên.</p>
        </div>
        {points && (
          <div className="hg-flex">
            <Chip tone="gold">
              {Number(points.current_points).toLocaleString("vi-VN")} ĐIỂM
            </Chip>
          </div>
        )}
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      {streak && points && (
        <div className="hg-metric-grid">
          <Stat label="Chuỗi tuần liên tiếp" value={streak.current_week_streak} gold />
          <Stat label="Chuỗi dài nhất" value={streak.longest_week_streak} />
          <Stat label="Buổi tập tuần này" value={streak.this_week_visits} />
          <Stat label="Tổng buổi tập" value={streak.total_checkins} />
          <Stat label="Huy hiệu đạt được" value={streak.badges_earned} />
          <Stat label="Tổng điểm tích luỹ" value={points.total_earned} gold />
        </div>
      )}

      {streak?.motivation && <Note tone={streak.streak_broken ? "warn" : "ok"}>{streak.motivation}</Note>}

      <div className="hg-tabs">
        <button className={`hg-tab ${tab === "progress" ? "active" : ""}`} onClick={() => setTab("progress")}>
          Tiến độ &amp; Huy hiệu
        </button>
        <button className={`hg-tab ${tab === "rewards" ? "active" : ""}`} onClick={() => setTab("rewards")}>
          Đổi quà
        </button>
        <button className={`hg-tab ${tab === "ranking" ? "active" : ""}`} onClick={() => setTab("ranking")}>
          Bảng xếp hạng
        </button>
        <button className={`hg-tab ${tab === "challenges" ? "active" : ""}`} onClick={() => setTab("challenges")}>
          Thử thách
        </button>
      </div>

      {/* ================= TIẾN ĐỘ & HUY HIỆU ================= */}
      {tab === "progress" && (
        <div className="hg-grid-2">
          <div className="hg-chart-card">
            <div className="hg-chart-title">Chuỗi tập luyện</div>
            <div className="hg-flex" style={{ justifyContent: "space-around", marginBottom: "18px" }}>
              <div className="hg-stack" style={{ alignItems: "center" }}>
                <ProgressRing
                  percent={Math.min(100, (streak?.current_week_streak ?? 0) * 8.33)}
                  label="Chuỗi tuần"
                  color="#0b6e8f"
                />
                <span className="hg-muted">{streak?.current_week_streak ?? 0}/12 tuần</span>
              </div>
              <div className="hg-stack" style={{ alignItems: "center" }}>
                <ProgressRing
                  percent={Math.min(100, ((streak?.this_week_visits ?? 0) / 3) * 100)}
                  label="Mục tiêu tuần"
                  color="#b8860b"
                />
                <span className="hg-muted">{streak?.this_week_visits ?? 0}/3 buổi</span>
              </div>
            </div>

            {streak?.next_milestone && (
              <Note tone="gold">
                Còn <strong>{streak.next_milestone.remaining} tuần</strong> nữa để đạt mốc{" "}
                {streak.next_milestone.weeks} tuần liên tiếp. {streak.next_milestone.reward_hint}
              </Note>
            )}

            <div className="hg-kv">
              <span>Chuỗi ngày liên tiếp</span>
              <span className="hg-num-mono">{streak?.current_day_streak ?? 0} ngày</span>
            </div>
            <div className="hg-kv">
              <span>Kỷ lục chuỗi ngày</span>
              <span className="hg-num-mono">{streak?.longest_day_streak ?? 0} ngày</span>
            </div>
            <div className="hg-kv">
              <span>Buổi tập đã ghi nhật ký</span>
              <span className="hg-num-mono">{streak?.total_workouts_logged ?? 0} buổi</span>
            </div>
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Huy hiệu của bạn</div>
            {(streak?.badges ?? []).length === 0 ? (
              <div className="hg-empty">
                <h3>Chưa có huy hiệu</h3>
                <p>Tập luyện đều đặn để mở khoá các huy hiệu thành tích.</p>
              </div>
            ) : (
              streak!.badges.map((b, i) => (
                <div key={i} className="hg-kv">
                  <span>
                    <strong>{b.name}</strong>
                    <div className="hg-exercise-muscle">{b.description}</div>
                  </span>
                  <span>
                    <Chip tone="gold">{b.category?.toUpperCase()}</Chip>
                  </span>
                </div>
              ))
            )}

            <SectionTitle>Cách tích điểm</SectionTitle>
            <ul className="benefit-list">
              {(points?.how_to_earn ?? []).map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Giới thiệu bạn bè</div>
            <p className="hg-chart-sub">
              Nhận 500 điểm khi người được giới thiệu chốt gói tập thành công.
            </p>

            {referrals && (
              <div className="hg-metric-grid">
                <Stat label="Đã giới thiệu" value={referrals.total_referrals} />
                <Stat label="Chốt gói thành công" value={referrals.converted} gold />
                <Stat label="Điểm nhận được" value={referrals.points_earned} />
              </div>
            )}

            <form onSubmit={sendReferral}>
              <label>Tên bạn bè</label>
              <input
                className="input-box"
                value={refForm.name}
                onChange={(e) => setRefForm({ ...refForm, name: e.target.value })}
                required
              />
              <label>Số điện thoại</label>
              <input
                className="input-box"
                value={refForm.phone}
                onChange={(e) => setRefForm({ ...refForm, phone: e.target.value })}
                required
              />
              <button className="hg-btn-primary" style={{ width: "100%" }}>
                Gửi lời giới thiệu
              </button>
            </form>
          </div>

          <div className="hg-chart-card">
            <div className="hg-chart-title">Điểm theo nguồn</div>
            {(points?.by_source ?? []).length === 0 ? (
              <div className="hg-empty">Chưa có dữ liệu điểm.</div>
            ) : (
              points!.by_source.map((s) => (
                <div key={s.kind} className="hg-kv">
                  <span>{s.label}</span>
                  <span
                    className="hg-num-mono"
                    style={{ fontWeight: 600, color: s.points >= 0 ? "#0f7a52" : "#b01c2e" }}
                  >
                    {s.points >= 0 ? "+" : ""}
                    {s.points}
                  </span>
                </div>
              ))
            )}

            <SectionTitle>Lịch sử gần đây</SectionTitle>
            <div style={{ maxHeight: "260px", overflowY: "auto" }}>
              {(points?.history ?? []).slice(0, 20).map((h, i) => (
                <div key={i} className="hg-kv">
                  <span>
                    <strong>{h.label}</strong>
                    <div className="hg-exercise-muscle">
                      {new Date(h.created_at).toLocaleDateString("vi-VN")}
                    </div>
                  </span>
                  <span
                    className="hg-num-mono"
                    style={{ fontWeight: 600, color: h.points >= 0 ? "#0f7a52" : "#b01c2e" }}
                  >
                    {h.points >= 0 ? "+" : ""}
                    {h.points}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ================= ĐỔI QUÀ ================= */}
      {tab === "rewards" && (
        <div>
          <Note tone="gold">
            Bạn đang có <strong>{points?.current_points ?? 0} điểm</strong>. Quy đổi tham khảo:
            10 điểm ≈ 10.000đ giá trị.
          </Note>
          <div className="grid">
            {rewards.map((r) => {
              const canAfford = (points?.current_points ?? 0) >= r.points_cost;
              return (
                <div key={r.id} className="card" style={{ gap: "10px" }}>
                  <div className="hg-flex" style={{ justifyContent: "space-between" }}>
                    <Chip tone="gold">{r.kind.toUpperCase()}</Chip>
                    <span
                      className="hg-num-mono"
                      style={{ fontSize: "16px", fontWeight: 700, color: "#8a6408" }}
                    >
                      {r.points_cost} điểm
                    </span>
                  </div>
                  <div style={{ fontWeight: 600, fontSize: "14px" }}>{r.name}</div>
                  {r.description && <div className="hg-muted">{r.description}</div>}
                  {r.value_amount > 0 && (
                    <div className="hg-exercise-muscle">
                      Giá trị: {Number(r.value_amount).toLocaleString("vi-VN")}đ
                    </div>
                  )}
                  {!canAfford && (
                    <div className="hg-muted" style={{ color: "#b45309" }}>
                      Cần thêm {r.points_cost - (points?.current_points ?? 0)} điểm
                    </div>
                  )}
                  <button
                    className={canAfford ? "hg-btn-gold" : "hg-btn-ghost"}
                    style={{ marginTop: "auto" }}
                    disabled={!canAfford}
                    onClick={() => redeem(r.id, r.name, r.points_cost)}
                  >
                    {canAfford ? "Đổi quà ngay" : "Chưa đủ điểm"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ================= BẢNG XẾP HẠNG ================= */}
      {tab === "ranking" && (
        <div>
          <div className="hg-flex" style={{ marginBottom: "16px" }}>
            {[
              { k: "checkins", label: "Số buổi tập" },
              { k: "points", label: "Điểm thưởng" },
              { k: "streak", label: "Chuỗi liên tiếp" },
              { k: "volume", label: "Khối lượng tập" },
            ].map((m) => (
              <button
                key={m.k}
                className={metric === m.k ? "hg-btn-primary hg-btn-sm" : "hg-btn-ghost hg-btn-sm"}
                onClick={() => setMetric(m.k)}
              >
                {m.label}
              </button>
            ))}
          </div>

          {leaderboard && (
            <>
              <Note>
                Bảng xếp hạng <strong>{leaderboard.metric_label}</strong> ·{" "}
                {leaderboard.period_label}
              </Note>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: "60px" }}>Hạng</th>
                      <th>Hội viên</th>
                      <th>Hạng thẻ</th>
                      <th>{leaderboard.metric_label}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.leaderboard.length === 0 ? (
                      <tr>
                        <td colSpan={4} style={{ textAlign: "center" }}>
                          Chưa có dữ liệu xếp hạng.
                        </td>
                      </tr>
                    ) : (
                      leaderboard.leaderboard.map((row: LeaderboardRow) => (
                        <tr key={row.member_id}>
                          <td>
                            <strong className="hg-num-mono">
                              {row.medal ? `${row.medal} ` : ""}#{row.rank}
                            </strong>
                          </td>
                          <td>
                            <strong>{row.member_name}</strong>
                          </td>
                          <td>
                            <Chip tone={row.tier === "vip" ? "gold" : "default"}>
                              {row.tier?.toUpperCase()}
                            </Chip>
                          </td>
                          <td className="hg-num-mono" style={{ fontWeight: 600 }}>
                            {Number(row.value).toLocaleString("vi-VN")} {row.unit}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* ================= THỬ THÁCH ================= */}
      {tab === "challenges" && (
        <div>
          {challenges.length === 0 ? (
            <div className="hg-empty">
              <h3>Chưa có thử thách nào</h3>
              <p>Hiện không có thử thách nào đang mở đăng ký.</p>
            </div>
          ) : (
            challenges.map((c) => (
              <div key={c.id} className="hg-chart-card">
                <div className="hg-chart-title">
                  <span>{c.name}</span>
                  <Chip tone={c.is_open ? "ok" : "warn"}>
                    {c.is_open ? "ĐANG DIỄN RA" : "SẮP BẮT ĐẦU"}
                  </Chip>
                </div>

                <p className="hg-muted" style={{ marginBottom: "14px" }}>
                  {c.description}
                </p>

                <div className="hg-metric-grid">
                  <Stat label="Bắt đầu" value={c.start_date} />
                  <Stat label="Kết thúc" value={c.end_date} />
                  <Stat label="Còn lại" value={`${c.days_remaining} ngày`} gold />
                  <Stat label="Người tham gia" value={`${c.participants}/${c.max_participants}`} />
                  <Stat label="Điểm thưởng" value={c.reward_points} gold />
                </div>

                {c.prize_description && <Note tone="gold">{c.prize_description}</Note>}

                <button
                  className="hg-btn-primary"
                  onClick={() => joinChallenge(c.id)}
                  disabled={!c.is_open || c.participants >= c.max_participants}
                >
                  {c.participants >= c.max_participants ? "Đã đủ người" : "Đăng ký tham gia"}
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}