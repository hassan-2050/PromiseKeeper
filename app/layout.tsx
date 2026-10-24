import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PromiseKeeper — Keep the small promises",
  description:
    "A private, evidence-first assistant for conversational commitments.",
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
