import type { ResearchJob } from "@/lib/types";

import { API_URL } from "@/lib/api";

export async function fetchResearchJob(jobId: string): Promise<ResearchJob> {
  return readResearchJob(
    await fetch(`${API_URL}/api/research/${jobId}`),
    "We couldn’t check research progress.",
  );
}

export async function cancelResearchJob(jobId: string): Promise<ResearchJob> {
  return readResearchJob(
    await fetch(`${API_URL}/api/research/${jobId}/cancel`, { method: "POST" }),
    "We couldn’t stop research.",
  );
}

export async function skipResearchCompany(jobId: string): Promise<ResearchJob> {
  return readResearchJob(
    await fetch(`${API_URL}/api/research/${jobId}/skip`, { method: "POST" }),
    "We couldn’t skip that company.",
  );
}

async function readResearchJob(
  response: Response,
  fallback: string,
): Promise<ResearchJob> {
  const payload = await response.json().catch(() => null);
  if (response.status === 404) {
    throw new Error("That research run was not found.");
  }
  if (!response.ok) {
    throw payload ?? new Error(fallback);
  }
  return payload as ResearchJob;
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
