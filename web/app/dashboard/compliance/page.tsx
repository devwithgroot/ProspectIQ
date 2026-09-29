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
import { buildContactRows } from "@/lib/mock-bundle";

export default function CompliancePage() {
  return (
    <DashboardShell>
      {(bundle) => {
        const suppressed = buildContactRows(bundle).filter(
          (contact) => contact.suppressed,
        );

        return (
          <div className="space-y-8">
            <div>
              <h2 className="text-base font-medium">Compliance</h2>
              <p className="text-sm text-muted-foreground">
                Do-not-contact entries and contacts that must not receive
                outreach.
              </p>
            </div>

            <section className="space-y-3">
              <h3 className="text-sm font-medium">Suppression list</h3>
              <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Kind</TableHead>
                      <TableHead>Value</TableHead>
                      <TableHead>Reason</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {bundle.do_not_contact.map((entry) => (
                      <TableRow key={`${entry.kind}-${entry.value}`}>
                        <TableCell>
                          <Badge variant="outline">{entry.kind}</Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {entry.value}
                        </TableCell>
                        <TableCell className="whitespace-normal text-muted-foreground">
                          {entry.reason ?? "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-medium">
                Blocked contacts ({suppressed.length})
              </h3>
              <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Contact</TableHead>
                      <TableHead>Company</TableHead>
                      <TableHead>Flag</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {suppressed.map((contact) => (
                      <TableRow key={contact.contact_id}>
                        <TableCell>
                          <Link
                            href={`/dashboard/contacts/${contact.contact_id}`}
                            className="font-medium underline-offset-4 hover:underline"
                          >
                            {contact.full_name}
                          </Link>
                        </TableCell>
                        <TableCell>{contact.company_name}</TableCell>
                        <TableCell>
                          <Badge variant="destructive">Do not contact</Badge>
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
