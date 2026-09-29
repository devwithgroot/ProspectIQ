"use client";

import { useState } from "react";
import Link from "next/link";

import { EngageDialog } from "@/components/engage-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { composeMetaFor, engagementKey } from "@/lib/book";
import { CHANNEL_LABELS } from "@/lib/channels";
import {
  useResearchHydrated,
  useResearchStore,
} from "@/lib/research-store";
import type { Channel, EngagementStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const statusLabel: Record<EngagementStatus, string> = {
  draft: "Draft",
  approved: "Approved",
  sent: "Sent (dry-run)",
};

export function Engagements() {
  const hydrated = useResearchHydrated();
  const book = useResearchStore((state) => state.book);
  const engagements = useResearchStore((state) => state.engagements);
  const notice = useResearchStore((state) => state.notice);
  const setEngagement = useResearchStore((state) => state.setEngagement);
  const [openKey, setOpenKey] = useState<string | null>(null);
  const drafts = Object.values(engagements);
  const openDraft = openKey ? engagements[openKey] ?? null : null;

  if (!hydrated) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-6 py-8 sm:py-10">
        <h1 className="font-heading text-2xl tracking-tight sm:text-3xl">
          Engagements
        </h1>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-6 py-8 sm:py-10">
      <div className="space-y-2">
        <h1 className="font-heading text-2xl tracking-tight sm:text-3xl">
          Engagements
        </h1>
        <p className="max-w-xl text-sm leading-6 text-muted-foreground">
          Drafts you write from Companies land here. Pick a person and a
          channel — email, LinkedIn, Slack, WhatsApp, or SMS.
        </p>
      </div>

      {notice ? (
        <Alert variant="destructive">
          <AlertTitle>{notice.title}</AlertTitle>
          <AlertDescription>{notice.message}</AlertDescription>
        </Alert>
      ) : null}

      {drafts.length === 0 ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {book.companies.length
              ? "No drafts yet. Open a company, pick a person, then choose how to engage."
              : "Research a company first, then come here after you write a draft."}
          </p>
          <Link
            href={book.companies.length ? "/companies" : "/"}
            className={cn(buttonVariants(), "w-fit")}
          >
            {book.companies.length ? "Open companies" : "Go to research"}
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {drafts.map((draft) => (
            <li key={engagementKey(draft.contact_id, draft.channel)}>
              <button
                type="button"
                className="flex w-full items-start justify-between gap-3 rounded-xl px-4 py-3 text-left ring-1 ring-foreground/10 hover:bg-muted/40"
                onClick={() =>
                  setOpenKey(engagementKey(draft.contact_id, draft.channel))
                }
              >
                <div>
                  <p className="font-medium">
                    {draft.contact_name} ·{" "}
                    {CHANNEL_LABELS[(draft.channel || "email") as Channel]}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {draft.subject || draft.body.slice(0, 80)}
                  </p>
                </div>
                <Badge variant="outline">{statusLabel[draft.status]}</Badge>
              </button>
            </li>
          ))}
        </ul>
      )}

      <EngageDialog
        draft={openDraft}
        compose={
          openDraft
            ? composeMetaFor(
                book,
                book.contacts.find(
                  (item) => item.contact_id === openDraft.contact_id,
                ) ?? null,
                openDraft.contact_name,
              )
            : null
        }
        onClose={() => setOpenKey(null)}
        onChange={setEngagement}
      />
    </div>
  );
}
