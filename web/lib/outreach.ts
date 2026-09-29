import { API_URL } from "@/lib/api"
import { formatDraftBody } from "@/lib/email-format"
import type {
  EngagementDraft,
  OutreachDraftResponse,
  ResearchResult,
} from "@/lib/types"

export async function writeOutreachDraft(input: {
  contactId: string
  jobId: string | null
  result: ResearchResult
  channel?: string
}): Promise<EngagementDraft> {
  const response = await fetch(`${API_URL}/api/outreach/draft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contact_id: input.contactId,
      job_id: input.jobId,
      result: input.result,
      channel: input.channel,
    }),
  })
  const body = (await response.json().catch(() => ({}))) as
    | OutreachDraftResponse
    | { detail?: string }
  if (!response.ok) {
    const detail =
      typeof body === "object" && body && "detail" in body
        ? String(body.detail)
        : "We couldn’t write that draft."
    throw new Error(detail)
  }
  return engagementFromResponse(body as OutreachDraftResponse)
}

export function engagementFromResponse(
  response: OutreachDraftResponse,
): EngagementDraft {
  const shown = response.drafts[0]
  return {
    contact_id: response.contact_id,
    company_id: response.company_id,
    contact_name: response.contact_name,
    channel: shown?.channel ?? "",
    subject: shown?.subject ?? "",
    body: formatDraftBody(shown?.channel ?? "", shown?.body ?? ""),
    rationale: shown?.rationale ?? "",
    status: "draft",
    skipped_reason: response.skipped_reason,
    dry_run: response.dry_run,
  }
}
