import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Secure Attendance System",
  description: "University attendance web application.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
