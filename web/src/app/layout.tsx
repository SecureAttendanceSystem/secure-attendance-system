import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  // This metadata uses the project's name on the authentication screen and browser tab.
  title: "Secure University Attendance System",
  description:
    "Secure attendance system for university students and professors.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
