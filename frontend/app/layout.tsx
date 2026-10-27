import React from "react";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata = {
  title: "HealthyGym — Sneat Smart Gym ERP & AI Fitness Coach",
  description:
    "Hệ thống Quản trị Phòng Gym Toàn diện & AI Fitness Coach với giao diện Sneat Dashboard hiện đại: " +
    "AI Smart Coach (PAR-Q, InBody, chu kỳ hóa), Quản lý hội viên, PT 1-1, GroupX, POS và CSVC.",
  keywords: [
    "phòng gym", "gym ERP", "huấn luyện viên AI", "InBody", "PAR-Q",
    "quản lý hội viên", "tính TDEE", "chu kỳ hóa tập luyện", "HealthyGym", "sneat dashboard",
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="sneat-app-layout">
          <Nav />
          <div className="sneat-main-content">
            <main className="sneat-page-body">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
