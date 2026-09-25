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
  const minutes = Math.max(1, Math.floor(secondsLeft / 60))
  return `${minutes} minute${minutes === 1 ? "" : "s"}`
}

export function remainingSeconds(
  elapsedSeconds: number,
  typicalMinutes: number,
  percent: number | null = null
): number {
  const typicalSeconds = Math.max(60, typicalMinutes * 60)
  const clockLeft = Math.max(0, typicalSeconds - elapsedSeconds)
  if (percent != null && percent >= 88) {
    return Math.min(clockLeft, 75)
  }
  return clockLeft
}

export function formatTimeLeft(
  elapsedSeconds: number,
  typicalMinutes: number,
  percent: number | null = null
): string | null {
  if (elapsedSeconds < 1 && (percent == null || percent < 1)) {
    return null
  }
  const remaining = remainingSeconds(elapsedSeconds, typicalMinutes, percent)
  if (percent != null && percent >= 92 && remaining <= 150) {
    return "Wrapping up"
  }
  if (remaining <= 45) {
    return "About a minute left"
  }
  return `About ${formatMinutesLeft(remaining)} left`
}

export function researchPhases(companyNames: string[]): string[] {
  const names = companyNames.map((name) => name.trim()).filter(Boolean)
  const list = names.length ? names : ["this company"]
  const phases = [
    "Thinking",
    "Reading your company website",
    "Learning what you sell",
  ]
  for (const name of list) {
    phases.push(`Searching public sources for ${name}`)
    phases.push(`Reading what we found on ${name}`)
    phases.push(`Writing the briefing for ${name}`)
  }
  phases.push("Putting the briefings together")
  return phases
}

export type ResearchActivity = {
  percent: number | null
  timeLeft: string | null
  done: string[]
  current: string
}

export function researchActivity(
  elapsedSeconds: number,
  companyNames: string[],
  typicalMinutes: number
): ResearchActivity {
  const phases = researchPhases(companyNames)
  const typicalSeconds = Math.max(60, typicalMinutes * 60)
  const started = elapsedSeconds >= 1
  const ratio = Math.min(0.999, Math.max(0, elapsedSeconds / typicalSeconds))
  const index = started
    ? Math.min(phases.length - 1, Math.floor(ratio * phases.length))
    : 0
  const keep = Math.min(4, index)

  const percent = started
    ? Math.min(92, Math.max(1, Math.round(ratio * 92)))
    : null
  return {
    percent,
    timeLeft: formatTimeLeft(elapsedSeconds, typicalMinutes, percent),
    done: phases.slice(Math.max(0, index - keep), index),
    current: phases[index] ?? "Thinking",
  }
}

export function activityFromJob(
  job: {
    current: string
    done: string[]
    percent: number
    started_at: string
  },
  typicalMinutes: number,
  nowMs: number = Date.now()
): ResearchActivity {
  const startedAt = Date.parse(job.started_at)
  const elapsedSeconds = Number.isNaN(startedAt)
    ? 0
    : Math.max(0, Math.floor((nowMs - startedAt) / 1000))
  const percent =
    job.percent > 0 ? Math.min(100, job.percent) : elapsedSeconds >= 1 ? 1 : null

  return {
    percent,
    timeLeft: formatTimeLeft(elapsedSeconds, typicalMinutes, percent),
    done: job.done.slice(-16),
    current: job.current || "Opening your website",
  }
}

export function waitingHint(current: string, elapsedSeconds: number): string {
  const text = current.toLowerCase()
  let lines = [
    "Still working on this",
    "This usually takes a minute",
    "Hang tight",
  ]
  if (
    text.includes("website") ||
    text.includes("page") ||
    text.includes("opening") ||
    text.includes("your site")
  ) {
    lines = [
      "Opening the page",
      "Reading what’s on it",
      "This can take a minute",
    ]
  } else if (
    text.includes("sell") ||
    text.includes("offer") ||
    text.includes("product")
  ) {
    lines = [
      "Learning what your company does",
      "Picking out what you sell",
      "Still reading your offer",
    ]
  } else if (text.startsWith("why:") || text.includes("because")) {
    lines = [
      "Working out why this matters",
      "Still going through what we found",
      "Putting this in plain language",
    ]
  } else if (
    text.includes("choosing") ||
    text.includes("look up") ||
    text.includes("thinking")
  ) {
    lines = [
      "Reviewing what we already have",
      "Choosing what to look up next",
      "This step is still running",
    ]
  } else if (text.includes("looking up") || text.includes("searching")) {
    lines = [
      "Looking this up online",
      "Collecting public articles",
      "Still searching",
    ]
  } else if (text.includes("found") || text.includes("reading ")) {
    lines = [
      "Opening that article",
      "Checking if it helps the pitch",
      "Reading it now",
    ]
  } else if (text.includes("rating") || text.includes("scored") || text.includes("fit")) {
    lines = [
      "Rating growth, hiring, and fit",
      "Weighing what we found",
      "Still scoring this company",
    ]
  } else if (text.includes("briefing") || text.includes("writing")) {
    lines = [
      "Drafting the summary",
      "Listing signals and risks",
      "Still writing the briefing",
    ]
  }
  const tick = Math.max(0, Math.floor(elapsedSeconds / 4))
  return lines[tick % lines.length]
}

export function researchTimeoutMs(estimate: ResearchEstimate): number {
  return Math.max(15, estimate.highMinutes + 5) * 60 * 1000
}
