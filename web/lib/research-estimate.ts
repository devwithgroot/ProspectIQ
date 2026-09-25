const ONBOARD_LOW_MINUTES = 1
const ONBOARD_HIGH_MINUTES = 2
const COMPANY_LOW_MINUTES = 2
const COMPANY_HIGH_MINUTES = 3.5
const TIME_BUFFER_MINUTES = 3

export type ResearchEstimate = {
  companyCount: number
  lowMinutes: number
  highMinutes: number
  typicalMinutes: number
}

export function estimateResearch(companyCount: number): ResearchEstimate {
  const count = Math.max(1, companyCount)
  const lowMinutes = Math.max(
    2,
    Math.round(ONBOARD_LOW_MINUTES + COMPANY_LOW_MINUTES * count)
  )
  const highMinutes =
    Math.max(
      lowMinutes + 1,
      Math.round(ONBOARD_HIGH_MINUTES + COMPANY_HIGH_MINUTES * count)
    ) + TIME_BUFFER_MINUTES
  return {
    companyCount: count,
    lowMinutes,
    highMinutes,
    typicalMinutes: Math.round((lowMinutes + highMinutes) / 2),
  }
}

export function formatEstimateRange(estimate: ResearchEstimate): string {
  if (estimate.lowMinutes === estimate.highMinutes) {
    return `${estimate.lowMinutes} minute${estimate.lowMinutes === 1 ? "" : "s"}`
  }
  return `${estimate.lowMinutes}–${estimate.highMinutes} minutes`
}

export function formatMinutesLeft(secondsLeft: number): string {
  const minutes = Math.max(1, Math.round(secondsLeft / 60))
  return `${minutes} minute${minutes === 1 ? "" : "s"}`
}

export function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  if (minutes === 0) {
    return `${rest}s so far`
  }
  if (rest === 0) {
    return `${minutes} minute${minutes === 1 ? "" : "s"} so far`
  }
  return `${minutes}m ${rest}s so far`
}

export function researchTimeoutMs(estimate: ResearchEstimate): number {
  return Math.max(15, estimate.highMinutes + 5) * 60 * 1000
}
