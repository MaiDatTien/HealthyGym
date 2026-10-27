# Smart AI Gym Platform — Tài liệu Kiến trúc & Nghiệp vụ

Hệ thống Website Quản lý Phòng Gym & Huấn luyện viên AI Thông minh
(**All-in-One Smart Gym ERP & AI Fitness Coach**, v3.0.0).
Toàn bộ số liệu trong tài liệu này được đối chiếu trực tiếp với cơ sở dữ liệu và API đang chạy.

---

## I. SƠ ĐỒ KIẾN TRÚC HỆ THỐNG

```
┌──────────────────────────────────────────────────────────────────────┐
│                         NGƯỜI DÙNG (6 vai trò)                        │
│  Guest   Member   PT/Coach   Receptionist   Facility Mgr   Admin     │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼─────────────────────────────────────────┐
│  FRONTEND — Next.js 15 (App Router) + React 18 + TypeScript          │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ 24 trang: AI Coach · AI Chuyên sâu · Tiến độ · PT 1-1 · Coach  │  │
│  │ Lễ tân · Khách tập thử · POS · Hợp đồng · Điểm&Quà · GroupX    │  │
│  │ CSVC · Thiết bị · Admin ...                                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  Theme: trắng + xanh biển (#0b6e8f) + kim (#b8860b) — góc VUÔNG     │
│  Font: IBM Plex Sans + IBM Plex Mono (số liệu)                       │
│  Biểu đồ: SVG thuần (không phụ thuộc thư viện ngoài)                 │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ REST / JSON  (JWT Bearer)
┌────────────────────────────▼─────────────────────────────────────────┐
│  BACKEND — FastAPI + SQLAlchemy 2 + Pydantic 2                       │
│                                                                       │
│  ┌─────────────── ROUTERS (API LAYER — 178 endpoints) ───────────────┐│
│  │ /auth  /listings  /search  /interactions  /chat  /recommendations ││
│  │ /admin                  → CRUD, báo cáo, quản lý hội viên          ││
│  │ /ai                     → AI Smart Fitness Coach (4 bước)          ││
│  │ /ai-plus                → PAR-Q+, InBody, chu kỳ hóa, dinh dưỡng+  ││
│  │ /progress               → Theo dõi tiến độ & nhật ký               ││
│  │ /pt                     → PT 1-1, Coach Dashboard, QR, bảo trì     ││
│  │ /pt-ops                 → Gói buổi tập, ca dạy, xác nhận kép, lương││
│  │ /memberships            → Vòng đời hợp đồng, leads, tập thử, ví    ││
│  │ /groupx                 → Lớp nhóm, chọn vị trí, danh sách chờ     ││
│  │ /gym-ops                → QR cổng, tủ đồ & khăn, POS Pro-Shop      ││
│  │ /engagement             → Streak, huy hiệu, thử thách, churn       ││
│  │ /equipment              → QR máy, vòng đời bảo trì, đồng bộ AI     ││
│  └───────────────────────┬───────────────────────────────────────────┘│
│                          │                                            │
│  ┌───────────────────────▼──── SERVICES (AI ENGINE) ─────────────┐   │
│  │ ai_diagnosis.py      Bước 2: BMI→LBM→BMR→TDEE→FFMI→tạng người │   │
│  │ ai_workout.py        Bước 3: Split, thư viện 45+ bài tập      │   │
│  │ ai_nutrition.py      Bước 4: Macros, thực đơn Việt, phục hồi  │   │
│  │ ai_coach.py          Điều phối 4 bước + System Instruction    │   │
│  │ ai_screening.py      PAR-Q+ & quy tắc cứng an toàn y tế       │   │
│  │ ai_inbody.py         InBody: SMM, mỡ nội tạng, dạng C-I-D     │   │
│  │ ai_periodization.py  1RM, tăng tiến, deload, đổi bài tức thì  │   │
│  │ ai_nutrition_plus.py Đổi món, carb cycling, bù cheat meal     │   │
│  │ llm.py               Cầu nối LLM (tuỳ chọn) + fallback tự động│   │
│  └───────────────────────────────────────────────────────────────┘   │
│  ┌───────────── SECURITY ─────────────┐  ┌────── MIGRATIONS ──────┐  │
│  │ JWT HS256 · RBAC 6 vai trò         │  │ migrations.py          │  │
│  │ hash SHA-256 + salt · optional auth│  │ ALTER TABLE idempotent │  │
│  └────────────────────────────────────┘  └────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ SQLAlchemy ORM
┌────────────────────────────▼─────────────────────────────────────────┐
│  DATABASE — PostgreSQL 18 (healthygym) — 67 bảng                     │
└──────────────────────────────────────────────────────────────────────┘
```

