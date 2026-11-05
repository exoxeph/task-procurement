import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Supplier Document Checker — A decision you can inspect",
  description:
    "Four approaches to checking supplier quotations. Explore the evidence, the measured results and the limits of a procurement AI experiment.",
  robots: { index: false, follow: false },
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
