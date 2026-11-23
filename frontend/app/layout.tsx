import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SmartCampus AI — Orientation universitaire",
  description: "Frontend de démarrage pour la plateforme SmartCampus AI.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
