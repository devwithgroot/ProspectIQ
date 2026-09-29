"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { DashboardShell } from "@/components/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  buildContactRows,
  buildProspectRows,
  formatRole,
  recommendationVariant,
} from "@/lib/mock-bundle";

export default function ProspectDetailPage() {
  const params = useParams<{ companyId: string }>();
  const companyId = params.companyId;

  return (
    <DashboardShell>
      {(bundle) => {
        const prospect = buildProspectRows(bundle).find(
          (row) => row.company_id === companyId,
        );
        const contacts = buildContactRows(bundle, companyId);

        if (!prospect) {
          return (
            <p className="text-sm text-muted-foreground">
              Company not found in the mock bundle.{" "}
              <Link href="/dashboard/prospects" className="underline">
                Back to prospects
              </Link>
            </p>
          );
        }

        const profile = prospect.profile;

        return (
          <div className="space-y-8">
            <div className="space-y-2">
              <Link
                href="/dashboard/prospects"
                className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              >
                ← Prospects
              </Link>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold tracking-tight">
                    {prospect.name}
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    {prospect.industry}
                    {prospect.headquarters ? ` · ${prospect.headquarters}` : ""}
                    {prospect.employee_count
                      ? ` · ${prospect.employee_count.toLocaleString()} employees`
                      : ""}
                  </p>
                  {prospect.website ? (
                    <a
                      href={prospect.website}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-block text-sm underline-offset-4 hover:underline"
                    >
                      {prospect.website}
                    </a>
                  ) : null}
                </div>
                {profile ? (
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={recommendationVariant(profile.recommendation)}
                    >
                      {profile.recommendation}
                    </Badge>
                    <span className="text-2xl font-semibold tabular-nums">
                      {profile.overall_score.toFixed(0)}
                    </span>
                  </div>
                ) : null}
              </div>
            </div>

            {profile ? (
              <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Executive summary</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm text-muted-foreground">
                    <p>{profile.executive_summary}</p>
                    <p>
                      <span className="font-medium text-foreground">
                        Why relevant:{" "}
                      </span>
                      {profile.why_relevant_to_user}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Sales approach</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm text-muted-foreground">
                    <p>{profile.recommended_sales_approach}</p>
                    <div className="flex flex-wrap gap-1">
                      {prospect.matched_products.map((product) => (
                        <Badge key={product.product_id} variant="outline">
                          {product.name}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Signals</CardTitle>
                    <CardDescription>
                      Research evidence that drove the score
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {profile.signals.map((signal) => (
                      <div key={`${signal.type}-${signal.description}`}>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="secondary">{signal.type}</Badge>
                          <Badge variant="outline">{signal.strength}</Badge>
                        </div>
                        <p className="mt-1 text-sm">{signal.description}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Pain points</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
                      {profile.pain_points.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </div>
            ) : null}

            <section className="space-y-3">
              <h3 className="text-base font-medium">
                Contacts ({contacts.length})
              </h3>
              <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Channel</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {contacts.map((contact) => (
                      <TableRow key={contact.contact_id}>
                        <TableCell className="whitespace-normal">
                          <Link
                            href={`/dashboard/contacts/${contact.contact_id}`}
                            className="font-medium underline-offset-4 hover:underline"
                          >
                            {contact.full_name}
                          </Link>
                          <p className="text-xs text-muted-foreground">
                            {contact.title}
                          </p>
                        </TableCell>
                        <TableCell className="capitalize">
                          {formatRole(contact.decision_role)}
                        </TableCell>
                        <TableCell className="capitalize">
                          {contact.preferred_channel}
                        </TableCell>
                        <TableCell>
                          {contact.suppressed ? (
                            <Badge variant="destructive">Do not contact</Badge>
                          ) : (
                            <Badge variant="secondary">Reachable</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </section>
          </div>
        );
      }}
    </DashboardShell>
  );
}