### Luồng dữ liệu AI Smart Coach (4 bước)

```
BƯỚC 1              BƯỚC 2                BƯỚC 3              BƯỚC 4
Thu thập       →    Chẩn đoán        →    Lịch tập       →    Dinh dưỡng
12 câu hỏi          BMI, LBM,             Chọn Split          Macros
(wizard/chat)       BMR, TDEE,            theo số buổi        Thực đơn Việt
                    FFMI, tạng người      thư viện bài tập    Phục hồi
      │                   │                     │                   │
      └───────────────────┴─────────────────────┴───────────────────┘
                                  ▼
              JSON có cấu trúc → Frontend render biểu đồ + bảng
                                  ▼
                 Lưu HealthMetrics + AIPlans (nếu đã đăng nhập)
```

---

## II. THIẾT KẾ CƠ SỞ DỮ LIỆU (ERD)

### Sơ đồ quan hệ

```
                    ┌──────────┐
                    │  users   │  (RBAC: admin/staff/trainer/member)
                    └────┬─────┘
                         │ 1-1
                    ┌────▼─────┐        ┌──────────────┐
                    │ members  │◄───────┤trainers      │
                    │          │ N-1    │(user_id 1-1) │
                    └────┬─────┘trainer_id└──────┬───────┘
                         │                       │
        ┌────────────────┼───────────────┐       │
        │                │               │       │
   ┌────▼──────────┐ ┌───▼────────┐ ┌────▼────┐  │
   │health_metrics │ │  ai_plans  │ │workout_ │  │
   │  (23 cột)     │ │ (25 cột)   │ │  logs   │  │
   └────┬──────────┘ └───┬────────┘ │(15 cột) │  │
        │  1-N            │ 1-N      └─────────┘  │
        └────────────►(metric_id)                 │
                         │                        │
                    ┌────▼─────────┐              │
                    │daily_checkins│              │
                    │  (14 cột)    │              │
                    └──────────────┘              │
                                                  │
   ┌──────────────────┬────────────────┬──────────┴────────┐
   │                  │                │                   │
┌──▼──────────┐ ┌─────▼──────┐ ┌───────▼──────┐ ┌──────────▼────────┐
│trainer_slots│ │pt_bookings │ │ coach_notes  │ │equipment_maintenance│
│  (7 cột)    │ │  (9 cột)   │ │  (8 cột)     │ │     (10 cột)        │
└─────────────┘ └────────────┘ └──────────────┘ └──────────┬──────────┘
   (slot_id 1-1)                                            │ N-1
                                                        ┌───▼──────┐
   ┌─────────────┐ ┌─────────────┐ ┌──────────┐         │facilities│
   │membership_  │ │  branches   │ │gym_classes│◄────────┤          │
   │   plans     │ │             │ │          │         └──────────┘
   └──────┬──────┘ └──────┬──────┘ └────┬─────┘
          │               │             │
     ┌────▼────┐     ┌────▼────┐   ┌────▼────┐
     │ orders  │     │bookings │   │ articles│
     └─────────┘     └─────────┘   └─────────┘
```

### Chi tiết bảng lõi phân hệ AI

