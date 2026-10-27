"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData, putGymData, deleteGymData } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default function AdminPortalPage() {
  const [tab, setTab] = useState<"members" | "plans" | "classes" | "trainers" | "branches" | "facilities" | "maintenance">("plans");
  const [members, setMembers] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [trainers, setTrainers] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [facilities, setFacilities] = useState<any[]>([]);
  const [maintenance, setMaintenance] = useState<any[]>([]);
  const [maintForm, setMaintForm] = useState({
    facility_id: "",
    issue: "",
    severity: "medium",
    technician: "",
    cost: "0",
  });
  const [msg, setMsg] = useState("");

  // State cho Form Gói tập (Thêm / Sửa)
  const [editingPlanId, setEditingPlanId] = useState<number | null>(null);
  const [planForm, setPlanForm] = useState({
    name: "",
    duration_days: 30,
    price: 399000,
    benefits: "Tập 24/7, Miễn phí lớp nhóm, Nước uống & Gửi xe",
    includes_pt: false,
    is_popular: false,
  });

  // State cho Form Lớp học (Thêm / Sửa)
  const [editingClassId, setEditingClassId] = useState<number | null>(null);
  const [classForm, setClassForm] = useState({
    name: "",
    category: "Yoga",
    schedule_time: "Thứ 2, 4, 6 (18:00 - 19:00)",
    room: "Studio 1",
    capacity: 25,
    description: "",
  });

  // State cho Form Huấn luyện viên (Thêm / Sửa)
  const [editingTrainerId, setEditingTrainerId] = useState<number | null>(null);
  const [trainerForm, setTrainerForm] = useState({
    full_name: "",
    specialty: "Bodybuilding & Tăng cơ",
    phone: "0909123456",
    experience_years: 4,
    bio: "",
  });

  // State cho Form Chi nhánh (Thêm / Sửa)
  const [editingBranchId, setEditingBranchId] = useState<number | null>(null);
  const [branchForm, setBranchForm] = useState({
    name: "",
    address: "",
    phone: "1900 636920",
    opening_hours: "Mở cửa 24/7",
  });

  // State cho Form Thiết bị CSVC (Thêm / Sửa)
  const [editingFacilityId, setEditingFacilityId] = useState<number | null>(null);
  const [facilityForm, setFacilityForm] = useState({
    name: "",
    category: "Cardio",
    quantity: 15,
    status: "Hoạt động tốt",
    description: "",
  });

  // State cho Form Hội viên (Thêm / Sửa)
  const [editingMemberId, setEditingMemberId] = useState<number | null>(null);
  const [memberForm, setMemberForm] = useState({
    full_name: "",
    phone: "",
    email: "",
    status: "active",
    expire_date: "2027-01-01",
  });

  const loadAll = () => {
    fetchGymData("/admin/members").then(setMembers).catch(() => {});
    fetchGymData("/listings/plans").then(setPlans).catch(() => {});
    fetchGymData("/listings/classes").then(setClasses).catch(() => {});
    fetchGymData("/listings/trainers").then(setTrainers).catch(() => {});
    fetchGymData("/listings/branches").then(setBranches).catch(() => {});
    fetchGymData("/listings/facilities").then(setFacilities).catch(() => {});
    fetchGymData("/pt/maintenance").then(setMaintenance).catch(() => {});
  };

  useEffect(() => {
    loadAll();
  }, []);

  const notify = (text: string) => {
    setMsg(text);
    setTimeout(() => setMsg(""), 4500);
    loadAll();
  };

  // Xử lý lưu Gói tập
  const savePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingPlanId) {
        await putGymData(`/admin/plans/${editingPlanId}`, planForm);
        notify("✅ Đã cập nhật gói tập!");
      } else {
        await postGymData("/admin/plans", planForm);
        notify("✅ Đã thêm gói tập mới!");
      }
      setEditingPlanId(null);
      setPlanForm({ name: "", duration_days: 30, price: 399000, benefits: "", includes_pt: false, is_popular: false });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  // Xử lý lưu Lớp học
  const saveClass = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingClassId) {
        await putGymData(`/admin/classes/${editingClassId}`, classForm);
        notify("✅ Đã cập nhật lớp học!");
      } else {
        await postGymData("/admin/classes", classForm);
        notify("✅ Đã thêm lớp học mới!");
      }
      setEditingClassId(null);
      setClassForm({ name: "", category: "Yoga", schedule_time: "", room: "Studio 1", capacity: 25, description: "" });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  // Xử lý lưu HLV
  const saveTrainer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingTrainerId) {
        await putGymData(`/admin/trainers/${editingTrainerId}`, trainerForm);
        notify("✅ Đã cập nhật Huấn luyện viên!");
      } else {
        await postGymData("/admin/trainers", trainerForm);
        notify("✅ Đã thêm Huấn luyện viên mới!");
      }
      setEditingTrainerId(null);
      setTrainerForm({ full_name: "", specialty: "", phone: "", experience_years: 4, bio: "" });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  // Xử lý lưu Chi nhánh
  const saveBranch = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingBranchId) {
        await putGymData(`/admin/branches/${editingBranchId}`, branchForm);
        notify("✅ Đã cập nhật chi nhánh!");
      } else {
        await postGymData("/admin/branches", branchForm);
        notify("✅ Đã thêm chi nhánh mới!");
      }
      setEditingBranchId(null);
      setBranchForm({ name: "", address: "", phone: "1900 636920", opening_hours: "Mở cửa 24/7" });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  // Xử lý lưu CSVC
  const saveFacility = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingFacilityId) {
        await putGymData(`/admin/facilities/${editingFacilityId}`, facilityForm);
        notify("✅ Đã cập nhật thiết bị!");
      } else {
        await postGymData("/admin/facilities", facilityForm);
        notify("✅ Đã thêm thiết bị mới!");
      }
      setEditingFacilityId(null);
      setFacilityForm({ name: "", category: "Cardio", quantity: 10, status: "Hoạt động tốt", description: "" });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  // Xử lý lưu Hội viên
  const saveMember = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...memberForm,
        expire_date: memberForm.expire_date ? memberForm.expire_date : null,
      };
      if (editingMemberId) {
        await putGymData(`/admin/members/${editingMemberId}`, payload);
        notify("✅ Đã cập nhật thông tin hội viên!");
      } else {
        await postGymData("/admin/members", payload);
        notify("✅ Đã thêm hội viên mới!");
      }
      setEditingMemberId(null);
      setMemberForm({ full_name: "", phone: "", email: "", status: "active", expire_date: "2027-01-01" });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">TRUNG TÂM QUẢN TRỊ VIÊN (ADMIN / 123)</span>
          <h1 style={{ marginTop: "0.4rem" }}>⚙️ Quản Lý Toàn Hệ Thống (Thêm • Sửa • Xóa)</h1>
          <p style={{ color: "#64748b" }}>
            Chọn từng phân mục bên dưới để thêm mới, chỉnh sửa hoặc xóa dữ liệu trực tiếp trong PostgreSQL.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {[
            { id: "plans", label: "💎 Gói Tập" },
            { id: "classes", label: "📅 Lớp Học" },
            { id: "trainers", label: "🏆 Huấn Luyện Viên" },
            { id: "branches", label: "📍 Chi Nhánh" },
            { id: "facilities", label: "🏋️ Thiết Bị CSVC" },
            { id: "maintenance", label: "🔧 Bảo Trì Thiết Bị" },
            { id: "members", label: "👥 Hội Viên & Check-in" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={tab === t.id ? "hg-btn-emerald" : "hg-btn-ghost"}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {msg && (
        <div
          style={{
            background: "#0e6d8c",
            color: "#fff",
            padding: "1rem 1.4rem",
            borderRadius: "14px",
            marginBottom: "1.5rem",
            fontWeight: 700,
          }}
        >
          {msg}
        </div>
      )}

      {/* TAB 1: QUẢN LÝ GÓI TẬP */}
      {tab === "plans" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={savePlan} className="card">
            <h3>{editingPlanId ? `✏️ Sửa Gói Tập #${editingPlanId}` : "➕ Thêm Gói Tập Mới"}</h3>
            <label style={{ fontSize: "0.85rem", fontWeight: 700, marginTop: "0.8rem" }}>Tên gói tập</label>
            <input
              className="input-box"
              value={planForm.name}
              onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })}
              required
            />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Số ngày sử dụng</label>
            <input
              type="number"
              className="input-box"
              value={planForm.duration_days}
              onChange={(e) => setPlanForm({ ...planForm, duration_days: Number(e.target.value) })}
              required
            />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Giá trọn gói (VNĐ)</label>
            <input
              type="number"
              className="input-box"
              value={planForm.price}
              onChange={(e) => setPlanForm({ ...planForm, price: Number(e.target.value) })}
              required
            />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Quyền lợi (cách nhau bằng dấu phẩy)</label>
            <textarea
              className="input-box"
              rows={3}
              value={planForm.benefits}
              onChange={(e) => setPlanForm({ ...planForm, benefits: e.target.value })}
            />
            <label style={{ display: "flex", gap: "0.5rem", marginBottom: "0.8rem", fontSize: "0.9rem" }}>
              <input
                type="checkbox"
                checked={planForm.is_popular}
                onChange={(e) => setPlanForm({ ...planForm, is_popular: e.target.checked })}
              />
              Đánh dấu là gói Phổ biến nhất
            </label>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button type="submit" className="hg-btn-emerald" style={{ flex: 1 }}>
                {editingPlanId ? "Lưu Cập Nhật" : "Thêm Gói Tập"}
              </button>
              {editingPlanId && (
                <button type="button" className="hg-btn-ghost" onClick={() => setEditingPlanId(null)}>
                  Hủy
                </button>
              )}
            </div>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Gói Tập ({plans.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tên gói</th>
                  <th>Thời hạn</th>
                  <th>Giá</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {plans.map((p) => (
                  <tr key={p.id}>
                    <td>#{p.id}</td>
                    <td><strong>{p.name}</strong></td>
                    <td>{p.duration_days} ngày</td>
                    <td style={{ color: "#0e6d8c", fontWeight: 700 }}>{formatCurrency(p.price)}</td>
                    <td style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingPlanId(p.id);
                          setPlanForm({
                            name: p.name,
                            duration_days: p.duration_days,
                            price: p.price,
                            benefits: p.benefits || "",
                            includes_pt: p.includes_pt,
                            is_popular: p.is_popular,
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.4rem 0.8rem" }}
                        onClick={() => deleteGymData(`/admin/plans/${p.id}`).then(() => notify("🗑️ Đã xóa gói tập"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: QUẢN LÝ LỚP HỌC */}
      {tab === "classes" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={saveClass} className="card">
            <h3>{editingClassId ? `✏️ Sửa Lớp Học #${editingClassId}` : "➕ Thêm Lớp Học Mới"}</h3>
            <label style={{ fontSize: "0.85rem", fontWeight: 700, marginTop: "0.8rem" }}>Tên lớp học</label>
            <input
              className="input-box"
              value={classForm.name}
              onChange={(e) => setClassForm({ ...classForm, name: e.target.value })}
              required
            />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Bộ môn</label>
            <select
              className="input-box"
              value={classForm.category}
              onChange={(e) => setClassForm({ ...classForm, category: e.target.value })}
            >
              <option value="Yoga">Yoga</option>
              <option value="HIIT">HIIT</option>
              <option value="Boxing">Boxing / Dance</option>
              <option value="Strength">Strength</option>
            </select>
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Lịch học</label>
            <input
              className="input-box"
              value={classForm.schedule_time}
              onChange={(e) => setClassForm({ ...classForm, schedule_time: e.target.value })}
              required
            />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Phòng tập & Sức chứa</label>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <input
                className="input-box"
                placeholder="Phòng"
                value={classForm.room}
                onChange={(e) => setClassForm({ ...classForm, room: e.target.value })}
              />
              <input
                type="number"
                className="input-box"
                placeholder="Sức chứa"
                value={classForm.capacity}
                onChange={(e) => setClassForm({ ...classForm, capacity: Number(e.target.value) })}
              />
            </div>
            <button type="submit" className="hg-btn-emerald">
              {editingClassId ? "Lưu Cập Nhật" : "Thêm Lớp Học"}
            </button>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Lớp Học ({classes.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Tên lớp</th>
                  <th>Bộ môn</th>
                  <th>Lịch học</th>
                  <th>Sĩ số</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {classes.map((c) => (
                  <tr key={c.id}>
                    <td><strong>{c.name}</strong></td>
                    <td><span className="chip">{c.category}</span></td>
                    <td>{c.schedule_time}</td>
                    <td>{c.enrolled_count}/{c.capacity}</td>
                    <td style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingClassId(c.id);
                          setClassForm({
                            name: c.name,
                            category: c.category,
                            schedule_time: c.schedule_time,
                            room: c.room,
                            capacity: c.capacity,
                            description: c.description || "",
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.4rem 0.8rem" }}
                        onClick={() => deleteGymData(`/admin/classes/${c.id}`).then(() => notify("🗑️ Đã xóa lớp học"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: QUẢN LÝ HUẤN LUYỆN VIÊN */}
      {tab === "trainers" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={saveTrainer} className="card">
            <h3>{editingTrainerId ? `✏️ Sửa HLV #${editingTrainerId}` : "➕ Thêm Huấn Luyện Viên"}</h3>
            <input
              className="input-box"
              placeholder="Họ và tên HLV *"
              value={trainerForm.full_name}
              onChange={(e) => setTrainerForm({ ...trainerForm, full_name: e.target.value })}
              required
            />
            <input
              className="input-box"
              placeholder="Chuyên môn *"
              value={trainerForm.specialty}
              onChange={(e) => setTrainerForm({ ...trainerForm, specialty: e.target.value })}
              required
            />
            <input
              className="input-box"
              placeholder="Số điện thoại"
              value={trainerForm.phone}
              onChange={(e) => setTrainerForm({ ...trainerForm, phone: e.target.value })}
            />
            <input
              type="number"
              className="input-box"
              placeholder="Số năm kinh nghiệm"
              value={trainerForm.experience_years}
              onChange={(e) => setTrainerForm({ ...trainerForm, experience_years: Number(e.target.value) })}
            />
            <textarea
              className="input-box"
              rows={3}
              placeholder="Tiểu sử / Chứng chỉ"
              value={trainerForm.bio}
              onChange={(e) => setTrainerForm({ ...trainerForm, bio: e.target.value })}
            />
            <button type="submit" className="hg-btn-emerald">
              {editingTrainerId ? "Lưu Cập Nhật" : "Thêm HLV"}
            </button>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Huấn Luyện Viên ({trainers.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Họ tên</th>
                  <th>Chuyên môn</th>
                  <th>Kinh nghiệm</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {trainers.map((t) => (
                  <tr key={t.id}>
                    <td><strong>{t.full_name}</strong></td>
                    <td>{t.specialty}</td>
                    <td>{t.experience_years} năm</td>
                    <td style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingTrainerId(t.id);
                          setTrainerForm({
                            full_name: t.full_name,
                            specialty: t.specialty,
                            phone: t.phone || "",
                            experience_years: t.experience_years,
                            bio: t.bio || "",
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.4rem 0.8rem" }}
                        onClick={() => deleteGymData(`/admin/trainers/${t.id}`).then(() => notify("🗑️ Đã xóa HLV"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: QUẢN LÝ CHI NHÁNH */}
      {tab === "branches" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={saveBranch} className="card">
            <h3>{editingBranchId ? `✏️ Sửa Chi Nhánh #${editingBranchId}` : "➕ Thêm Chi Nhánh Mới"}</h3>
            <input
              className="input-box"
              placeholder="Tên chi nhánh *"
              value={branchForm.name}
              onChange={(e) => setBranchForm({ ...branchForm, name: e.target.value })}
              required
            />
            <input
              className="input-box"
              placeholder="Địa chỉ chi tiết *"
              value={branchForm.address}
              onChange={(e) => setBranchForm({ ...branchForm, address: e.target.value })}
              required
            />
            <input
              className="input-box"
              placeholder="Hotline"
              value={branchForm.phone}
              onChange={(e) => setBranchForm({ ...branchForm, phone: e.target.value })}
            />
            <input
              className="input-box"
              placeholder="Giờ mở cửa"
              value={branchForm.opening_hours}
              onChange={(e) => setBranchForm({ ...branchForm, opening_hours: e.target.value })}
            />
            <button type="submit" className="hg-btn-emerald">
              {editingBranchId ? "Lưu Cập Nhật" : "Thêm Chi Nhánh"}
            </button>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Chi Nhánh ({branches.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Tên chi nhánh</th>
                  <th>Địa chỉ</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {branches.map((b) => (
                  <tr key={b.id}>
                    <td><strong>{b.name}</strong></td>
                    <td>{b.address}</td>
                    <td style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingBranchId(b.id);
                          setBranchForm({
                            name: b.name,
                            address: b.address,
                            phone: b.phone || "",
                            opening_hours: b.opening_hours,
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.4rem 0.8rem" }}
                        onClick={() => deleteGymData(`/admin/branches/${b.id}`).then(() => notify("🗑️ Đã xóa chi nhánh"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: QUẢN LÝ THIẾT BỊ CSVC */}
      {tab === "facilities" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={saveFacility} className="card">
            <h3>{editingFacilityId ? `✏️ Sửa Thiết Bị #${editingFacilityId}` : "➕ Thêm Thiết Bị Mới"}</h3>
            <input
              className="input-box"
              placeholder="Tên thiết bị / khu vực *"
              value={facilityForm.name}
              onChange={(e) => setFacilityForm({ ...facilityForm, name: e.target.value })}
              required
            />
            <select
              className="input-box"
              value={facilityForm.category}
              onChange={(e) => setFacilityForm({ ...facilityForm, category: e.target.value })}
            >
              <option value="Cardio">Cardio</option>
              <option value="Strength">Strength (Tạ & Khung gánh)</option>
              <option value="Tiện ích">Tiện ích miễn phí</option>
            </select>
            <input
              type="number"
              className="input-box"
              placeholder="Số lượng"
              value={facilityForm.quantity}
              onChange={(e) => setFacilityForm({ ...facilityForm, quantity: Number(e.target.value) })}
            />
            <textarea
              className="input-box"
              rows={3}
              placeholder="Mô tả thiết bị"
              value={facilityForm.description}
              onChange={(e) => setFacilityForm({ ...facilityForm, description: e.target.value })}
            />
            <button type="submit" className="hg-btn-emerald">
              {editingFacilityId ? "Lưu Cập Nhật" : "Thêm Thiết Bị"}
            </button>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Thiết Bị ({facilities.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Tên thiết bị</th>
                  <th>Loại</th>
                  <th>Số lượng</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {facilities.map((f) => (
                  <tr key={f.id}>
                    <td><strong>{f.name}</strong></td>
                    <td><span className="chip">{f.category}</span></td>
                    <td>{f.quantity}</td>
                    <td style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingFacilityId(f.id);
                          setFacilityForm({
                            name: f.name,
                            category: f.category,
                            quantity: f.quantity,
                            status: f.status,
                            description: f.description || "",
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.4rem 0.8rem" }}
                        onClick={() => deleteGymData(`/admin/facilities/${f.id}`).then(() => notify("🗑️ Đã xóa thiết bị"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 6: QUẢN LÝ HỘI VIÊN */}
      {tab === "members" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={saveMember} className="card">
            <h3>{editingMemberId ? `✏️ Sửa Hội Viên #${editingMemberId}` : "➕ Thêm Hội Viên"}</h3>
            <input
              className="input-box"
              placeholder="Họ và tên *"
              value={memberForm.full_name}
              onChange={(e) => setMemberForm({ ...memberForm, full_name: e.target.value })}
              required
            />
            <input
              className="input-box"
              placeholder="Số điện thoại"
              value={memberForm.phone}
              onChange={(e) => setMemberForm({ ...memberForm, phone: e.target.value })}
            />
            <select
              className="input-box"
              value={memberForm.status}
              onChange={(e) => setMemberForm({ ...memberForm, status: e.target.value })}
            >
              <option value="active">active (Đang hoạt động)</option>
              <option value="frozen">frozen (Đang bảo lưu)</option>
              <option value="expired">expired (Đã hết hạn)</option>
              <option value="inactive">inactive (Chưa kích hoạt)</option>
            </select>
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Hạn thẻ (YYYY-MM-DD)</label>
            <input
              type="date"
              className="input-box"
              value={memberForm.expire_date}
              onChange={(e) => setMemberForm({ ...memberForm, expire_date: e.target.value })}
            />
            <button type="submit" className="hg-btn-emerald">
              {editingMemberId ? "Lưu Cập Nhật" : "Thêm Hội Viên"}
            </button>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Hội Viên ({members.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Họ tên</th>
                  <th>SĐT</th>
                  <th>Trạng thái</th>
                  <th>Hạn thẻ</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id}>
                    <td><strong>{m.full_name}</strong></td>
                    <td>{m.phone || "—"}</td>
                    <td><span className="chip">{m.status}</span></td>
                    <td>{m.expire_date || "—"}</td>
                    <td style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                      <button
                        className="hg-btn-emerald"
                        style={{ padding: "0.35rem 0.7rem", fontSize: "0.8rem" }}
                        onClick={() => postGymData(`/interactions/checkin/${m.id}`).then((r) => notify(r.message)).catch((e) => notify(e.message))}
                      >
                        Check-in
                      </button>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingMemberId(m.id);
                          setMemberForm({
                            full_name: m.full_name,
                            phone: m.phone || "",
                            email: m.email || "",
                            status: m.status,
                            expire_date: m.expire_date || "",
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.35rem 0.7rem", fontSize: "0.8rem" }}
                        onClick={() => deleteGymData(`/admin/members/${m.id}`).then(() => notify("🗑️ Đã xóa hội viên"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB: QUẢN LÝ BẢO TRÌ THIẾT BỊ */}
      {tab === "maintenance" && (
        <div>
          <div className="hg-chart-card">
            <h3 style={{ marginBottom: "0.8rem" }}>🔧 Báo Cáo Sự Cố Thiết Bị</h3>
            <p className="hg-muted" style={{ marginBottom: "1rem" }}>
              Phiếu bảo trì mức độ medium/high sẽ tự động chuyển thiết bị sang trạng thái
              &quot;Đang bảo trì&quot; để hội viên biết.
            </p>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  const res = await postGymData("/pt/maintenance", {
                    facility_id: Number(maintForm.facility_id),
                    issue: maintForm.issue,
                    severity: maintForm.severity,
                    technician: maintForm.technician || null,
                    cost: Number(maintForm.cost || 0),
                  });
                  setMaintForm({ facility_id: "", issue: "", severity: "medium", technician: "", cost: "0" });
                  notify(res.message);
                } catch (err: any) {
                  notify(err.message);
                }
              }}
            >
              <select
                className="input-box"
                value={maintForm.facility_id}
                onChange={(e) => setMaintForm({ ...maintForm, facility_id: e.target.value })}
                required
              >
                <option value="">— Chọn thiết bị / khu vực —</option>
                {facilities.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </select>
              <textarea
                className="input-box"
                rows={3}
                placeholder="Mô tả sự cố chi tiết *"
                value={maintForm.issue}
                onChange={(e) => setMaintForm({ ...maintForm, issue: e.target.value })}
                required
              />
              <div className="hg-flex" style={{ gap: "0.6rem" }}>
                <select
                  className="input-box"
                  value={maintForm.severity}
                  onChange={(e) => setMaintForm({ ...maintForm, severity: e.target.value })}
                >
                  <option value="low">Mức độ: Thấp</option>
                  <option value="medium">Mức độ: Trung bình</option>
                  <option value="high">Mức độ: Nghiêm trọng</option>
                </select>
                <input
                  className="input-box"
                  placeholder="Kỹ thuật viên phụ trách"
                  value={maintForm.technician}
                  onChange={(e) => setMaintForm({ ...maintForm, technician: e.target.value })}
                />
                <input
                  className="input-box"
                  type="number"
                  placeholder="Chi phí dự kiến (đ)"
                  value={maintForm.cost}
                  onChange={(e) => setMaintForm({ ...maintForm, cost: e.target.value })}
                />
              </div>
              <button type="submit" className="hg-btn-emerald">
                Tạo Phiếu Bảo Trì
              </button>
            </form>
          </div>

          <div className="table-wrap">
            <h3>Danh Sách Phiếu Bảo Trì ({maintenance.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Thiết bị</th>
                  <th>Sự cố</th>
                  <th>Mức độ</th>
                  <th>Trạng thái</th>
                  <th>Kỹ thuật viên</th>
                  <th>Chi phí</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {maintenance.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center", color: "#6b8598" }}>
                      Chưa có phiếu bảo trì nào.
                    </td>
                  </tr>
                ) : (
                  maintenance.map((t) => (
                    <tr key={t.id}>
                      <td>
                        <strong>{t.facility_name}</strong>
                      </td>
                      <td style={{ fontSize: "0.85rem", maxWidth: 300 }}>{t.issue}</td>
                      <td>
                        <span
                          className={`chip ${
                            t.severity === "high"
                              ? "chip-danger"
                              : t.severity === "medium"
                              ? "chip-warn"
                              : ""
                          }`}
                        >
                          {t.severity}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`chip ${
                            t.status === "resolved" ? "chip-ok" : t.status === "in_progress" ? "chip-warn" : ""
                          }`}
                        >
                          {t.status === "resolved"
                            ? "Đã xử lý"
                            : t.status === "in_progress"
                            ? "Đang xử lý"
                            : "Chờ xử lý"}
                        </span>
                      </td>
                      <td>{t.technician || "—"}</td>
                      <td>{formatCurrency(t.cost || 0)}</td>
                      <td style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                        {t.status !== "in_progress" && t.status !== "resolved" && (
                          <button
                            className="hg-btn-ghost"
                            style={{ padding: "0.35rem 0.7rem", fontSize: "0.8rem" }}
                            onClick={() =>
                              putGymData(`/pt/maintenance/${t.id}`, { status: "in_progress" })
                                .then((r) => notify(r.message))
                                .catch((e) => notify(e.message))
                            }
                          >
                            Nhận xử lý
                          </button>
                        )}
                        {t.status !== "resolved" && (
                          <button
                            className="hg-btn-emerald"
                            style={{ padding: "0.35rem 0.7rem", fontSize: "0.8rem" }}
                            onClick={() =>
                              putGymData(`/pt/maintenance/${t.id}`, { status: "resolved" })
                                .then((r) => notify(r.message))
                                .catch((e) => notify(e.message))
                            }
                          >
                            Hoàn tất
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
      )}
    </div>
  );
}
