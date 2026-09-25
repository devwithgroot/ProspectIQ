import type { Metadata } from "next"
import { Inter } from "next/font/google"

import "./globals.css"

const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "ProspectIQ",
  description: "Learn your company, upload a prospect list, and get research briefings.",
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body
        className={`${inter.className} flex min-h-full flex-col bg-background text-foreground`}
      >
        <header className="border-b bg-card/80 backdrop-blur">
          <div className="mx-auto flex h-14 w-full max-w-3xl items-center px-6">
            <div className="flex items-center gap-2.5">
              <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-xs font-semibold text-primary-foreground">
                IQ
              </span>
              <div>
                <p className="text-sm font-semibold leading-none">ProspectIQ</p>
                <p className="text-xs text-muted-foreground">
                  Research before you reach out
                </p>
              </div>
            </div>
          </div>
        </header>
        <main className="flex-1">{children}</main>
      </body>
    </html>
  )
}
