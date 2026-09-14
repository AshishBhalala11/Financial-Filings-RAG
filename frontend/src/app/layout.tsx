import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "10-K Filings Analyst",
  description:
    "Ask grounded questions about an uploaded annual report or Form 10-K.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
