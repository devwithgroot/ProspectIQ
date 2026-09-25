"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { EngageDialog } from "@/components/engage-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { bookToResult, composeMetaFor, contactHandle, engagementKey } from "@/lib/book";
import { CHANNEL_LABELS, CHANNEL_MISSING, CHANNELS } from "@/lib/channels";
import { writeOutreachDraft } from "@/lib/outreach";
import {
  useResearchHydrated,
  useResearchStore,
} from "@/lib/research-store";
import type { Channel, Contact, EngagementDraft } from "@/lib/types";
import { cn } from "@/lib/utils";

export function CompaniesIndex() {
  const hydrated = useResearchHydrated();
  const book = useResearchStore((state) => state.book);

  if (!hydrated) {
    return <PageFrame title="Companies" />;
  }

  if (book.companies.length === 0 && !book.user) {
    return (
      <PageFrame
        title="Companies"
        copy="Research a list once. Those companies stay here with their people and briefings."
      >
        <Link href="/" className={cn(buttonVariants(), "w-fit")}>
          Go to research
        </Link>
      </PageFrame>
    );
  }

  const rows = book.companies
    .map((company) => {
      const profile = book.company_profiles.find(
        (item) => item.company_id === company.company_id,
      );
      const people = book.contacts.filter(
        (contact) => contact.company_id === company.company_id,
      );
      return { company, profile, people };
    })
    .sort(
      (a, b) =>
        (b.profile?.overall_score ?? 0) - (a.profile?.overall_score ?? 0),
    );

  return (
    <PageFrame
      title="Companies"
      copy={
        rows.length
          ? `${rows.length} compan${rows.length === 1 ? "y" : "ies"} you’ve already researched. Your company stays saved too, so we don’t read the site again.`
          : "Your company is saved. Research a prospect list to add companies here."
      }
    >
      {book.user ? (
        <Card>
          <CardHeader>
            <CardTitle>Your company</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm leading-6">
            <p className="font-medium">
              {book.user.company.name} · {book.user.full_name}
            </p>
            <p className="text-muted-foreground">
              {book.user.company.description}
            </p>
            <p className="text-muted-foreground">{book.user.company.website}</p>
            {book.products.length ? (
              <div>
                <p className="font-medium">What you sell</p>
                <ul className="list-disc pl-5 text-muted-foreground">
                  {book.products.map((product) => (
                    <li key={product.product_id}>{product.name}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
      <div className="space-y-3">
        {rows.map(({ company, profile, people }) => (
          <Link
            key={company.company_id}
            href={`/companies/${company.company_id}`}
            className="block rounded-xl ring-1 ring-foreground/10 transition-colors hover:bg-muted/40"
          >
            <div className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-medium">{company.name}</p>
                <p className="text-sm text-muted-foreground">
                  {company.industry || "Company"}
                  {company.website ? ` · ${company.website}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {profile ? (
                  <>
                    <Badge variant="outline">{profile.recommendation}</Badge>
                    <span className="text-sm font-medium tabular-nums">
                      {profile.overall_score.toFixed(0)}
                    </span>
                  </>
                ) : null}
                <span className="text-sm text-muted-foreground">
                  {people.length} {people.length === 1 ? "person" : "people"}
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </PageFrame>
  );
}

export function CompanyDetail() {
  const params = useParams<{ companyId: string }>();
  const hydrated = useResearchHydrated();
  const book = useResearchStore((state) => state.book);
  const companyId = params.companyId;

  if (!hydrated) {
    return <PageFrame title="Company" />;
  }

  const company = book.companies.find((item) => item.company_id === companyId);
  const profile = book.company_profiles.find(
    (item) => item.company_id === companyId,
  );
  const people = book.contacts.filter((item) => item.company_id === companyId);

  if (!company) {
    return (
      <PageFrame title="Company">
        <p className="text-sm text-muted-foreground">
          That company isn’t in your book yet.{" "}
          <Link href="/companies" className="underline">
            Back to companies
          </Link>
        </p>
      </PageFrame>
    );
  }

  const signals = (profile?.signals ?? []).map((signal) => signal.description);

  return (
    <PageFrame title={company.name}>
      <Link
        href="/companies"
        className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
      >
        ← Companies
      </Link>
      {profile ? (
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">
            Score {profile.overall_score.toFixed(0)}
          </Badge>
          <Badge variant="outline">{profile.recommendation}</Badge>
        </div>
      ) : null}

      {profile ? (
        <Card>
          <CardHeader>
            <CardTitle>Company briefing</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm leading-6">
            <p>{profile.executive_summary}</p>
            {profile.why_relevant_to_user ? (
              <p>
                <span className="font-medium">Why they look interesting. </span>
                {profile.why_relevant_to_user}
              </p>
            ) : null}
            {signals.length ? (
              <ListBlock title="Signals" items={signals} />
            ) : null}
            {(profile.pain_points?.length || profile.risks.length) ? (
              <ListBlock
                title="Watch-outs"
                items={profile.pain_points?.length ? profile.pain_points : profile.risks}
              />
            ) : null}
            <p>
              <span className="font-medium">Suggested approach. </span>
              {profile.recommended_sales_approach}
            </p>
          </CardContent>
        </Card>
      ) : null}

      <section className="space-y-3">
        <h2 className="font-heading text-lg">People</h2>
        {people.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No people listed for this company yet.
          </p>
        ) : (
          <div className="space-y-3">
            {people.map((contact) => {
              const person = book.contact_profiles.find(
                (item) => item.contact_id === contact.contact_id,
              );
              return (
                <Link
                  key={contact.contact_id}
                  href={`/companies/${company.company_id}/${contact.contact_id}`}
                  className="block rounded-xl ring-1 ring-foreground/10 transition-colors hover:bg-muted/40"
                >
                  <div className="space-y-1 px-4 py-3">
                    <p className="font-medium">
                      {contact.full_name}
                      {contact.title ? ` · ${contact.title}` : ""}
                    </p>
                    {person?.bio ? (
                      <p className="text-sm text-muted-foreground">
                        {person.bio}
                      </p>
                    ) : null}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </PageFrame>
  );
}

export function ContactDetail() {
  const params = useParams<{ companyId: string; contactId: string }>();
  const hydrated = useResearchHydrated();
  const book = useResearchStore((state) => state.book);
  const jobId = useResearchStore((state) => state.jobId);
  const engagements = useResearchStore((state) => state.engagements);
  const setEngagement = useResearchStore((state) => state.setEngagement);
  const showError = useResearchStore((state) => state.showError);
  const notice = useResearchStore((state) => state.notice);
  const [busy, setBusy] = useState<Channel | null>(null);
  const [openKey, setOpenKey] = useState<string | null>(null);

  if (!hydrated) {
    return <PageFrame title="Contact" />;
  }

  const company = book.companies.find(
    (item) => item.company_id === params.companyId,
  );
  const contact = book.contacts.find(
    (item) => item.contact_id === params.contactId,
  );
  const companyProfile = book.company_profiles.find(
    (item) => item.company_id === params.companyId,
  );
  const profile = book.contact_profiles.find(
    (item) => item.contact_id === params.contactId,
  );
  const result = bookToResult(book);
  const openDraft = openKey ? engagements[openKey] ?? null : null;

  if (!company || !contact) {
    return (
      <PageFrame title="Contact">
        <p className="text-sm text-muted-foreground">
          That person isn’t in your book yet.{" "}
          <Link href="/companies" className="underline">
            Back to companies
          </Link>
        </p>
      </PageFrame>
    );
  }

  async function writeDraft(channel: Channel) {
    if (!result) {
      return;
    }
    setBusy(channel);
    try {
      const draft = await writeOutreachDraft({
        contactId: contact.contact_id,
        jobId,
        result,
        channel,
      });
      setEngagement(draft);
      setOpenKey(engagementKey(draft.contact_id, draft.channel));
    } catch (error) {
      showError(error);
    } finally {
      setBusy(null);
    }
  }

  return (
    <PageFrame title={contact.full_name}>
      {notice ? (
        <Alert variant="destructive">
          <AlertTitle>{notice.title}</AlertTitle>
          <AlertDescription>{notice.message}</AlertDescription>
        </Alert>
      ) : null}
      <Link
        href={`/companies/${company.company_id}`}
        className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
      >
        ← {company.name}
      </Link>
      <p className="text-sm text-muted-foreground">
        {contact.title}
        {contact.department ? ` · ${contact.department}` : ""}
      </p>

      {companyProfile ? (
        <Card>
          <CardHeader>
            <CardTitle>Company briefing</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm leading-6 text-muted-foreground">
            <p>{companyProfile.executive_summary}</p>
            <p>
              <span className="font-medium text-foreground">Approach. </span>
              {companyProfile.recommended_sales_approach}
            </p>
          </CardContent>
        </Card>
      ) : null}

      {profile ? (
        <Card>
          <CardHeader>
            <CardTitle>Person briefing</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-6">
            <p>{profile.bio}</p>
            {profile.communication_style ? (
              <p>
                <span className="font-medium">Style. </span>
                {profile.communication_style}
              </p>
            ) : null}
            {profile.likely_pain_vs_product ? (
              <p>
                <span className="font-medium">Pain vs product. </span>
                {profile.likely_pain_vs_product}
              </p>
            ) : null}
            <p>
              <span className="font-medium">Approach. </span>
              {profile.recommended_approach}
            </p>
            {profile.talking_points.length ? (
              <ListBlock title="Talking points" items={profile.talking_points} />
            ) : null}
            {profile.risks?.length ? (
              <ListBlock title="Risks" items={profile.risks} />
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Engage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {contact.do_not_contact ? (
            <p className="text-sm text-destructive">
              This person is marked do-not-contact.
            </p>
          ) : (
            <ChannelPicker
              contact={contact}
              busy={busy}
              drafts={engagements}
              onWrite={writeDraft}
              onOpen={(channel) =>
                setOpenKey(engagementKey(contact.contact_id, channel))
              }
            />
          )}
        </CardContent>
      </Card>

      <EngageDialog
        draft={openDraft}
        compose={composeMetaFor(book, contact)}
        onClose={() => setOpenKey(null)}
        onChange={setEngagement}
      />
    </PageFrame>
  );
}

function ChannelPicker({
  contact,
  busy,
  drafts,
  onWrite,
  onOpen,
}: {
  contact: Contact;
  busy: Channel | null;
  drafts: Record<string, EngagementDraft>;
  onWrite: (channel: Channel) => void;
  onOpen: (channel: Channel) => void;
}) {
  return (
    <div className="space-y-2">
      <p className="text-sm text-muted-foreground">
        Pick how you want to reach {contact.full_name.split(" ")[0]}. We’ll
        write one draft for that channel.
      </p>
      <div className="flex flex-wrap gap-2">
        {CHANNELS.map((channel) => {
          const handle = contactHandle(contact, channel);
          const draft = drafts[engagementKey(contact.contact_id, channel)];
          const preferred = contact.preferred_channel === channel;
          return (
            <Button
              key={channel}
              type="button"
              variant="outline"
              size="sm"
              disabled={busy === channel}
              onClick={() => (draft ? onOpen(channel) : onWrite(channel))}
            >
              {busy === channel
                ? "Writing…"
                : draft
                  ? `${CHANNEL_LABELS[channel]} · ${draft.status}`
                  : handle
                    ? CHANNEL_LABELS[channel]
                    : `${CHANNEL_LABELS[channel]} · ${CHANNEL_MISSING[channel]}`}
              {preferred ? (
                <span className="ml-1 text-[11px] text-muted-foreground">
                  · preferred
                </span>
              ) : null}
            </Button>
          );
        })}
      </div>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="font-medium">{title}</p>
      <ul className="list-disc pl-5 text-muted-foreground">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function PageFrame({
  title,
  copy,
  children,
}: {
  title: string;
  copy?: string;
  children?: ReactNode;
}) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-6 py-8 sm:py-10">
      <div className="space-y-2">
        <h1 className="font-heading text-2xl tracking-tight sm:text-3xl">
          {title}
        </h1>
        {copy ? (
          <p className="max-w-xl text-sm leading-6 text-muted-foreground">
            {copy}
          </p>
        ) : null}
      </div>
      {children}
    </div>
  );
}
