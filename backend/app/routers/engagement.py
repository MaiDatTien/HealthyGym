"""Router GAMIFICATION, CỘNG ĐỒNG & CRM GIỮ CHÂN HỘI VIÊN.

Bao gồm: streak, huy hiệu, bảng xếp hạng, thử thách biến đổi hình thể,
tích điểm đổi quà, giới thiệu bạn bè, và quét rủi ro rời bỏ (churn).
"""
from __future__ import annotations

import json
import secrets
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai import WorkoutLog
from app.models.engagement import (
    Badge, Challenge, ChallengeEntry, ChurnRiskSnapshot, LoyaltyPoint,
    MemberBadge, MemberStreak, PointKind, Referral, RenewalReminder,
    RetentionTask, Reward, RewardRedemption,
)
from app.models.interaction import now_local
from app.models.membership import ContractStatus, MembershipContract
from app.models.operations import GateCheckin, GateResult
from app.models.user import Member, User
from app.schemas.erp import (
    ChallengeCreate, ChallengeFinalize, ChallengeJoin, LeaderboardQuery,
    ReferralCreate, RenewalOfferCreate, RetentionTaskUpdate,
    RewardCreate, RewardRedeem,
)
from app.security import get_current_user, require_operations

router = APIRouter(prefix="/engagement", tags=["Gamification & CRM Retention"])


#: Ngưỡng điểm thưởng
POINTS_CHECKIN = 10
POINTS_WEEKLY_GOAL = 50
POINTS_REFERRAL = 500

#: Mốc cảnh báo vắng mặt (ngày)
CHURN_THRESHOLDS = (7, 14, 30)


def _member_of(user: User, db: Session) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hội viên")
    return member


def _award_points(
    member: Member, points: int, kind: str, note: str, db: Session, reference: Optional[str] = None
) -> int:
    """Cộng điểm và ghi sổ cái."""
    new_balance = (member.loyalty_points or 0) + points
    member.loyalty_points = new_balance
    member.total_points_earned = (member.total_points_earned or 0) + max(0, points)
    db.add(LoyaltyPoint(
        member_id=member.id,
        points=points,
        balance_after=new_balance,
        kind=kind,
        reference=reference,
        note=note,
    ))
    return new_balance


