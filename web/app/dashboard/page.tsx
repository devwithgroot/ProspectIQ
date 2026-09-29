"use client";

import Link from "next/link";

import { DashboardShell } from "@/components/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { buildProspectRows, recommendationVariant } from "@/lib/mock-bundle";

export default function DashboardOverviewPage() {
  return (
    <DashboardShell>
      {(bundle) => {
        const prospects = buildProspectRows(bundle);
        const highPriority = prospects.filter((row) =>
          (row.profile?.recommendation ?? "").toLowerCase().includes("high"),
        ).length;
        const potential = prospects.filter((row) =>
          (row.profile?.recommendation ?? "")
            .toLowerCase()
            .includes("potential"),
        ).length;
        const dncContacts = bundle.contacts.filter(
          (contact) => contact.do_not_contact,
        ).length;

        return (
          <div className="space-y-8">
            <Card>
              <CardHeader>
                <CardTitle>{bundle.user.full_name}</CardTitle>
                <CardDescription>
                  {bundle.user.title} · {bundle.user.company.name} ·{" "}
                  {bundle.user.company.industry}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p className="text-muted-foreground">
                  {bundle.user.company.description}
                </p>
                <p>
                  <span className="text-muted-foreground">Voice CTA: </span>
                  {bundle.user.voice.cta}
                </p>
                <p>
                  <span className="text-muted-foreground">Outreach from: </span>
                  {bundle.user.outreach_email}
                  {bundle.user.outreach_email_verified ? (
                    <Badge className="ml-2" variant="secondary">
                      verified
                    </Badge>
                  ) : null}
                </p>
              </CardContent>
            </Card>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Prospects" value={String(prospects.length)} />
              <StatCard
                label="Contacts"
                value={String(bundle.contacts.length)}
              />
              <StatCard
                label="High-priority"
                value={String(highPriority)}
                hint={`${potential} potential`}
              />
              <StatCard
                label="DNC flagged"
                value={String(dncContacts)}
                hint={`${bundle.do_not_contact.length} suppression rows`}
              />
            </div>

            <section className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-medium">Products</h2>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                {bundle.products.map((product) => (
                  <Card key={product.product_id} size="sm">
                    <CardHeader>
                      <CardTitle>{product.name}</CardTitle>
                      <CardDescription>{product.category}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="line-clamp-3 text-sm text-muted-foreground">
                        {product.description}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>

            <section className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-medium">Top prospects</h2>
                <Link
                  href="/dashboard/prospects"
                  className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                >
                  View all
                </Link>
              </div>
              <div className="grid gap-3">
                {prospects.map((row) => (
                  <Link
                    key={row.company_id}
                    href={`/dashboard/prospects/${row.company_id}`}
                    className="rounded-xl ring-1 ring-foreground/10 transition-colors hover:bg-muted/40"
                    aria-label={`Open ${row.name}`}
                  >
                    <div className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="font-medium">{row.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {row.industry}
                          {row.headquarters ? ` · ${row.headquarters}` : ""}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {row.profile ? (
                          <>
                            <Badge
                              variant={recommendationVariant(
                                row.profile.recommendation,
                              )}
                            >
                              {row.profile.recommendation}
                            </Badge>
                            <span className="text-sm font-medium tabular-nums">
                              {row.profile.overall_score.toFixed(0)}
                            </span>
                          </>
                        ) : null}
                        <span className="text-sm text-muted-foreground">
                          {row.contact_count} contacts
                        </span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          </div>
        );
      }}
    </DashboardShell>
  );
}

const StatCard = ({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) => (
  <Card size="sm">
    <CardHeader>
      <CardDescription>{label}</CardDescription>
      <CardTitle className="text-2xl tabular-nums">{value}</CardTitle>
    </CardHeader>
    {hint ? (
      <CardContent>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </CardContent>
    ) : null}
  </Card>
);