#### `health_metrics` — Chỉ số cơ thể theo từng lần đo (23 cột)

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | INTEGER PK | |
| `member_id` | FK → members | Hội viên sở hữu |
| `measured_at` | DATE | Ngày đo (dùng làm trục X biểu đồ) |
| `height_cm`, `weight_kg` | FLOAT | Chỉ số bắt buộc |
| `body_fat_percentage` | FLOAT | **Chỉ số then chốt** cho Katch-McArdle |
| `age`, `gender` | INTEGER, VARCHAR | Phân loại theo giới tính + độ tuổi |
| `muscle_mass_kg` | FLOAT | Khối cơ (từ InBody) |
| `visceral_fat_level` | FLOAT | Mỡ nội tạng |
| `waist_cm`, `neck_cm`, `hip_cm` | FLOAT | Số đo thước dây (US Navy Method) |
| `body_water_kg` | FLOAT | Lượng nước cơ thể |
| `bmi`, `lean_body_mass_kg`, `fat_mass_kg` | FLOAT | **Kết quả engine tính sẵn** |
| `bmr_kcal`, `tdee_kcal` | FLOAT | Nhu cầu năng lượng |
| `body_type_classification` | VARCHAR(150) | Tạng người (Skinny Fat / Obese / …) |
| `source` | VARCHAR(50) | `inbody` / `manual` / `ai_coach` / `staff` |

> Kết quả tính toán được **lưu sẵn** thay vì tính lại mỗi lần đọc, giúp biểu đồ tiến độ
> hiển thị đúng giá trị tại thời điểm đo (Body Fat thay đổi thì BMR cũng phải thay đổi theo).

#### `ai_plans` — Phác đồ AI hoàn chỉnh (25 cột)

| Nhóm | Cột | Ý nghĩa |
|---|---|---|
| Đầu vào | `goal`, `activity_level`, `training_days_per_week`, `session_minutes`, `training_location` | Lựa chọn của hội viên |
| An toàn | `injuries`, `allergies` | CSV — dùng để loại bài tập và thay thực phẩm |
| Kết quả phẳng | `split_type`, `target_daily_calories`, `caloric_adjustment`, `protein_grams`, `carbs_grams`, `fat_grams`, `daily_water_liters`, `estimated_weeks_to_goal` | Cột phẳng để query/thống kê nhanh |
| JSON | `diagnosis_json`, `nutrition_json`, `workout_json`, `recovery_json` | Toàn bộ phác đồ để render |
| Trạng thái | `is_active` | Chỉ giữ **1 phác đồ active** mỗi hội viên |

> Thiết kế **cột phẳng + JSON**: cột phẳng cho Admin thống kê (`GROUP BY goal`),
> JSON cho frontend render bảng biểu phức tạp mà không cần join nhiều bảng.

#### Các bảng còn lại

| Bảng | Cột | Vai trò |
|---|---|---|
| `workout_logs` | 15 | Nhật ký từng hiệp tập → Progressive Overload |
| `daily_checkins` | 14 | Calo/đạm/nước/giấc ngủ/bước chân theo ngày |
| `trainer_slots` | 7 | Khung giờ trống của PT (Real-time Slot) |
| `pt_bookings` | 9 | Lịch 1-1, có `slot_id` UNIQUE chống trùng |
| `coach_notes` | 8 | HLV đánh giá học viên sau buổi tập |
| `equipment_maintenance` | 10 | Phiếu bảo trì thiết bị + chi phí |

### Migration

`create_all()` chỉ tạo bảng mới, **không thêm cột vào bảng đã tồn tại**. Module
`app/migrations.py` bổ sung cột còn thiếu bằng `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
(idempotent, hỗ trợ cả PostgreSQL và SQLite) nên nâng cấp bản cài đặt cũ không mất dữ liệu.

---

## III. DANH SÁCH API ENDPOINTS

Base URL: `http://127.0.0.1:8000` · Tài liệu tương tác: `/docs`

### AI Smart Fitness Coach — `/ai`

