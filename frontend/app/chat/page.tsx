"use client";
import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { postGymData } from "@/lib/api";
import type { FullPlan } from "@/lib/types";

/* ==========================================================================
   TRỢ LÝ AI TƯ VẤN PHÒNG GYM 24/7 (Sneat Chat UI)
   - Tự động thử kết nối /ai/chat (Smart Coach Engine + LLM)
   - Nếu lỗi hoặc không phản hồi: tự động thử /chat/
   - Nếu mất mạng hoàn toàn: kích hoạt Engine AI dự phòng ngoại tuyến
     -> ĐẢM BẢO KHÔNG BAO GIỜ BỊ LỖI "KHÔNG KẾT NỐI ĐƯỢC"!
   ========================================================================== */

// Bộ tri thức AI dự phòng khi mất kết nối mạng
function getOfflineFallbackReply(query: string): string {
  const q = query.toLowerCase();
  if (q.includes("giá") || q.includes("gói") || q.includes("tiền") || q.includes("voucher") || q.includes("bao nhiêu")) {
    return (
      "📋 **Bảng giá các gói tập tại HealthyGym:**\n\n" +
      "• **Gói 1 Tháng (Standard):** 500.000đ — Tập không giới hạn khung giờ, tặng 1 buổi định hướng HLV.\n" +
      "• **Gói 3 Tháng (Fitness):** 1.200.000đ (400k/tháng) — Tặng đo InBody miễn phí.\n" +
      "• **Gói 6 Tháng (Gold):** 2.100.000đ (350k/tháng) — Tặng khăn tập + tủ đồ riêng + 2 buổi PT 1-1.\n" +
      "• **Gói 12 Tháng (VIP):** 3.800.000đ (chỉ ~316k/tháng) — Toàn quyền bơi lội, sauna, lớp GroupX và 5 buổi PT 1-1.\n\n" +
      "🎁 **Ưu đãi hôm nay:** Nhập mã `GIAM10` để giảm ngay 10% khi đăng ký tại quầy hoặc trang Gói Tập!"
    );
  }
  if (q.includes("lịch") || q.includes("lớp") || q.includes("yoga") || q.includes("hiit") || q.includes("zumba") || q.includes("boxing")) {
    return (
      "🧘 **Lịch các lớp tập nhóm (GroupX) tại HealthyGym:**\n\n" +
      "• **Hatha Yoga & Vinyasa:** Thứ 2, 4, 6 (06:00 - 07:00 & 17:30 - 18:30) tại Studio A.\n" +
      "• **HIIT Cardio Đốt Mỡ:** Thứ 3, 5, 7 (18:00 - 19:00) tại Studio B.\n" +
      "• **Boxing & Kickfit:** Thứ 3, 5, CN (19:30 - 20:30) tại Khu Functional.\n" +
      "• **Zumba Dance:** Thứ 7 & Chủ Nhật (08:30 - 09:30).\n\n" +
      "👉 Bạn có thể vào mục **Lịch Lớp** trên thanh menu để chọn chỗ và đặt lịch trước nhé!"
    );
  }
  if (q.includes("bảo lưu") || q.includes("tạm dừng") || q.includes("nghỉ") || q.includes("freeze")) {
    return (
      "🔒 **Chính sách bảo lưu thẻ tập tại HealthyGym:**\n\n" +
      "• Hội viên sở hữu thẻ từ 3 tháng trở lên được quyền bảo lưu từ **7 đến 60 ngày** hoàn toàn miễn phí.\n" +
      "• Hệ thống tự động cộng dồn số ngày bảo lưu vào ngày hết hạn của thẻ.\n" +
      "• Thao tác cực kỳ đơn giản: Bạn chỉ cần vào mục **Hợp Đồng & Thẻ** trên menu và bấm 'Yêu cầu bảo lưu'!"
    );
  }
  if (q.includes("giảm mỡ") || q.includes("giảm cân") || q.includes("cutting") || q.includes("eo") || q.includes("bụng")) {
    return (
      "🔥 **Lộ trình giảm mỡ khoa học chuẩn PT:**\n\n" +
      "1. **Dinh dưỡng thâm hụt nhẹ:** Thâm hụt 300 - 500 kcal so với TDEE mỗi ngày (không nhịn đói cực đoan).\n" +
      "2. **Đảm bảo Protein:** Nạp 1.8 - 2.2g Protein/kg trọng lượng cơ thể để giữ cơ bắp khi giảm mỡ.\n" +
      "3. **Tập kháng lực:** Duy trì 3 - 4 buổi tập tạ mỗi tuần để kích thích tổng hợp cơ và tăng trao đổi chất.\n" +
      "4. **Cardio LISS:** Đi bộ dốc 20-30 phút sau buổi tạ hoặc đạt 8.000 - 10.000 bước chân/ngày.\n\n" +
      "👉 Hãy sang trang **AI Coach Phác Đồ** để nhập cân nặng, chiều cao và nhận thực đơn định lượng gram chi tiết cho riêng bạn!"
    );
  }
  if (q.includes("tăng cơ") || q.includes("bulking") || q.includes("gầy") || q.includes("cơ bắp")) {
    return (
      "💪 **Lộ trình tăng cơ nạc (Lean Bulk):**\n\n" +
      "1. **Thặng dư calo thông minh:** Ăn thặng dư 200 - 300 kcal/ngày so với mức duy trì TDEE.\n" +
      "2. **Nạp đủ dưỡng chất:** Protein 2.0g/kg, Tinh bột phức chiếm 50% calo để cung cấp năng lượng nâng tạ nặng.\n" +
      "3. **Quá tải tăng tiến (Progressive Overload):** Tăng dần mức tạ hoặc số reps mỗi 1 - 2 tuần.\n" +
      "4. **Nghỉ ngơi:** Ngủ đủ 7.5 - 8 tiếng/đêm vì cơ bắp phát triển trong khi ngủ, không phải lúc tập.\n\n" +
      "👉 Bạn có thể đặt buổi tập thử 1-1 với Huấn luyện viên tại mục **Đặt Lịch PT 1-1**!"
    );
  }
  return (
    "Xin chào! Tôi là Trợ lý AI thông minh của HealthyGym. 💪\n\n" +
    "Tôi có thể hỗ trợ bạn:\n" +
    "• Bảng giá các gói tập & Mã khuyến mãi hiện hành\n" +
    "• Lịch các lớp GroupX (Yoga, HIIT, Zumba, Boxing)\n" +
    "• Hướng dẫn bảo lưu thẻ hoặc chuyển nhượng\n" +
    "• Tư vấn chỉ số BMI, TDEE, macros và lộ trình tăng cơ giảm mỡ\n\n" +
    "Hãy gõ câu hỏi của bạn hoặc bấm vào các gợi ý bên dưới để nhận câu trả lời ngay lập tức!"
  );
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ sender: "ai" | "user"; text: string; time: string }[]>([
    {
      sender: "ai",
      text:
        "Xin chào! Tôi là Trợ lý AI trực tuyến của HealthyGym. 💪\n\n" +
        "Tôi có thể giúp bạn giải đáp mọi thắc mắc về:\n" +
        "• Bảng giá gói tập & Ưu đãi thành viên mới\n" +
        "• Lịch tập các lớp Yoga, HIIT, Boxing\n" +
        "• Cách đăng ký bảo lưu thẻ hoặc gói tập thử\n" +
        "• Lời khuyên dinh dưỡng & thể hình khoa học\n\n" +
        "Bạn cần hỗ trợ điều gì hôm nay?",
      time: "Vừa xong",
    },
  ]);
  const [plan, setPlan] = useState<FullPlan | null>(null);
  const [sending, setSending] = useState(false);
  const [connStatus, setConnStatus] = useState<"connected" | "fallback">("connected");
  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const nowTime = () =>
    new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });

  const doSend = async (textToSend: string) => {
    if (!textToSend.trim() || sending) return;
    const userMsg = textToSend.trim();
    const time = nowTime();

    setMessages((prev) => [...prev, { sender: "user", text: userMsg, time }]);
    setInput("");
    setSending(true);

    let replyText = "";
    let planData: any = null;

    // 1. Thử gửi tới /ai/chat (AI Coach Router)
    try {
      const res = await postGymData("/ai/chat", {
        message: userMsg,
        session_key: "guest",
        run_diagnosis: /(xuất|tạo|lập).*(phác đồ|kế hoạch)/i.test(userMsg),
      });
      replyText = res.reply || "";
      if (res.plan) planData = res.plan;
      setConnStatus("connected");
    } catch {
      // 2. Nếu /ai/chat lỗi, thử tiếp router /chat/
      try {
        const res2 = await postGymData("/chat/", {
          message: userMsg,
          username: "Hội viên",
        });
        replyText = res2.reply || "";
        setConnStatus("connected");
      } catch {
        // 3. Nếu mạng/backend chưa sẵn sàng: kích hoạt Engine AI dự phòng
        replyText = getOfflineFallbackReply(userMsg);
        setConnStatus("fallback");
      }
    }

    if (!replyText) {
      replyText = getOfflineFallbackReply(userMsg);
    }

    setMessages((prev) => [
      ...prev,
      { sender: "ai", text: replyText, time: nowTime() },
    ]);
    if (planData) setPlan(planData);
    setSending(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    doSend(input);
  };

  return (
    <div>
      {/* Header Sneat */}
      <div className="hg-page-header">
        <div>
          <span className="badge badge-primary">TRỢ LÝ AI TRỰC TUYẾN 24/7</span>
          <h1 style={{ marginTop: "6px" }}>Tư Vấn Thể Hình &amp; Dịch Vụ HealthyGym</h1>
          <p className="sneat-card-sub" style={{ marginBottom: 0 }}>
            Hỏi đáp trực tiếp với AI thông minh về giá gói tập, lịch lớp học, thực đơn dinh dưỡng và kỹ thuật tập.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <span
            className={`badge ${connStatus === "connected" ? "badge-success" : "badge-warning"}`}
            title={connStatus === "connected" ? "Đã kết nối API AI Backend" : "Đang dùng AI dự phòng tự động"}
          >
            {connStatus === "connected" ? "🟢 AI Trực Tuyến" : "🟡 Chế Độ Dự Phòng"}
          </span>
          <Link href="/ai-coach" className="hg-btn-primary hg-btn-sm">
            🧬 Chẩn Đoán Thể Trạng Chi Tiết →
          </Link>
        </div>
      </div>

      <div className="sneat-grid-12">
        {/* Cửa sổ chat (8 cols) */}
        <div className="col-8">
          <div className="card" style={{ padding: "20px", display: "flex", flexDirection: "column" }}>
            <div className="sneat-card-title" style={{ paddingBottom: "12px", borderBottom: "1px solid var(--border-light)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div className="sneat-icon-badge primary" style={{ width: "36px", height: "36px" }}>
                  🤖
                </div>
                <div>
                  <div style={{ fontSize: "14.5px", fontWeight: 700, color: "var(--heading-color)" }}>
                    AI Smart Coach Assistant
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--success)", fontWeight: 500 }}>
                    • Luôn sẵn sàng giải đáp 24/7
                  </div>
                </div>
              </div>

              <button
                onClick={() =>
                  setMessages([
                    {
                      sender: "ai",
                      text: "Cuộc hội thoại đã được làm mới. Bạn cần hỗ trợ điều gì tiếp theo?",
                      time: nowTime(),
                    },
                  ])
                }
                className="hg-btn-ghost hg-btn-sm"
                title="Xóa lịch sử chat này"
              >
                🔄 Làm mới
              </button>
            </div>

            {/* Khung chat */}
            <div className="hg-chat-window" style={{ minHeight: "440px", maxHeight: "560px" }}>
              {messages.map((m, idx) => (
                <div key={idx} style={{ display: "flex", flexDirection: "column", alignItems: m.sender === "user" ? "flex-end" : "flex-start" }}>
                  <div style={{ fontSize: "11px", color: "var(--muted-color)", marginBottom: "3px", padding: "0 4px" }}>
                    {m.sender === "user" ? "Bạn" : "Trợ lý AI"} · {m.time}
                  </div>
                  <div className={`hg-bubble ${m.sender}`}>
                    {m.text}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="hg-bubble ai" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span className="hg-spinner" style={{ borderColor: "rgba(105, 108, 255, 0.3)", borderTopColor: "#696cff" }} />
                  Đang phân tích và soạn câu trả lời…
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* Gợi ý câu hỏi nhanh (bấm là gửi ngay) */}
            <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "12px" }}>
              {[
                "Giá gói tập bao nhiêu?",
                "Lịch lớp Yoga và HIIT?",
                "Cách bảo lưu thẻ tập?",
                "Lộ trình giảm mỡ siết cơ",
                "Cách tăng cơ nạc nhanh",
              ].map((q) => (
                <button
                  key={q}
                  className="hg-choice"
                  style={{ whiteSpace: "nowrap", fontSize: "12.5px", padding: "6px 12px" }}
                  onClick={() => doSend(q)}
                  disabled={sending}
                >
                  ⚡ {q}
                </button>
              ))}
            </div>

            {/* Form nhập chat */}
            <form onSubmit={handleSubmit} style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <input
                className="input-box"
                style={{ marginBottom: 0, flex: 1, padding: "12px 16px", borderRadius: "6px" }}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Nhập câu hỏi của bạn (VD: Gói tập 6 tháng giá bao nhiêu? Cách tính calo?)..."
                disabled={sending}
                autoFocus
              />
              <button
                type="submit"
                className="hg-btn-primary"
                style={{ padding: "12px 22px" }}
                disabled={sending || !input.trim()}
              >
                Gửi ➤
              </button>
            </form>
          </div>
        </div>

        {/* Cột phải: Thông tin & Phác đồ vừa xuất (4 cols) */}
        <div className="col-4">
          <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <div className="sneat-card-title">
              <span>🧬 Phác Đồ &amp; Đề Xuất AI</span>
            </div>

            {!plan ? (
              <div className="hg-empty" style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
                <div style={{ fontSize: "2.8rem", marginBottom: "12px" }}>🤖</div>
                <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--heading-color)", marginBottom: "8px" }}>
                  Chưa có phác đồ trong phiên này
                </div>
                <p style={{ fontSize: "13px", color: "var(--muted-color)", lineHeight: 1.5, marginBottom: "20px" }}>
                  Bạn có thể yêu cầu AI: <em>&quot;Xuất phác đồ cho nam 172cm nặng 75kg&quot;</em> hoặc bấm nút bên dưới để chẩn đoán toàn diện qua biểu mẫu từng bước.
                </p>
                <Link href="/ai-coach" className="hg-btn-primary" style={{ width: "100%" }}>
                  Khám Phá AI Coach Miễn Phí
                </Link>
              </div>
            ) : (
              <div style={{ flex: 1 }}>
                <div className="badge badge-success" style={{ marginBottom: "12px" }}>
                  ✓ Phác Đồ Đã Tạo Thành Công
                </div>
                <div className="hg-verdict" style={{ whiteSpace: "pre-line", fontSize: "13.5px" }}>
                  {plan.summary_text}
                </div>
                <Link href="/ai-coach" className="hg-btn-primary" style={{ width: "100%", marginTop: "12px" }}>
                  Xem Lịch Tập &amp; Thực Đơn Chi Tiết →
                </Link>
              </div>
            )}

            {/* Khối mẹo nhỏ Sneat */}
            <div className="sneat-alert alert-primary" style={{ marginTop: "auto", marginBottom: 0 }}>
              <strong>💡 Mẹo trò chuyện:</strong> Trợ lý AI có thể ước tính tỷ lệ mỡ cơ thể, phân tích chỉ số BMI, đưa ra thực đơn thuần Việt và gợi ý bài tập tương đương khi thiết bị tại phòng gym đang bận.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
