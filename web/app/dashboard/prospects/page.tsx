"use client";

import Link from "next/link";

import { DashboardShell } from "@/components/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { buildProspectRows, recommendationVariant } from "@/lib/mock-bundle";

export default function ProspectsPage() {
  return (
    <DashboardShell>
      {(bundle) => {
        const rows = buildProspectRows(bundle);

        return (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-medium">Prospects</h2>
              <p className="text-sm text-muted-foreground">
                Companies joined with scores, matched products, and contact
                counts from the mock bundle.
              </p>
            </div>

            <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Company</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Recommendation</TableHead>
                    <TableHead>Matched products</TableHead>
                    <TableHead className="text-right">Contacts</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow key={row.company_id}>
                      <TableCell className="whitespace-normal">
                        <Link
                          href={`/dashboard/prospects/${row.company_id}`}
                          className="font-medium underline-offset-4 hover:underline"
                        >
                          {row.name}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {row.industry}
                          {row.headquarters ? ` · ${row.headquarters}` : ""}
                        </p>
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {row.profile
                          ? row.profile.overall_score.toFixed(0)
                          : "—"}
                      </TableCell>
                      <TableCell>
                        {row.profile ? (
                          <Badge
                            variant={recommendationVariant(
                              row.profile.recommendation,
                            )}
                          >
                            {row.profile.recommendation}
                          </Badge>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell className="whitespace-normal">
                        <div className="flex flex-wrap gap-1">
                          {row.matched_products.length === 0 ? (
                            <span className="text-muted-foreground">—</span>
                          ) : (
                            row.matched_products.map((product) => (
                              <Badge key={product.product_id} variant="outline">
                                {product.name.replace("NexusFlow ", "")}
                              </Badge>
                            ))
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {row.contact_count}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        );
      }}
    </DashboardShell>
  );
}
