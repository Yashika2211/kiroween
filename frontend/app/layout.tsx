import type { Metadata, Viewport } from "next";
import { IM_Fell_English, Inter, JetBrains_Mono, Pirata_One } from "next/font/google";

import { Fog } from "@/components/Fog";
import { SiteHeader } from "@/components/SiteHeader";

import "./globals.css";

const display = Pirata_One({ weight: "400", subsets: ["latin"], variable: "--font-display" });
const sans = Inter({ subsets: ["latin"], variable: "--font-sans" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });
const hand = IM_Fell_English({ weight: "400", style: ["normal", "italic"], subsets: ["latin"], variable: "--font-hand" });

export const metadata: Metadata = {
  title: "Necromancer: resurrect dead Python repos",
  description:
    "Paste an abandoned GitHub Python repository. Get an autopsy, a resurrection spec and a working pull request for Python 3.12.",
  icons: { icon: "/favicon.svg" },
};

export const viewport: Viewport = { themeColor: "#0b0a10" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable} ${hand.variable}`}>
      <body className="font-sans antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-ecto focus:px-4 focus:py-2 focus:text-crypt"
        >
          Skip to content
        </a>
        <Fog />
        <div className="relative z-10 flex min-h-screen flex-col">
          <SiteHeader />
          <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 pb-24 sm:px-6">
            {children}
          </main>
          <footer className="border-t border-stone/60 py-6 text-center text-sm text-bone-faint">
            Necromancer · built for Kiroween 2026 · repository code only ever runs in a sealed Docker sandbox
          </footer>
        </div>
      </body>
    </html>
  );
}