| Method | Endpoint | Quyền | Mô tả |
|---|---|---|---|
| GET | `/ai/onboarding` | Public | 12 câu hỏi wizard theo từng bước |
| GET | `/ai/options` | Public | Danh mục mục tiêu, mức vận động, chấn thương, dị ứng |
| GET | `/ai/system-instruction` | Public | System Instruction để nhúng vào LLM API |
| POST | `/ai/estimate-body-fat` | Public | **US Navy Method** — ước tính BF% từ số đo vòng |
| POST | `/ai/diagnose` | Public | **Bước 2** — Chẩn đoán thể trạng (guest dùng thử) |
| POST | `/ai/quick-calc` | Public | Tính nhanh TDEE & Body Fat cho trang chủ |
| POST | `/ai/plan` | Optional auth | **Bước 3+4** — Phác đồ đầy đủ; tự lưu nếu đã đăng nhập |
| GET | `/ai/plan/my` | Member | Phác đồ đang áp dụng |
| GET | `/ai/plan/history` | Member | Lịch sử phác đồ |
| POST | `/ai/chat` | Public | Hội thoại theo Conversational Flow |

### Theo dõi tiến độ — `/progress`

| Method | Endpoint | Quyền | Mô tả |
|---|---|---|---|
| POST | `/progress/metrics` | Member | Ghi chỉ số cơ thể mới |
| GET | `/progress/metrics` | Member | Lịch sử chỉ số |
| GET | `/progress/charts` | Member | Dữ liệu biểu đồ + delta + mục tiêu |
| GET | `/progress/summary` | Member | Tổng quan + mức tuân thủ 30 ngày |
| POST | `/progress/workout-logs` | Member | Ghi nhật ký tập + gợi ý tăng tiến |
| GET | `/progress/workout-logs` | Member | Lịch sử tập luyện |
| GET | `/progress/workout-logs/personal-records` | Member | Kỷ lục cá nhân (PR) |
| GET | `/progress/workout-logs/progress/{exercise}` | Member | Tiến bộ mức tạ theo thời gian |
| POST | `/progress/checkins` | Member | Nhật ký dinh dưỡng (upsert theo ngày) |
| GET | `/progress/checkins` · `/checkins/chart` | Member | Nhật ký & biểu đồ |

### PT 1-1, Coach & Vận hành — `/pt`

| Method | Endpoint | Quyền | Mô tả |
|---|---|---|---|
| GET | `/pt/trainers` | Public | HLV kèm rating, số khung giờ trống |
| GET | `/pt/slots` | Public | Khung giờ trống (Real-time Slot) |
| POST/DELETE | `/pt/slots` · `/slots/{id}` | Staff/Admin | Mở/xóa khung giờ dạy |
| POST | `/pt/bookings` | Member | Đặt lịch 1-1 (khóa `FOR UPDATE` chống trùng) |
| GET | `/pt/bookings/my` | Member | Lịch 1-1 của hội viên |
| POST | `/pt/bookings/{id}/cancel` | Member | Hủy lịch (trước 12 giờ) |
| POST | `/pt/bookings/{id}/feedback` | Member | Đánh giá PT |
| GET | `/pt/coach/overview` | **Trainer/Admin** | Tổng quan dashboard HLV |
| GET | `/pt/coach/trainees` | Trainer/Admin | Học viên + phác đồ AI |
| GET | `/pt/coach/trainees/{id}` | Trainer/Admin | Hồ sơ sức khỏe chi tiết |
| POST | `/pt/coach/notes` | Trainer/Admin | Đánh giá sau buổi tập |
| GET | `/pt/checkin/qr` | Member | Lấy mã QR check-in |
| POST | `/pt/checkin/scan` | Staff/Admin | Quét QR check-in (chống trùng 30 phút) |
| GET/POST/PUT | `/pt/equipment` · `/maintenance` | Staff/Admin | Thiết bị & bảo trì |

### Nghiệp vụ phòng gym (đã có sẵn, được mở rộng)

`/auth` (login, register, me) · `/listings` (plans, classes, trainers, branches, facilities, articles) ·
`/interactions` (free-trial, orders, bookings, freeze, checkin, feedbacks) · `/admin` (CRUD đầy đủ + reports) ·
`/search` · `/recommendations` · `/chat`

