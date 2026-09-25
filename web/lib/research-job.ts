import type { ResearchJob } from "@/lib/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function fetchResearchJob(jobId: string): Promise<ResearchJob> {
  const response = await fetch(`${API_URL}/api/research/${jobId}`)
  const payload = await response.json().catch(() => null)
  if (response.status === 404) {
    throw new Error("That research run was not found.")
  }
  if (!response.ok) {
    throw payload ?? new Error("We couldn’t check research progress.")
  }
  return payload as ResearchJob
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}
