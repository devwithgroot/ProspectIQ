import Link from "next/link";

import { DashboardNav } from "@/components/dashboard-nav";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-8">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Phase 4 · Mock book
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Seller dashboard
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Browse researched prospects, contacts, and compliance from the
            fixture bundle while live runs are still JSON files.
          </p>
        </div>
        <div className="flex flex-col items-start gap-3 sm:items-end">
          <DashboardNav />
          <Link
            href="/"
            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            Back to research form
          </Link>
        </div>
      </div>
      {children}
    </div>
  );
}