---

## IV. NGHIỆP VỤ AI COACH — CÔNG THỨC & NGƯỠNG

### Bước 2 — Chẩn đoán (đã kiểm chứng bằng test)

| Chỉ số | Công thức | Ví dụ (172cm, 75kg, 24.5% BF, nam 29t) |
|---|---|---|
| BMI | `W / H(m)²` | **25.35** |
| LBM | `W × (1 − BF%/100)` | **56.62 kg** |
| Fat Mass | `W − LBM` | **18.38 kg** |
| BMR | `370 + 21.6 × LBM` (Katch-McArdle) | **1.593 kcal** |
| TDEE | `BMR × hệ số` (moderate 1.55) | **2.469 kcal** |
| FFMI | `LBM / H(m)²` + chuẩn hóa | 19.63 → "Cơ bắp dưới trung bình" |

**Phân loại Body Fat** (coi mỗi nhóm trải liên tục tới ngay trước cận dưới của nhóm kế tiếp,
nhờ đó giá trị trong khe hở như 17.5% vẫn xếp đúng thay vì rơi xuống "Essential"):

- Nam: Essential 2–5% · Athletes 6–13% · Fitness 14–17% · Average 18–24% · **Obese ≥25%**
- Nữ: Essential 10–13% · Athletes 14–20% · Fitness 21–24% · Average 25–31% · **Obese ≥32%**
- Bù trừ tuổi: cộng ~1%/thập kỷ sau 30 tuổi

**Phát hiện Skinny Fat** (trọng tâm nghiệp vụ): BF ≥18% (nam) **VÀ**
(BMI < 27 **HOẶC** FFMI < 18) → ngoại hình bình thường nhưng mỡ cao, cơ thấp.

### Bước 3 — Lịch tập

| Số buổi/tuần | Split |
|---|---|
| 3 | Full Body |
| 4 | Upper / Lower |
| 5 | PPL + Upper/Lower |
| 6 | Push / Pull / Legs |

Thư viện **45+ bài tập** với trường `avoid_for` (chấn thương cần tránh) và `alternative`
(bài thay thế). Hệ thống tự thay/loại bài theo chấn thương **và** theo thiết bị tại nơi tập,
đồng thời khử trùng lặp khi nhiều bài gốc cùng trỏ về một bài thay thế.

### Bước 4 — Dinh dưỡng

| Mục tiêu | Điều chỉnh calo | Ghi chú |
|---|---|---|
| Cutting | TDEE −300…−500 | Sâu hơn nếu BF cao |
| Bulking | TDEE +200…+300 | Thấp hơn nếu BF ≥15% |
| Recomp | TDEE −100…−200 | |
| Endurance | TDEE | |

- **Protein**: 1.8–2.2 g/kg cân nặng **và** 2.2–2.5 g/kg LBM. Khi hai khoảng không giao nhau
  (người thừa mỡ nhiều), ưu tiên **sàn theo cân nặng** — thiếu đạm gây mất cơ là rủi ro lớn hơn.
- **Fat**: 25–27% calo, sàn 0.6 g/kg để bảo vệ hormone.
- **Carbs**: phần calo còn lại. Sàn an toàn: **không bao giờ dưới 1.200 kcal/ngày**.
- **Nước**: `W × 0.04 lít` + `500ml × giờ tập/tuần ÷ 7`.
- **Thực đơn**: 4–5 bữa, ~30 thực phẩm Việt Nam, tự thay thế theo 9 nhóm dị ứng.

### Tích hợp LLM (tuỳ chọn)

Chatbot hoạt động theo nguyên tắc **engine nội bộ là nguồn sự thật, LLM chỉ diễn giải**:

1. Engine nội bộ luôn chạy trước → các hành động nghiệp vụ (ước tính Body Fat, sinh phác đồ,
   tra cứu giá/lịch lớp) luôn chính xác và nhất quán.
