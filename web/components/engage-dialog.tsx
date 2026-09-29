"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { CHANNEL_LIMITS, CHANNEL_TITLES } from "@/lib/channels";
import { formatDraftBody } from "@/lib/email-format";
import type { Channel, ComposeMeta, EngagementDraft } from "@/lib/types";
import { cn } from "@/lib/utils";

export type { ComposeMeta };

const HEADER: Record<Channel, string> = {
  email: "bg-muted/80",
  linkedin: "bg-[#0A66C2] text-white",
  whatsapp: "bg-[#075E54] text-white",
  slack: "bg-[#350d36] text-white",
  sms: "bg-muted/80",
};

const SEND: Partial<Record<Channel, string>> = {
  linkedin: "bg-[#0A66C2] hover:bg-[#004182]",
  whatsapp: "bg-[#075E54] hover:bg-[#054C44]",
  slack: "bg-[#007a5a] hover:bg-[#148567]",
  sms: "bg-[#0A84FF] hover:bg-[#0066D6]",
};

export function EngageDialog({
  draft,
  compose,
  onClose,
  onChange,
}: {
  draft: EngagementDraft | null;
  compose?: ComposeMeta | null;
  onClose: () => void;
  onChange: (next: EngagementDraft) => void;
}) {
  const channel = (draft?.channel || "email") as Channel;
  const darkChrome =
    channel === "linkedin" || channel === "whatsapp" || channel === "slack";

  useEffect(() => {
    if (!draft?.body) {
      return;
    }
    const next = formatDraftBody(draft.channel, draft.body);
    if (next !== draft.body) {
      onChange({ ...draft, body: next });
    }
  }, [draft, onChange]);

  return (
    <Dialog open={draft !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="max-w-2xl gap-0 overflow-hidden p-0"
        closeClassName={
          darkChrome
            ? "text-white/80 hover:bg-white/15 hover:text-white"
            : undefined
        }
      >
        {draft ? (
          <ComposeFrame
            channel={channel}
            draft={draft}
            compose={compose}
            onClose={onClose}
            onChange={onChange}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function ComposeFrame({
  channel,
  draft,
  compose,
  onClose,
  onChange,
}: ComposeProps & { channel: Channel }) {
  const locked = draft.status === "sent";
  const fields = composeFields(channel, draft, compose);
  const limit = CHANNEL_LIMITS[channel];

  return (
    <div className="flex max-h-[85vh] flex-col">
      <div className={cn("px-4 py-2.5 pr-12", HEADER[channel])}>
        <DialogTitle
          className={cn(
            "text-sm font-medium",
            darkTitle(channel) && "text-white",
          )}
        >
          {CHANNEL_TITLES[channel]}
        </DialogTitle>
        <DialogDescription className="sr-only">
          {draft.skipped_reason || `${CHANNEL_TITLES[channel]} draft`}
        </DialogDescription>
      </div>

      <div className="divide-y">
        <ComposeRow label="From" value={fields.from} />
        <ComposeRow label="To" value={fields.to} />
        {channel === "email" ? (
          <label className="flex items-center gap-3 px-4 py-2">
            <span className="w-14 shrink-0 text-xs text-muted-foreground">
              Subject
            </span>
            <input
              id="engagement-subject"
              value={draft.subject}
              disabled={locked}
              onChange={(event) =>
                updateDraft(onChange, draft, { subject: event.target.value })
              }
              className="min-w-0 flex-1 bg-transparent text-sm outline-none disabled:opacity-60"
            />
          </label>
        ) : null}
      </div>

      <textarea
        id="engagement-body"
        value={draft.body}
        disabled={locked || !draft.body}
        onChange={(event) =>
          updateDraft(onChange, draft, { body: event.target.value })
        }
        className="min-h-[280px] flex-1 resize-none overflow-y-auto border-0 bg-transparent px-4 py-3 text-sm leading-7 outline-none disabled:opacity-60"
      />

      {limit ? (
        <div className="px-4">
          <CharCount body={draft.body} limit={limit} />
        </div>
      ) : null}

      <ComposeActions
        draft={draft}
        onClose={onClose}
        onChange={onChange}
        sendClassName={SEND[channel]}
      />
    </div>
  );
}

function composeFields(
  channel: Channel,
  draft: EngagementDraft,
  compose?: ComposeMeta | null,
): { from: string; to: string } {
  const name = compose?.toName || draft.contact_name;
  const fromName = compose?.fromName || "You";
  if (channel === "email") {
    return {
      from: formatAddress(compose?.fromName ?? "", compose?.fromEmail ?? null),
      to: formatAddress(name, compose?.toEmail ?? null),
    };
  }
  if (channel === "linkedin") {
    return {
      from: [fromName, compose?.fromTitle].filter(Boolean).join(" · "),
      to: [name, compose?.toTitle || "LinkedIn member"].filter(Boolean).join(" · "),
    };
  }
  if (channel === "whatsapp") {
    const handle = compose?.toWhatsapp || compose?.toPhone;
    return {
      from: [fromName, compose?.fromCompany].filter(Boolean).join(" · "),
      to: handle ? `${name} · ${handle}` : name,
    };
  }
  if (channel === "slack") {
    return {
      from: [fromName, compose?.fromCompany].filter(Boolean).join(" · "),
      to: [
        `@${compose?.toSlack || handleize(name)}`,
        compose?.toTitle,
      ]
        .filter(Boolean)
        .join(" · "),
    };
  }
  const phone = compose?.toPhone;
  return {
    from: [fromName, compose?.fromCompany].filter(Boolean).join(" · "),
    to: phone ? `${name} · ${phone}` : name,
  };
}

function darkTitle(channel: Channel): boolean {
  return channel === "linkedin" || channel === "whatsapp" || channel === "slack";
}

type ComposeProps = {
  draft: EngagementDraft
  compose?: ComposeMeta | null
  onClose: () => void
  onChange: (next: EngagementDraft) => void
}

function ComposeActions({
  draft,
  onClose,
  onChange,
  sendClassName,
}: {
  draft: EngagementDraft
  onClose: () => void
  onChange: (next: EngagementDraft) => void
  sendClassName?: string
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-t px-4 py-3">
      <p className="text-xs text-muted-foreground">
        {draft.skipped_reason || "Dry-run. Nothing is sent."}
      </p>
      <div className="flex gap-2">
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          Discard
        </Button>
        {draft.body && !draft.skipped_reason ? (
          draft.status === "sent" ? (
            <Button type="button" size="sm" disabled>
              Sent
            </Button>
          ) : draft.status === "approved" ? (
            <Button
              type="button"
              size="sm"
              className={sendClassName}
              onClick={() => onChange({ ...draft, status: "sent" })}
            >
              Send
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              className={sendClassName}
              onClick={() => onChange({ ...draft, status: "approved" })}
            >
              Approve
            </Button>
          )
        ) : null}
      </div>
    </div>
  );
}

function ComposeRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 text-sm">
      <span className="w-14 shrink-0 text-xs text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate">{value || "Not on file"}</span>
    </div>
  );
}

function CharCount({
  body,
  limit,
}: {
  body: string
  limit: number
}) {
  const over = body.length > limit;
  return (
    <p
      className={cn(
        "mb-1 text-right text-[11px] text-muted-foreground",
        over && "font-medium text-destructive",
      )}
    >
      {body.length}/{limit}
    </p>
  );
}

function formatAddress(name: string, email: string | null): string {
  if (name && email) {
    return `${name} <${email}>`;
  }
  return email || name || "Not on file";
}

function handleize(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, ".").replace(/^\.|\.$/g, "") || "contact";
}

function updateDraft(
  onChange: (next: EngagementDraft) => void,
  draft: EngagementDraft,
  patch: Partial<EngagementDraft>,
) {
  onChange({
    ...draft,
    ...patch,
    status: draft.status === "sent" ? "sent" : "draft",
  });
}
