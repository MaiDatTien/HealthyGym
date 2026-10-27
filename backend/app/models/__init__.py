from app.models.user import User, Member, Trainer
from app.models.listing import Branch, Facility, MembershipPlan, GymClass, Article
from app.models.interaction import Voucher, Order, Booking, CheckInLog, Feedback, now_local
from app.models.chat import ChatMessage
from app.models.ai import (
    HealthMetric, AIPlan, WorkoutLog, DailyCheckin,
    PARQScreening, InBodyRecord, WeeklyCheckin, ChecklistItem,
)
from app.models.pt import TrainerSlot, PTBooking, CoachNote, EquipmentMaintenance
from app.models.membership import (
    MembershipContract, FreezeRequest, TransferRequest, UpgradeRequest,
    Installment, Lead, TrialPass, MemberWallet, WalletTransaction,
    ContractStatus, TierLevel, TimeWindow, LeadStage, PaymentStatus,
)
from app.models.operations import (
    ClassSchedule, ClassSpot, ClassBooking, ClassWaitlist, BookingPenalty,
    DynamicQRToken, GateCheckin, Locker, LockerAssignment,
    Product, InventoryTransaction, PosOrder, PosOrderItem,
    ScheduleStatus, BookingStatus, GateResult,
)
from app.models.trainer_ops import (
    PTPackage, PTPackagePurchase, TrainerShift, PTBurnConfirmation,
    TrainerChangeRequest, TrainerPayroll, PackageStatus, SessionOutcome,
)
from app.models.engagement import (
    MemberStreak, Badge, MemberBadge, Challenge, ChallengeEntry,
    LoyaltyPoint, Reward, RewardRedemption, Referral,
    RetentionTask, ChurnRiskSnapshot, RenewalReminder, MachineQR, PointKind,
)

__all__ = [
    # Người dùng & hội viên
    "User", "Member", "Trainer",
    # Danh mục cơ sở
    "Branch", "Facility", "MembershipPlan", "GymClass", "Article",
    # Tương tác
    "Voucher", "Order", "Booking", "CheckInLog", "Feedback", "now_local",
    "ChatMessage",
    # AI & sức khỏe
    "HealthMetric", "AIPlan", "WorkoutLog", "DailyCheckin",
    "PARQScreening", "InBodyRecord", "WeeklyCheckin", "ChecklistItem",
    # PT nội bộ
    "TrainerSlot", "PTBooking", "CoachNote", "EquipmentMaintenance",
    # Vòng đời hợp đồng
    "MembershipContract", "FreezeRequest", "TransferRequest", "UpgradeRequest",
    "Installment", "Lead", "TrialPass", "MemberWallet", "WalletTransaction",
    "ContractStatus", "TierLevel", "TimeWindow", "LeadStage", "PaymentStatus",
    # Vận hành
    "ClassSchedule", "ClassSpot", "ClassBooking", "ClassWaitlist", "BookingPenalty",
    "DynamicQRToken", "GateCheckin", "Locker", "LockerAssignment",
    "Product", "InventoryTransaction", "PosOrder", "PosOrderItem",
    "ScheduleStatus", "BookingStatus", "GateResult",
    # Nghiệp vụ PT
    "PTPackage", "PTPackagePurchase", "TrainerShift", "PTBurnConfirmation",
    "TrainerChangeRequest", "TrainerPayroll", "PackageStatus", "SessionOutcome",
    # Gamification & CRM
    "MemberStreak", "Badge", "MemberBadge", "Challenge", "ChallengeEntry",
    "LoyaltyPoint", "Reward", "RewardRedemption", "Referral",
    "RetentionTask", "ChurnRiskSnapshot", "RenewalReminder", "MachineQR", "PointKind",
]