2. Nếu đã cấu hình `LLM_API_KEY`, LLM được gọi kèm `SYSTEM_INSTRUCTION` (3.762 ký tự) **và**
   các chỉ số đã tính sẵn (BMI, LBM, BMR, TDEE, macros…). Prompt ghi rõ:
   *"dùng đúng số này, KHÔNG tự tính lại"* — nhờ đó con số LLM nói ra luôn khớp tuyệt đối với
   phác đồ đã lưu và biểu đồ tiến độ.
3. Nếu chưa cấu hình hoặc LLM lỗi/timeout → tự động rơi về engine rule-based.
   **Website không bao giờ phụ thuộc mạng để hoạt động.**

Cấu hình trong `backend/.env` (xem `.env.example`):

```env
LLM_PROVIDER=gemini          # gemini | openai
LLM_API_KEY=<api-key>
LLM_MODEL=gemini-2.0-flash   # tuỳ chọn
```

Chỉ dùng `urllib.request` từ thư viện chuẩn — **không cần cài thêm gói nào**.
Kiểm tra trạng thái: `GET /ai/system-instruction` trả về `llm_enabled`, `llm_provider`, `llm_model`.

---

## V. PHÂN QUYỀN (RBAC — 6 VAI TRÒ)

| Vai trò | Quyền chính |
|---|---|
| **Guest** | Trang chủ, gói tập, lịch lớp, HLV, chi nhánh, `/ai/*` (không lưu), `/ai-plus/parq/questions`, `/ai-plus/foods/list`, `/equipment/scan/{qr}`, `/memberships/trial/register` |
| **Member** | Toàn bộ AI Coach + `/ai-plus/*` (PAR-Q, InBody, đổi bài, đổi món, check-in tuần), `/progress/*`, `/pt/bookings`, xác nhận kép buổi tập, `/pt-ops/packages/my`, `/memberships/wallet/my`, `/engagement/*`, QR check-in |
| **Trainer (PT)** | `/pt/coach/*`, `/pt-ops/*` — gói buổi tập, ca dạy, xác nhận hoàn thành buổi, `/pt-ops/payroll/my` |
| **Receptionist / Staff** | `/memberships/leads`, `/memberships/debt/overdue`, `/gym-ops/*` (QR cổng, tủ đồ, POS), hợp đồng, bảo lưu/chuyển nhượng, `/pt-ops/payroll/generate` |
| **Facility Manager** | `/equipment/*` (vòng đời, bảo trì, mã QR máy), báo cáo tồn kho |
| **Admin** | Toàn quyền + CRUD + báo cáo doanh thu/churn |

Nhóm quyền được gom trong `security.py`:

- `OPERATIONS_ROLES` = Lễ tân · Quản lý CSVC · Admin · Staff (bí danh cũ) → `require_operations`
- `TRAINER_ROLES` = HLV · Admin → `require_trainer_or_admin`
- `require_facility_manager` tách riêng vì chỉ Quản lý CSVC được tạo mã QR máy
- `get_optional_user` cho phép endpoint vừa phục vụ guest vừa tự động lưu hồ sơ khi đã đăng nhập
- `require_trainer_or_admin` tách riêng khỏi `require_staff_or_admin` vì HLV không được
  truy cập báo cáo doanh thu

---

## VI. GIAO DIỆN & TRẢI NGHIỆM

**Phong cách: GEOMETRIC / TECHNICAL / SQUARE** — góc vuông (không bo tròn), viền rõ ràng,
không đổ bóng mềm, không gradient trang trí. Số liệu luôn dùng font mono để thể hiện
tính kỹ thuật.

**Bảng màu** (nền trắng + xanh biển + kim):

| Token | Màu | Dùng cho |
|---|---|---|
| `--bg` / `--bg-sub` | `#ffffff` / `#f5f8fa` | Nền chính, nền phụ |
| `--sea` → `--sea-deep` | `#0b6e8f` → `#06303d` | Tiêu đề, nút chính, biểu đồ |
| `--gold` / `--gold-dark` | `#b8860b` / `#8a6408` | Điểm nhấn cao cấp, dữ liệu quan trọng |
| `--ok` / `--warn` / `--err` | `#0f7a52` / `#b45309` / `#b01c2e` | Trạng thái |

