import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  // This metadata describes the student- and professor-facing attendance prototype.
  title: "Attendwise | Secure University Attendance",
  description:
    "A student-first university attendance experience for secure check-ins and class insights.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