# ==========================================================================
# STREAK & HUY HIỆU
# ==========================================================================
@router.get("/streak/my")
def my_streak(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Chuỗi ngày/tuần đi tập liên tục của hội viên."""
    member = _member_of(current_user, db)
    streak = db.query(MemberStreak).filter(MemberStreak.member_id == member.id).first()

    if not streak:
        streak = MemberStreak(member_id=member.id)
        db.add(streak)
        db.commit()
        db.refresh(streak)

    # Đứt chuỗi nếu quá 7 ngày không tập
    today = date.today()
    broken = False
    if streak.last_activity_date:
        gap = (today - streak.last_activity_date).days
        if gap > 7 and (streak.current_week_streak or 0) > 0:
            broken = True

    badges = (
        db.query(MemberBadge)
        .filter(MemberBadge.member_id == member.id)
        .order_by(MemberBadge.earned_at.desc())
        .all()
    )

    next_milestone = None
    for milestone in (4, 8, 12, 26, 52):
        if (streak.current_week_streak or 0) < milestone:
            next_milestone = {
                "weeks": milestone,
                "remaining": milestone - (streak.current_week_streak or 0),
                "reward_hint": f"Đạt {milestone} tuần liên tiếp để nhận huy hiệu đặc biệt",
            }
            break

    return {
        "current_day_streak": streak.current_day_streak,
        "longest_day_streak": streak.longest_day_streak,
        "current_week_streak": streak.current_week_streak,
        "longest_week_streak": streak.longest_week_streak,
        "this_week_visits": streak.this_week_visits,
        "total_checkins": streak.total_checkins,
        "total_workouts_logged": streak.total_workouts_logged,
        "last_activity_date": streak.last_activity_date,
        "streak_broken": broken,
        "next_milestone": next_milestone,
        "loyalty_points": member.loyalty_points,
        "badges_earned": len(badges),
        "badges": [
            {
                "code": b.badge.code if b.badge else None,
                "name": b.badge.name if b.badge else None,
                "category": b.badge.category if b.badge else None,
                "earned_at": b.earned_at,
                "description": b.badge.description if b.badge else None,
            }
            for b in badges
        ],
        "motivation": (
            f"🔥 Bạn đang có chuỗi {streak.current_week_streak} tuần tập liên tiếp! "
            f"Đừng để đứt chuỗi — chỉ cần 1 buổi tập trong tuần này."
            if (streak.current_week_streak or 0) >= 2 else
            (
                f"Chuỗi của bạn đã đứt sau {streak.longest_week_streak} tuần. "
                f"Bắt đầu lại từ tuần này — 1 buổi tập là đủ để mở chuỗi mới!"
                if broken else
                "Hãy tập ít nhất 3 buổi trong tuần này để bắt đầu xây chuỗi."
            )
        ),
    }


@router.post("/streak/update")
def update_streak(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Cập nhật chuỗi đi tập (gọi sau khi hội viên hoàn thành buổi tập)."""
    member = _member_of(current_user, db)
    today = date.today()

    streak = db.query(MemberStreak).filter(MemberStreak.member_id == member.id).first()
    if not streak:
        streak = MemberStreak(member_id=member.id)
        db.add(streak)

    # Đếm số buổi tập trong tuần hiện tại (từ Thứ 2)
    week_start = today - timedelta(days=today.weekday())
    visits_this_week = (
        db.query(func.count(GateCheckin.id))
        .filter(
            GateCheckin.member_id == member.id,
            GateCheckin.result == GateResult.GRANTED,
            GateCheckin.checkin_time >= datetime.combine(week_start, datetime.min.time()),
        )
        .scalar()
        or 0
    )

    newly_earned: list[dict] = []
    points = 0
    old_week_streak = streak.current_week_streak or 0

    # Hội viên đạt mục tiêu tuần (>= 3 buổi)?
    if visits_this_week >= 3 and old_week_streak == 0:
        streak.current_week_streak = 1
        points = POINTS_WEEKLY_GOAL
        newly_earned.append({
            "name": "Mục tiêu tuần đạt được",
            "points": POINTS_WEEKLY_GOAL,
        })
    elif visits_this_week >= 3 and streak.last_activity_date:
        weeks_since = (today - streak.last_activity_date).days // 7
        if weeks_since == 1:
            streak.current_week_streak = old_week_streak + 1

    streak.longest_week_streak = max(
        streak.longest_week_streak or 0, streak.current_week_streak or 0
    )
    streak.last_activity_date = today
    streak.this_week_visits = visits_this_week
    streak.total_workouts_logged = (streak.total_workouts_logged or 0) + 1

    balance = member.loyalty_points or 0
    if points:
        balance = _award_points(
            member, points, PointKind.WORKOUT_GOAL,
            f"Đạt mục tiêu {visits_this_week} buổi tập trong tuần", db,
        )

    # --- Kiểm tra và trao huy hiệu tự động ---
    total_volume = (
        db.query(func.coalesce(func.sum(WorkoutLog.sets * WorkoutLog.reps * WorkoutLog.weight_kg), 0))
        .filter(WorkoutLog.member_id == member.id)
        .scalar()
        or 0
    )
    badge_stats = {
        "checkin_count": streak.total_checkins or 0,
        "streak": streak.current_week_streak or 0,
        "points": member.total_points_earned or 0,
        "volume": float(total_volume),
    }

    candidate_badges = db.query(Badge).filter(Badge.is_active == True).all()
    for badge in candidate_badges:
        already = (
            db.query(MemberBadge)
            .filter(MemberBadge.member_id == member.id, MemberBadge.badge_id == badge.id)
            .first()
        )
        if already:
            continue

        value = badge_stats.get(badge.criteria_type or "", 0)
        if badge.criteria_value and value >= badge.criteria_value:
            db.add(MemberBadge(
                member_id=member.id,
                badge_id=badge.id,
                progress_value=value,
                note=f"Tự động trao khi đạt {badge.criteria_type} >= {badge.criteria_value}",
            ))
            if badge.point_reward:
                balance = _award_points(
                    member, badge.point_reward, PointKind.BONUS,
                    f"Huy hiệu: {badge.name}", db,
                )
            newly_earned.append({
                "code": badge.code,
                "name": badge.name,
                "points": badge.point_reward,
                "description": badge.description,
            })

    db.commit()

    return {
        "message": (
            f"Đã cập nhật chuỗi tập luyện: {visits_this_week} buổi trong tuần này, "
            f"chuỗi {streak.current_week_streak} tuần liên tiếp."
        ),
        "visits_this_week": visits_this_week,
        "current_week_streak": streak.current_week_streak,
        "longest_week_streak": streak.longest_week_streak,
        "points_awarded": points,
        "points_balance": balance,
        "newly_earned": newly_earned,
    }


@router.get("/badges")
def list_badges(db: Session = Depends(get_db)):
    """Danh mục toàn bộ huy hiệu của hệ thống."""
    badges = db.query(Badge).filter(Badge.is_active == True).all()
    return [
        {
            "id": b.id,
            "code": b.code,
            "name": b.name,
            "description": b.description,
            "category": b.category,
            "criteria_type": b.criteria_type,
            "criteria_value": b.criteria_value,
            "criteria_exercise": b.criteria_exercise,
            "point_reward": b.point_reward,
        }
        for b in badges
    ]


# ==========================================================================
# BẢNG XẾP HẠNG
# ==========================================================================
@router.get("/leaderboard")
def leaderboard(
    period: str = Query("month", pattern="^(week|month|all)$"),
    metric: str = Query("checkins", pattern="^(checkins|points|streak|volume)$"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Bảng xếp hạng hội viên — tạo động lực cạnh tranh lành mạnh."""
    today = date.today()
    if period == "week":
        since = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
        period_label = "tuần này"
    elif period == "month":
        since = datetime.combine(today.replace(day=1), datetime.min.time())
        period_label = "tháng này"
    else:
        since = datetime(2000, 1, 1)
        period_label = "mọi thời đại"

    rows: list[dict] = []

    if metric == "checkins":
        data = (
            db.query(
                Member.id, Member.full_name, Member.tier,
                func.count(GateCheckin.id).label("value"),
            )
            .join(GateCheckin, GateCheckin.member_id == Member.id)
            .filter(
                GateCheckin.result == GateResult.GRANTED,
                GateCheckin.checkin_time >= since,
            )
            .group_by(Member.id, Member.full_name, Member.tier)
            .order_by(func.count(GateCheckin.id).desc())
            .limit(limit)
            .all()
        )
        rows = [
            {"member_id": r.id, "member_name": r.full_name, "tier": r.tier,
             "value": r.value, "unit": "buổi tập"}
            for r in data
        ]

    elif metric == "points":
        data = (
            db.query(Member.id, Member.full_name, Member.tier, Member.loyalty_points)
            .filter(Member.loyalty_points > 0)
            .order_by(Member.loyalty_points.desc())
            .limit(limit)
            .all()
        )
        rows = [
            {"member_id": r.id, "member_name": r.full_name, "tier": r.tier,
             "value": r.loyalty_points, "unit": "điểm"}
            for r in data
        ]

    elif metric == "streak":
        data = (
            db.query(
                Member.id, Member.full_name, Member.tier,
                MemberStreak.current_week_streak,
            )
            .join(MemberStreak, MemberStreak.member_id == Member.id)
            .filter(MemberStreak.current_week_streak > 0)
            .order_by(MemberStreak.current_week_streak.desc())
            .limit(limit)
            .all()
        )
        rows = [
            {"member_id": r.id, "member_name": r.full_name, "tier": r.tier,
             "value": r.current_week_streak, "unit": "tuần liên tiếp"}
            for r in data
        ]

    else:  # volume
        data = (
            db.query(
                Member.id, Member.full_name, Member.tier,
                func.coalesce(
                    func.sum(WorkoutLog.sets * WorkoutLog.reps * WorkoutLog.weight_kg), 0
                ).label("value"),
            )
            .join(WorkoutLog, WorkoutLog.member_id == Member.id)
            .filter(WorkoutLog.log_date >= since.date())
            .group_by(Member.id, Member.full_name, Member.tier)
            .order_by(func.sum(WorkoutLog.sets * WorkoutLog.reps * WorkoutLog.weight_kg).desc())
            .limit(limit)
            .all()
        )
        rows = [
            {"member_id": r.id, "member_name": r.full_name, "tier": r.tier,
             "value": round(float(r.value)), "unit": "kg khối lượng tập"}
            for r in data
        ]

    # Gắn thứ hạng
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
        row["medal"] = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else None))

    metric_labels = {
        "checkins": "Số buổi tập",
        "points": "Điểm thưởng tích luỹ",
        "streak": "Chuỗi tuần liên tiếp",
        "volume": "Tổng khối lượng tập",
    }

    return {
        "period": period,
        "period_label": period_label,
        "metric": metric,
        "metric_label": metric_labels.get(metric, metric),
        "leaderboard": rows,
        "empty_note": (
            "Chưa có dữ liệu xếp hạng cho kỳ này."
            if not rows else None
        ),
    }


# ==========================================================================
# THỬ THÁCH BIẾN ĐỔI HÌNH THỂ
# ==========================================================================
@router.get("/challenges")
def list_challenges(
    active_only: bool = True, db: Session = Depends(get_db)
):
    """Danh sách thử thách."""
    query = db.query(Challenge)
    if active_only:
        today = date.today()
        query = query.filter(
            Challenge.is_active == True,
            Challenge.end_date >= today,
        )
    challenges = query.order_by(Challenge.start_date.desc()).all()

    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "kind": c.kind,
            "start_date": c.start_date,
            "end_date": c.end_date,
            "days_remaining": max(0, (c.end_date - date.today()).days),
            "max_participants": c.max_participants,
            "participants": db.query(func.count(ChallengeEntry.id))
            .filter(ChallengeEntry.challenge_id == c.id).scalar() or 0,
            "entry_fee": c.entry_fee,
            "prize_description": c.prize_description,
            "reward_points": c.reward_points,
            "is_open": c.start_date <= date.today() <= c.end_date,
        }
        for c in challenges
    ]


@router.post("/challenges")
def create_challenge(
    data: ChallengeCreate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Tạo thử thách mới (Admin)."""
    if data.end_date <= data.start_date:
        raise HTTPException(status_code=422, detail="Ngày kết thúc phải sau ngày bắt đầu")

    challenge = Challenge(**data.model_dump(), is_active=True)
    db.add(challenge)
    db.commit()
    db.refresh(challenge)

    return {
        "message": f"Đã tạo thử thách '{challenge.name}'",
        "challenge_id": challenge.id,
        "duration_days": (challenge.end_date - challenge.start_date).days,
    }


@router.post("/challenges/join")
def join_challenge(
    data: ChallengeJoin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hội viên đăng ký tham gia thử thách với chỉ số và ảnh Before."""
    member = _member_of(current_user, db)
    challenge = db.query(Challenge).filter(Challenge.id == data.challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Không tìm thấy thử thách")

    today = date.today()
    if today > challenge.end_date:
        raise HTTPException(status_code=400, detail="Thử thách đã kết thúc")

    existing = (
        db.query(ChallengeEntry)
        .filter(
            ChallengeEntry.challenge_id == challenge.id,
            ChallengeEntry.member_id == member.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Bạn đã đăng ký thử thách này rồi")

    participants = (
        db.query(func.count(ChallengeEntry.id))
        .filter(ChallengeEntry.challenge_id == challenge.id)
        .scalar()
        or 0
    )
    if participants >= challenge.max_participants:
        raise HTTPException(
            status_code=400,
            detail=f"Thử thách đã đủ {challenge.max_participants} người tham gia.",
        )

    entry = ChallengeEntry(
        challenge_id=challenge.id,
        member_id=member.id,
        start_weight_kg=data.start_weight_kg,
        start_body_fat=data.start_body_fat,
        start_muscle_kg=data.start_muscle_kg,
        before_photo_url=data.before_photo_url,
        status="active",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "message": (
            f"Đã đăng ký tham gia '{challenge.name}'! "
            f"Thử thách kéo dài đến {challenge.end_date}."
        ),
        "entry_id": entry.id,
        "challenge_name": challenge.name,
        "start_date": challenge.start_date,
        "end_date": challenge.end_date,
        "prize": challenge.prize_description,
        "guidance": [
            "Cập nhật ảnh Before ngay hôm nay để có mốc so sánh.",
            "Đo InBody đầu kỳ để có chỉ số chính xác.",
            "Dùng AI Coach để nhận phác đồ tập luyện và dinh dưỡng cho thử thách.",
            "Cập nhật tiến độ mỗi 2 tuần để ban tổ chức theo dõi.",
        ],
    }


@router.post("/challenges/{entry_id}/finalize")
def finalize_challenge_entry(
    entry_id: int,
    data: ChallengeFinalize,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nộp kết quả cuối kỳ: chỉ số After + ảnh After, hệ thống tính điểm."""
    entry = db.query(ChallengeEntry).filter(ChallengeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Không tìm thấy đăng ký thử thách")

    if entry.member_id != _member_of(current_user, db).id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền nộp kết quả này")

    entry.end_weight_kg = data.end_weight_kg
    entry.end_body_fat = data.end_body_fat
    entry.end_muscle_kg = data.end_muscle_kg
    entry.after_photo_url = data.after_photo_url

    # --- Tính điểm biến đổi hình thể ---
    score = 0.0
    breakdown: list[str] = []

    if entry.start_body_fat is not None and entry.end_body_fat is not None:
        fat_drop = entry.start_body_fat - entry.end_body_fat
        if fat_drop > 0:
            pts = fat_drop * 8
            score += pts
            breakdown.append(f"Giảm {round(fat_drop, 1)}% mỡ: +{round(pts)} điểm")

    if entry.start_muscle_kg is not None and entry.end_muscle_kg is not None:
        muscle_gain = entry.end_muscle_kg - entry.start_muscle_kg
        if muscle_gain > 0:
            pts = muscle_gain * 15
            score += pts
            breakdown.append(f"Tăng {round(muscle_gain, 1)}kg cơ: +{round(pts)} điểm")

    if entry.start_weight_kg is not None and entry.end_weight_kg is not None:
        weight_change = entry.start_weight_kg - entry.end_weight_kg
        # Chỉ cộng điểm khi giảm cân ở mức hợp lý (không khuyến khích sụt cân cực đoan)
        if 0 < weight_change <= entry.start_weight_kg * 0.15:
            pts = weight_change * 5
            score += pts
            breakdown.append(f"Giảm {round(weight_change, 1)}kg an toàn: +{round(pts)} điểm")

    entry.score = round(score, 1)
    entry.status = "completed"

    # Cộng điểm thưởng khi hoàn thành
    member = db.query(Member).filter(Member.id == entry.member_id).first()
    challenge = db.query(Challenge).filter(Challenge.id == entry.challenge_id).first()
    points = 0
    if member and challenge and challenge.reward_points:
        points = _award_points(
            member, challenge.reward_points, PointKind.CHALLENGE,
            f"Hoàn thành thử thách '{challenge.name}'", db,
        )

    db.commit()

    return {
        "message": (
            f"Đã nộp kết quả! Điểm biến đổi hình thể của bạn: {entry.score}"
            + (f" và nhận {points} điểm thưởng." if points else ".")
        ),
        "score": entry.score,
        "score_breakdown": breakdown,
        "points_awarded": points,
        "note": (
            "Ban tổ chức sẽ tổng hợp và công bố xếp hạng sau khi thử thách kết thúc. "
            "Điểm được tính theo mức giảm mỡ, tăng cơ và mức giảm cân an toàn."
        ),
    }


@router.get("/challenges/{challenge_id}/leaderboard")
def challenge_leaderboard(challenge_id: int, db: Session = Depends(get_db)):
    """Bảng xếp hạng thử thách."""
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Không tìm thấy thử thách")

    entries = (
        db.query(ChallengeEntry)
        .filter(ChallengeEntry.challenge_id == challenge_id)
        .order_by(ChallengeEntry.score.desc(), ChallengeEntry.votes.desc())
        .all()
    )

    # Gán thứ hạng
    for i, e in enumerate(entries, start=1):
        if e.status == "completed":
            e.rank = i
    db.commit()

    return {
        "challenge_name": challenge.name,
        "end_date": challenge.end_date,
        "prize": challenge.prize_description,
        "total_entries": len(entries),
        "completed_entries": sum(1 for e in entries if e.status == "completed"),
        "entries": [
            {
                "rank": e.rank,
                "member_name": e.member.full_name if e.member else None,
                "score": e.score,
                "fat_change": round((e.start_body_fat or 0) - (e.end_body_fat or 0), 1)
                if e.start_body_fat and e.end_body_fat else None,
                "muscle_change": round((e.end_muscle_kg or 0) - (e.start_muscle_kg or 0), 1)
                if e.start_muscle_kg and e.end_muscle_kg else None,
                "before_photo": e.before_photo_url,
                "after_photo": e.after_photo_url,
                "status": e.status,
                "votes": e.votes,
            }
            for e in entries
        ],
    }


# ==========================================================================
# ĐIỂM THƯỞNG & ĐỔI QUÀ
# ==========================================================================
@router.get("/points/my")
def my_points(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Điểm thưởng và lịch sử tích/đổi điểm."""
    member = _member_of(current_user, db)
    history = (
        db.query(LoyaltyPoint)
        .filter(LoyaltyPoint.member_id == member.id)
        .order_by(LoyaltyPoint.created_at.desc())
        .limit(50)
        .all()
    )

    # Tổng hợp theo nguồn
    by_kind = (
        db.query(LoyaltyPoint.kind, func.sum(LoyaltyPoint.points))
        .filter(LoyaltyPoint.member_id == member.id)
        .group_by(LoyaltyPoint.kind)
        .all()
    )

    kind_labels = {
        "checkin": "Check-in tại phòng tập",
        "workout_goal": "Hoàn thành mục tiêu tuần",
        "referral": "Giới thiệu bạn bè",
        "challenge": "Thử thách",
        "purchase": "Mua hàng tại quầy",
        "redeem": "Đổi quà",
        "bonus": "Huy hiệu & thưởng",
    }

    return {
        "current_points": member.loyalty_points,
        "total_earned": member.total_points_earned,
        "points_value_note": (
            f"{member.loyalty_points or 0} điểm có thể đổi thành quà tại mục Đổi quà. "
            f"Quy đổi tham khảo: 10 điểm ≈ 10.000đ giá trị."
        ),
        "by_source": [
            {
                "kind": k,
                "label": kind_labels.get(k, k),
                "points": int(v or 0),
            }
            for k, v in by_kind
        ],
        "history": [
            {
                "points": h.points,
                "balance_after": h.balance_after,
                "kind": h.kind,
                "label": kind_labels.get(h.kind, h.kind),
                "note": h.note,
                "created_at": h.created_at,
            }
            for h in history
        ],
        "how_to_earn": [
            f"Check-in tại phòng tập: +{POINTS_CHECKIN} điểm/lượt",
            f"Hoàn thành mục tiêu tuần của AI Coach: +{POINTS_WEEKLY_GOAL} điểm",
            "Mua hàng tại quầy Pro-Shop: +1 điểm/10.000đ",
            f"Giới thiệu bạn bè đi tập: +{POINTS_REFERRAL} điểm",
            "Hoàn thành thử thách biến đổi hình thể: theo giải thưởng",
        ],
    }


@router.get("/rewards")
def list_rewards(db: Session = Depends(get_db)):
    """Danh mục quà có thể đổi bằng điểm."""
    rewards = db.query(Reward).filter(Reward.is_active == True).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "points_cost": r.points_cost,
            "kind": r.kind,
            "value_amount": r.value_amount,
            "stock": r.stock,
            "in_stock": r.stock == 0 or r.stock > 0,
        }
        for r in rewards
    ]


@router.post("/rewards")
def create_reward(
    data: RewardCreate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Admin tạo quà đổi điểm."""
    reward = Reward(**data.model_dump(), is_active=True)
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return {"message": f"Đã tạo quà '{reward.name}'", "reward_id": reward.id}


@router.post("/rewards/redeem")
def redeem_reward(
    data: RewardRedeem,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hội viên đổi điểm lấy quà."""
    member = _member_of(current_user, db)
    reward = db.query(Reward).filter(
        Reward.id == data.reward_id, Reward.is_active == True
    ).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Không tìm thấy quà")

    if (member.loyalty_points or 0) < reward.points_cost:
        shortage = reward.points_cost - (member.loyalty_points or 0)
        raise HTTPException(
            status_code=400,
            detail=f"Không đủ điểm. Bạn có {member.loyalty_points or 0} điểm, "
                   f"cần {reward.points_cost} điểm (thiếu {shortage} điểm).",
        )

    if reward.stock > 0:
        redeemed = (
            db.query(func.count(RewardRedemption.id))
            .filter(
                RewardRedemption.reward_id == reward.id,
                RewardRedemption.status != "cancelled",
            )
            .scalar()
            or 0
        )
        if redeemed >= reward.stock:
            raise HTTPException(status_code=400, detail="Quà này đã hết hàng")

    # Trừ điểm
    balance = _award_points(
        member, -reward.points_cost, PointKind.REDEEM, f"Đổi quà: {reward.name}", db
    )

    code = f"RW-{secrets.token_hex(3).upper()}"
    redemption = RewardRedemption(
        member_id=member.id,
        reward_id=reward.id,
        points_spent=reward.points_cost,
        status="pending",
        code=code,
    )
    db.add(redemption)
    db.commit()
    db.refresh(redemption)

    return {
        "message": (
            f"🎁 Đổi quà thành công! Bạn đã dùng {reward.points_cost} điểm để nhận "
            f"'{reward.name}'. Mã nhận quà: {code}"
        ),
        "redemption_id": redemption.id,
        "code": code,
        "reward_name": reward.name,
        "points_spent": reward.points_cost,
        "points_balance": balance,
        "how_to_claim": (
            "Đưa mã này cho lễ tân để nhận quà. Quà sẽ được trao trong vòng 24 giờ."
        ),
    }


@router.post("/rewards/redemptions/{redemption_id}/fulfill")
def fulfill_redemption(
    redemption_id: int,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Lễ tân xác nhận trao quà cho hội viên."""
    redemption = (
        db.query(RewardRedemption)
        .filter(RewardRedemption.id == redemption_id)
        .first()
    )
    if not redemption:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu đổi quà")
    if redemption.status == "fulfilled":
        raise HTTPException(status_code=400, detail="Phiếu này đã được trao rồi")

    redemption.status = "fulfilled"
    redemption.fulfilled_by = current_user.full_name or current_user.username
    redemption.fulfilled_at = now_local()
    db.commit()

    return {
        "message": (
            f"Đã trao quà '{redemption.reward.name if redemption.reward else ''}' "
            f"cho hội viên."
        ),
        "redemption_id": redemption.id,
        "status": redemption.status,
    }


# ==========================================================================
# GIỚI THIỆU BẠN BÈ
# ==========================================================================
@router.post("/referrals")
def create_referral(
    data: ReferralCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hội viên giới thiệu bạn bè — nhận điểm khi người được giới thiệu chốt gói."""
    member = _member_of(current_user, db)

    existing = (
        db.query(Referral)
        .filter(
            Referral.referrer_member_id == member.id,
            Referral.referred_phone == data.referred_phone.strip(),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Bạn đã giới thiệu số điện thoại này rồi"
        )

    code = f"REF-{member.id}-{secrets.token_hex(3).upper()}"

    referral = Referral(
        referrer_member_id=member.id,
        referred_name=data.referred_name.strip(),
        referred_phone=data.referred_phone.strip(),
        referral_code=code,
        status="pending",
    )
    db.add(referral)
    db.commit()
    db.refresh(referral)

    return {
        "message": (
            f"Đã ghi nhận giới thiệu {referral.referred_name}. "
            f"Khi người này chốt gói tập, bạn sẽ nhận {POINTS_REFERRAL} điểm thưởng."
        ),
        "referral_id": referral.id,
        "referral_code": code,
        "reward_points": POINTS_REFERRAL,
        "share_message": (
            f"Mình đang tập ở HealthyGym và thấy rất hiệu quả! Bạn thử ghé tập miễn phí "
            f"7 ngày nhé. Nhắc mã giới thiệu của mình: {code}"
        ),
    }


@router.get("/referrals/my")
def my_referrals(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Danh sách bạn bè đã giới thiệu."""
    member = _member_of(current_user, db)
    referrals = (
        db.query(Referral)
        .filter(Referral.referrer_member_id == member.id)
        .order_by(Referral.created_at.desc())
        .all()
    )
    return {
        "total_referrals": len(referrals),
        "converted": sum(1 for r in referrals if r.status == "converted"),
        "points_earned": sum(r.points_awarded or 0 for r in referrals),
        "points_per_conversion": POINTS_REFERRAL,
        "referrals": [
            {
                "id": r.id,
                "referred_name": r.referred_name,
                "referred_phone": r.referred_phone,
                "referral_code": r.referral_code,
                "status": r.status,
                "points_awarded": r.points_awarded,
                "created_at": r.created_at,
                "converted_at": r.converted_at,
            }
            for r in referrals
        ],
    }


# ==========================================================================
# CRM: PHÁT HIỆN RỦI RO RỜI BỎ & NHẮC GIA HẠN
# ==========================================================================
@router.post("/churn/scan")
def scan_churn_risk(
    current_user: User = Depends(require_operations), db: Session = Depends(get_db)
):
    """Quét hàng ngày: phát hiện hội viên có nguy cơ bỏ cuộc (Sleeping Members).

    Mốc 7 ngày  -> AI Coach gửi tin nhắn hỏi thăm + đề xuất bài tập nhẹ
    Mốc 14 ngày -> Tạo task cho Sale/CSKH gọi điện
    Mốc 30 ngày -> Task ưu tiên cao + đề xuất bảo lưu gói
    """
    today = date.today()
    members = (
        db.query(Member)
        .filter(
            Member.status == "active",
            Member.expire_date >= today,
        )
        .all()
    )

    created_tasks = 0
    escalated = 0
    snapshots = 0
    critical_members: list[dict] = []

    for member in members:
        last_visit = member.last_visit_date

        if not last_visit:
            # Chưa từng tập: tính từ ngày tham gia
            days_since = (today - member.join_date).days if member.join_date else 0
        else:
            days_since = (today - last_visit).days

        visits_30d = (
            db.query(func.count(GateCheckin.id))
            .filter(
                GateCheckin.member_id == member.id,
                GateCheckin.result == GateResult.GRANTED,
                GateCheckin.checkin_time >= datetime.combine(
                    today - timedelta(days=30), datetime.min.time()
                ),
            )
            .scalar()
            or 0
        )

        # --- Tính điểm rủi ro 0-100 ---
        risk_score = 0.0
        factors: list[str] = []

        if days_since >= 30:
            risk_score += 50
            factors.append(f"Không đến tập {days_since} ngày")
        elif days_since >= 14:
            risk_score += 32
            factors.append(f"Không đến tập {days_since} ngày")
        elif days_since >= 7:
            risk_score += 18
            factors.append(f"Không đến tập {days_since} ngày")

        if visits_30d == 0:
            risk_score += 20
            factors.append("Không có buổi tập nào trong 30 ngày qua")
        elif visits_30d <= 3:
            risk_score += 10
            factors.append(f"Chỉ tập {visits_30d} buổi trong 30 ngày")

        days_to_expiry = (member.expire_date - today).days if member.expire_date else 0
        if days_to_expiry <= 7:
            risk_score += 15
            factors.append(f"Thẻ sắp hết hạn ({days_to_expiry} ngày)")

        if member.is_debt_blocked:
            risk_score += 25
            factors.append("Đang có công nợ quá hạn")

        streak = db.query(MemberStreak).filter(
            MemberStreak.member_id == member.id
        ).first()
        if streak and (streak.current_week_streak or 0) == 0 and visits_30d > 0:
            risk_score += 8
            factors.append("Đã đứt chuỗi tập luyện")

        risk_score = min(100.0, risk_score)

        if risk_score >= 70:
            level = "critical"
        elif risk_score >= 45:
            level = "high"
        elif risk_score >= 25:
            level = "medium"
        else:
            level = "low"

        member.risk_level = level

        # --- Ghi snapshot ---
        existing_snapshot = (
            db.query(ChurnRiskSnapshot)
            .filter(
                ChurnRiskSnapshot.member_id == member.id,
                ChurnRiskSnapshot.snapshot_date == today,
            )
            .first()
        )
        if existing_snapshot:
            existing_snapshot.days_since_last_visit = days_since
            existing_snapshot.visits_last_30d = visits_30d
            existing_snapshot.risk_score = risk_score
            existing_snapshot.risk_level = level
            existing_snapshot.factors_json = json.dumps(factors, ensure_ascii=False)
        else:
            db.add(ChurnRiskSnapshot(
                member_id=member.id,
                snapshot_date=today,
                days_since_last_visit=days_since,
                visits_last_30d=visits_30d,
                risk_score=risk_score,
                risk_level=level,
                factors_json=json.dumps(factors, ensure_ascii=False),
            ))
            snapshots += 1

        # --- Tạo task chăm sóc theo mốc ---
        task_kind = None
        priority = "medium"
        title = ""
        detail = ""
        action = ""

        if days_since >= 30:
            task_kind = "sleeping_30d"
            priority = "high"
            title = f"Hội viên vắng mặt {days_since} ngày — nguy cơ bỏ cuộc cao"
            detail = (
                f"{member.full_name} không đến tập {days_since} ngày. "
                f"Thẻ còn {days_to_expiry} ngày. Yếu tố: {'; '.join(factors)}"
            )
            action = (
                "Gọi điện trực tiếp. Hỏi thăm xem hội viên gặp khó khăn gì (thời gian, "
                "chấn thương, tài chính). Đề xuất phương án bảo lưu thẻ 30-60 ngày để giữ "
                "quan hệ, hoặc chuyển sang gói linh hoạt hơn."
            )
            if level == "critical":
                critical_members.append({
                    "member_id": member.id,
                    "full_name": member.full_name,
                    "phone": member.phone,
                    "days_absent": days_since,
                    "risk_score": risk_score,
                })

        elif days_since >= 14:
            task_kind = "sleeping_14d"
            priority = "high"
            title = f"Hội viên vắng mặt {days_since} ngày — cần gọi điện"
            detail = (
                f"{member.full_name} không đến tập {days_since} ngày. "
                f"Yếu tố: {'; '.join(factors)}"
            )
            action = (
                "Gọi điện hỏi thăm trong 24 giờ. Kiểm tra xem hội viên có gặp chấn thương "
                "hoặc bận việc cần hỗ trợ bảo lưu gói tập không."
            )

        elif days_since >= 7:
            task_kind = "sleeping_7d"
            priority = "medium"
            title = f"Hội viên vắng mặt {days_since} ngày — gửi tin nhắn động viên"
            detail = f"{member.full_name} không đến tập {days_since} ngày."
            action = (
                "Gửi tin nhắn qua Zalo/SMS với giọng động viên, không trách móc. "
                "Đính kèm bài tập ngắn 20 phút tại nhà và đề xuất giảm nhẹ cường độ "
                "lịch tập để hội viên dễ quay lại."
            )

        if task_kind:
            existing_task = (
                db.query(RetentionTask)
                .filter(
                    RetentionTask.member_id == member.id,
                    RetentionTask.kind == task_kind,
                    RetentionTask.status.in_(["open", "in_progress"]),
                )
                .first()
            )
            if not existing_task:
                db.add(RetentionTask(
                    member_id=member.id,
                    kind=task_kind,
                    priority=priority,
                    title=title,
                    detail=detail,
                    suggested_action=action,
                    assigned_to="CSKH",
                    status="open",
                ))
                created_tasks += 1
            elif existing_task.priority != priority:
                existing_task.priority = priority
                escalated += 1

    db.commit()

    return {
        "message": (
            f"Đã quét {len(members)} hội viên. Phát hiện {created_tasks} trường hợp "
            f"cần chăm sóc, trong đó {len(critical_members)} trường hợp nghiêm trọng."
        ),
        "scanned": len(members),
        "tasks_created": created_tasks,
        "tasks_escalated": escalated,
        "snapshots_recorded": snapshots,
        "critical_members": critical_members,
        "thresholds": {
            "7_days": "AI Coach gửi tin nhắn hỏi thăm + bài tập nhẹ tại nhà",
            "14_days": "Tạo task cho Sale/CSKH gọi điện",
            "30_days": "Task ưu tiên cao + đề xuất bảo lưu gói",
        },
    }


@router.get("/retention/tasks")
def list_retention_tasks(
    status: Optional[str] = Query(None, pattern="^(open|in_progress|done|dismissed)$"),
    priority: Optional[str] = Query(None, pattern="^(low|medium|high)$"),
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Danh sách task chăm sóc hội viên cho Sale/CSKH."""
    query = db.query(RetentionTask)
    if status:
        query = query.filter(RetentionTask.status == status)
    if priority:
        query = query.filter(RetentionTask.priority == priority)

    tasks = (
        query.order_by(
            RetentionTask.priority.desc(),
            RetentionTask.created_at.desc(),
        )
        .limit(200)
        .all()
    )

    open_count = db.query(func.count(RetentionTask.id)).filter(
        RetentionTask.status == "open"
    ).scalar() or 0

    return {
        "total": len(tasks),
        "open_tasks": open_count,
        "tasks": [
            {
                "id": t.id,
                "member_id": t.member_id,
                "member_name": t.member.full_name if t.member else None,
                "member_phone": t.member.phone if t.member else None,
                "kind": t.kind,
                "priority": t.priority,
                "title": t.title,
                "detail": t.detail,
                "suggested_action": t.suggested_action,
                "assigned_to": t.assigned_to,
                "status": t.status,
                "due_date": t.due_date,
                "created_at": t.created_at,
                "outcome": t.outcome,
            }
            for t in tasks
        ],
    }


@router.put("/retention/tasks/{task_id}")
def update_retention_task(
    task_id: int,
    data: RetentionTaskUpdate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Cập nhật task chăm sóc (Sale ghi lại kết quả xử lý)."""
    task = db.query(RetentionTask).filter(RetentionTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy task")

    if data.status:
        task.status = data.status
        if data.status in ("done", "dismissed"):
            task.resolved_at = now_local()
    if data.assigned_to is not None:
        task.assigned_to = data.assigned_to
    if data.outcome is not None:
        task.outcome = data.outcome

    db.commit()

    return {
        "message": f"Đã cập nhật task #{task.id} sang trạng thái '{task.status}'",
        "task_id": task.id,
        "status": task.status,
    }


@router.post("/renewal/create-offers")
def create_renewal_offers(
    current_user: User = Depends(require_operations), db: Session = Depends(get_db)
):
    """Tạo nhắc gia hạn tự động tại các mốc 30/14/7/3 ngày trước khi hết hạn."""
    today = date.today()
    milestones = [30, 14, 7, 3]

    created = 0
    offers: list[dict] = []

    contracts = (
        db.query(MembershipContract)
        .filter(
            MembershipContract.status == ContractStatus.ACTIVE,
            MembershipContract.end_date >= today,
        )
        .all()
    )

    for contract in contracts:
        days_left = (contract.end_date - today).days

        for milestone in milestones:
            # Tạo offer khi đã bước vào mốc (days_left <= milestone)
            if days_left > milestone:
                continue

            existing = (
                db.query(RenewalReminder)
                .filter(
                    RenewalReminder.contract_id == contract.id,
                    RenewalReminder.days_before_expiry == milestone,
                )
                .first()
            )
            if existing:
                continue

            # Ưu đãi Early Bird: càng sớm càng cao
            discount = {30: 15, 14: 10, 7: 5, 3: 0}[milestone]
            member = contract.member

            offer = RenewalReminder(
                member_id=contract.member_id,
                contract_id=contract.id,
                days_before_expiry=milestone,
                discount_percent=discount,
                channel="in_app",
                offer_text=(
                    f"Ưu đãi gia hạn sớm: giảm {discount}% khi gia hạn trước khi thẻ hết hạn "
                    f"({contract.end_date}). Chỉ còn {days_left} ngày!"
                    if discount > 0 else
                    f"Thẻ của bạn sẽ hết hạn sau {days_left} ngày. Gia hạn ngay để "
                    f"không gián đoạn tập luyện!"
                ),
                status="pending",
            )
            db.add(offer)
            created += 1

            offers.append({
                "member_name": member.full_name if member else None,
                "phone": member.phone if member else None,
                "end_date": contract.end_date,
                "days_left": days_left,
                "milestone": milestone,
                "discount_percent": discount,
                "offer_text": offer.offer_text,
            })

    db.commit()

    # Sắp xếp theo mức độ khẩn cấp
    offers.sort(key=lambda x: x["days_left"])

    return {
        "message": (
            f"Đã tạo {created} nhắc gia hạn. "
            f"{len(offers)} hội viên đang trong giai đoạn cần nhắc."
        ),
        "created": created,
        "total_contracts_expiring": len(contracts),
        "offers": offers,
        "early_bird_policy": (
            "Gia hạn sớm 30 ngày: giảm 15% · 14 ngày: giảm 10% · "
            "7 ngày: giảm 5% · dưới 3 ngày: không giảm"
        ),
    }


@router.get("/churn/report")
def churn_report(
    current_user: User = Depends(require_operations), db: Session = Depends(get_db)
):
    """Báo cáo rủi ro rời bỏ & tỷ lệ giữ chân (Retention / Churn Rate)."""
    today = date.today()

    latest_snapshot_date = (
        db.query(func.max(ChurnRiskSnapshot.snapshot_date)).scalar()
    )
    rows = (
        db.query(ChurnRiskSnapshot)
        .filter(ChurnRiskSnapshot.snapshot_date == latest_snapshot_date)
        .all()
        if latest_snapshot_date else []
    )

    by_level: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for r in rows:
        by_level[r.risk_level] = by_level.get(r.risk_level, 0) + 1

    total_members = db.query(func.count(Member.id)).scalar() or 0
    active_members = (
        db.query(func.count(Member.id)).filter(Member.status == "active").scalar() or 0
    )

    # Tỷ lệ gia hạn: hội viên có >= 2 hợp đồng / tổng hội viên có hợp đồng
    members_with_contracts = (
        db.query(func.count(func.distinct(MembershipContract.member_id))).scalar() or 0
    )
    renewed_members = (
        db.query(func.count(func.distinct(MembershipContract.member_id)))
        .filter(MembershipContract.is_renewal == True)
        .scalar()
        or 0
    )
    retention_rate = (
        round(renewed_members / members_with_contracts * 100, 1)
        if members_with_contracts else 0.0
    )

    # Hội viên hết hạn không gia hạn trong 60 ngày -> coi như churned
    churned = (
        db.query(func.count(Member.id))
        .filter(
            Member.expire_date < today - timedelta(days=60),
            Member.status.in_(["expired", "inactive"]),
        )
        .scalar()
        or 0
    )
    churn_rate = round(churned / total_members * 100, 1) if total_members else 0.0

    return {
        "snapshot_date": latest_snapshot_date,
        "total_members": total_members,
        "active_members": active_members,
        "risk_distribution": by_level,
        "at_risk_total": by_level["high"] + by_level["critical"],
        "retention_rate": retention_rate,
        "churn_rate": churn_rate,
        "renewed_members": renewed_members,
        "churned_members": churned,
        "interpretation": (
            f"Tỷ lệ gia hạn {retention_rate}% — "
            + (
                "rất tốt, cao hơn mức trung bình ngành (khoảng 60-70%)."
                if retention_rate >= 75 else
                "khá tốt, ngang mức trung bình ngành."
                if retention_rate >= 60 else
                "cần cải thiện. Hãy tập trung vào luồng chăm sóc hội viên ở mốc 7 và 14 ngày."
            )
        ),
        "top_risk_members": [
            {
                "member_id": r.member_id,
                "member_name": r.member.full_name if r.member else None,
                "phone": r.member.phone if r.member else None,
                "days_since_last_visit": r.days_since_last_visit,
                "visits_last_30d": r.visits_last_30d,
                "risk_score": r.risk_score,
                "risk_level": r.risk_level,
                "factors": json.loads(r.factors_json) if r.factors_json else [],
            }
            for r in sorted(rows, key=lambda x: x.risk_score, reverse=True)[:20]
        ],
        "recommendation": (
            "Chạy quét rủi ro hàng ngày bằng POST /engagement/churn/scan để luôn có "
            "dữ liệu mới nhất. Tạo nhắc gia hạn bằng POST /engagement/renewal/create-offers."
        ),
    }