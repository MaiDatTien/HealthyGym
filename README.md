# HealthyGym
Đề cương
Đề tài: Xây dựng website quản lí phòng tập thể hình và sức khỏe cho hội viên.
Lý do chọn đề tài : Do sự phát triển và công nghệ và nhu cầu của sức khỏe của mọi người hiện tại, các chủ phòng thể hình thường dùng những cách thủ công để ghi chép nên dể gây nhầm lẫn và sai sót trong lợi nhuận và cách dạy cho các học viên .
Mục tiêu đề tài: Xây dựng website tự động hóa quy trình đăng ký, điểm danh, quản lý doanh thu và hỗ trợ hội viên theo dõi chỉ số thể trạng.
Phạm vi nghiên cứu: Quy mô phòng tập vừa và nhỏ; đối tượng sử dụng gồm Quản trị viên (Admin), Huấn luyện viên (PT), và Hội viên (Member).
CHƯƠNG 1: TỔNG QUAN VÀ CƠ SỞ LÝ THUYẾT
-	1.1. Khảo sát thực trạng: Phân tích quy trình quản lý truyền thống và các phần mềm gym hiện hành trên thị trường.
-	1.2. Công nghệ sử dụng:
o	Frontend: React.js / Vue.js / HTML5 & Tailwind CSS.
o	BackendPython (Django/FastAPI) 
o	Database: PostgreSQL 
-	1.3. Công cụ hỗ trợ: Git, Postman, Figma.
CHƯƠNG 2: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG
-	2.1. Yêu cầu chức năng:
o	Hội viên: Đăng ký/gia hạn gói tập, đăng ký lịch tập với PT, theo dõi chỉ số BMI/calo, xem lịch sử tập luyện.
o	Huấn luyện viên (PT): Quản lý lịch dạy, thiết lập giáo án/chế độ dinh dưỡng cho hội viên, cập nhật chỉ số sức khỏe hội viên.
o	Quản trị viên (Admin): Quản lý gói tập/lớp học, điểm danh (QR code/Mã số), quản lý nhân sự, báo cáo doanh thu.
-	2.2. Yêu cầu phi chức năng: Bảo mật thông tin, thời gian phản hồi nhanh (< 2s), giao diện tương thích đa thiết bị (Responsive).
-	2.3. Thiết kế hệ thống: Biểu đồ Use Case, Biểu đồ tuần tự (Sequence Diagram), Biểu đồ lớp (Class Diagram).
-	2.4. Thiết kế cơ sở dữ liệu: Sơ đồ ERD và chi tiết các bảng (Users, Packages, Bookings, HealthLogs, Payments).
CHƯƠNG 3: XÂY DỰNG VÀ TRIỂN KHAI HỆ THỐNG
-	3.1. Phân hệ Quản trị & Vận hành: Giao diện Dashboard thống kê, chức năng quét mã QR check-in, tạo hóa đơn.
-	3.2. Phân hệ Theo dõi sức khỏe: Đồ thị biến động cân nặng/BMI theo thời gian, tính toán lượng BMR/TDEE tự động.
-	3.3. Tích hợp cổng thanh toán: VNPay/Momo/Stripe để gia hạn gói tập trực tuyến.
-	3.4. Hệ thống thông báo: Gửi email/thông báo tự động khi sắp hết hạn gói tập hoặc có lịch hẹn mới.
CHƯƠNG 4: THỬ NGHIỆM VÀ ĐÁNH GIÁ
-	4.1. Thử nghiệm chức năng (Black-box Testing): Kiểm thử các luồng đăng ký, thanh toán, đặt lịch.
-	4.2. Đánh giá hiệu năng và bảo mật: Kiểm tra khả năng chịu tải và phân quyền người dùng (RBAC).
-	4.3. Hạn chế và hướng khắc phục.
