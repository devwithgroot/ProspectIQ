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
import { buildContactRows, formatRole } from "@/lib/mock-bundle";
import type { Channel, ChannelConsent } from "@/lib/mock-types";

const channels: Channel[] = ["email", "linkedin", "whatsapp", "slack", "sms"];

export default function ContactDetailPage() {
  const params = useParams<{ contactId: string }>();
  const contactId = params.contactId;

  return (
    <DashboardShell>
      {(bundle) => {
        const contact = buildContactRows(bundle).find(
          (row) => row.contact_id === contactId,
        );

        if (!contact) {
          return (
            <p className="text-sm text-muted-foreground">
              Contact not found.{" "}
              <Link href="/dashboard/prospects" className="underline">
                Back to prospects
              </Link>
            </p>
          );
        }

        const profile = contact.profile;

        return (
          <div className="space-y-8">
            <div className="space-y-2">
              <Link
                href={`/dashboard/prospects/${contact.company_id}`}
                className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              >
                ← {contact.company_name}
              </Link>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold tracking-tight">
                    {contact.full_name}
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    {contact.title} · {contact.department}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline" className="capitalize">
                    {formatRole(contact.decision_role)}
                  </Badge>
                  <Badge variant="secondary" className="capitalize">
                    Prefers {contact.preferred_channel}
                  </Badge>
                  {contact.suppressed ? (
                    <Badge variant="destructive">Do not contact</Badge>
                  ) : null}
                </div>
              </div>
            </div>

            {contact.suppressed ? (
              <Card className="border-destructive/30 bg-destructive/5">
                <CardHeader>
                  <CardTitle>Outreach blocked</CardTitle>
                  <CardDescription>
                    This person is flagged do-not-contact or appears on the
                    suppression list. Drafts and sends should stay disabled.
                  </CardDescription>
                </CardHeader>
              </Card>
            ) : null}

            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Channels</CardTitle>
                  <CardDescription>
                    Handles and consent from the contact record
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <ChannelRow label="Email" value={contact.email} />
                  <ChannelRow label="Phone" value={contact.phone} />
                  <ChannelRow label="LinkedIn" value={contact.linkedin_url} />
                  <ChannelRow
                    label="WhatsApp"
                    value={contact.whatsapp_number}
                  />
                  <ChannelRow label="Slack" value={contact.slack_user_id} />
                  <div className="flex flex-wrap gap-1 pt-2">
                    {channels.map((channel) => (
                      <Badge
                        key={channel}
                        variant={
                          hasConsent(contact.consent, channel)
                            ? "secondary"
                            : "outline"
                        }
                        className="capitalize"
                      >
                        {channel}{" "}
                        {hasConsent(contact.consent, channel) ? "on" : "off"}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {profile ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Person briefing</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm text-muted-foreground">
                    <p>{profile.bio}</p>
                    <p>
                      <span className="font-medium text-foreground">
                        Style:{" "}
                      </span>
                      {profile.communication_style}
                    </p>
                    <p>
                      <span className="font-medium text-foreground">
                        Approach:{" "}
                      </span>
                      {profile.recommended_approach}
                    </p>
                  </CardContent>
                </Card>
              ) : null}
            </div>

            {profile ? (
              <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Talking points</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {profile.talking_points.length === 0 ? (
                      <p className="text-sm text-muted-foreground">None</p>
                    ) : (
                      <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
                        {profile.talking_points.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    )}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>Risks</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
                      {profile.risks.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
                <Card className="lg:col-span-2">
                  <CardHeader>
                    <CardTitle>Pain vs product</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    {profile.likely_pain_vs_product}
                  </CardContent>
                </Card>
              </div>
            ) : null}
          </div>
        );
      }}
    </DashboardShell>
  );
}

const hasConsent = (consent: ChannelConsent, channel: Channel): boolean =>
  Boolean(consent[channel]);

const ChannelRow = ({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) => (
  <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-3">
    <span className="w-24 shrink-0 text-muted-foreground">{label}</span>
    {value ? (
      value.startsWith("http") ? (
        <a
          href={value}
          target="_blank"
          rel="noreferrer"
          className="break-all underline-offset-4 hover:underline"
        >
          {value}
        </a>
      ) : (
        <span className="break-all">{value}</span>
      )
    ) : (
      <span className="text-muted-foreground">Not on file</span>
    )}
  </div>
);