- Tiêu đề và nội dung: **IBM Plex Sans** · Số liệu: **IBM Plex Mono**.
- `--radius: 0px` — mọi thành phần đều vuông vức, nhìn là biết giao diện kỹ thuật.
- Biểu đồ vẽ bằng **SVG thuần** (đường, cột, vòng tiến độ, thanh macros) nên không tăng
  bundle size và không phụ thuộc thư viện ngoài.

**24 trang** (`frontend/app/`):

| Nhóm | Trang |
|---|---|
| Công khai | `/` · `/plans` · `/groupx` · `/pt-booking` · `/equipment` · `/login` · `/branches` · `/facilities` · `/schedule` · `/chat` |
| AI | `/ai-coach` (wizard 12 bước + chat + 4 tab) · `/ai-plus` (PAR-Q+ · InBody · chu kỳ hóa · dinh dưỡng+ · đánh giá tuần) |
| Hội viên | `/progress` · `/contract` · `/rewards` · `/profile` |
| HLV | `/coach` · `/pt-ops` |
| Lễ tân | `/front-desk` · `/leads` · `/pos` |
| CSVC | `/facility` |
| Admin | `/admin` |

Điều hướng (`components/Nav.tsx`) hiển thị menu theo vai trò: mỗi vai trò chỉ thấy các mục
thuộc quyền hạn của mình, kèm nhãn vai trò trên chip người dùng.

---

## VII. KIỂM THỬ

| Hạng mục | Kết quả |
|---|---|
| Bộ test engine AI | **170 / 170 PASS** (`backend/tests/test_ai_engine.py`) |
| Kiểm thử endpoint + RBAC | **28 / 28 PASS** (6 vai trò đăng nhập, 17 endpoint, 7 kiểm tra chặn quyền) |
| Đối chiếu ví dụ nghiệp vụ | BMI 25.35 · LBM 56.62 · BMR 1593 · TDEE 2469 — khớp |
| Quy tắc cứng PAR-Q | Thoát vị đĩa đệm → cấm `no_axial_load`; gợi ý thay thế Box Squat / Goblet Squat / Leg Press (không còn bài nén trục) |
| Xác nhận kép (chống gian lận) | HLV bấm hoàn thành → chưa trừ buổi; hội viên xác nhận → `both_confirmed=true`, cộng điểm |
| Chống lạm dụng tập thử | Đăng ký trùng số điện thoại → HTTP 400 (đã chặn) |
| Build frontend | **26 route**, TypeScript sạch |
| Render toàn bộ trang | **23 / 23 trang HTTP 200** |

Các lỗi thực tế được bộ test phát hiện và đã sửa: Body Fat 24.5% bị xếp nhầm "Essential"
do khe hở giữa các dải ngưỡng; protein vượt trần 2.5 g/kg LBM; bài tập thay thế trỏ tới
tên không tồn tại gây lặp bài; lệch múi giờ khiến chống check-in trùng không hoạt động;
và component `Note` thiếu tone `warn` khiến các trang `contract`/`rewards` không build được.

**Tài khoản demo** (mật khẩu `123`): `admin` · `letan` · `csvc` · `hlv` · `hoivien` · `staff`

---

## VIII. KHỞI CHẠY

```bash
# Backend (cổng 8000) — cần PostgreSQL đang chạy
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Frontend (cổng 3000)
cd frontend
npm run dev
```

Tài liệu API: http://127.0.0.1:8000/docs · Website: http://localhost:3000
Chạy test: `.venv\Scripts\python.exe tests\test_ai_engine.py`

**Lưu ý an toàn**: phác đồ do AI sinh là tư vấn tham khảo, không thay thế chẩn đoán y khoa.
Hệ thống tự động cảnh báo khi BMI ≥30, tuổi ≥55 hoặc <18, Body Fat dưới ngưỡng an toàn,
và khi chọn Bulking trong lúc đã thừa cân.