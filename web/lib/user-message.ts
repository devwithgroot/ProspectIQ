export type UserNotice = {
  title: string
  message: string
}

const FALLBACK: UserNotice = {
  title: "Something went wrong",
  message: "Please try again in a moment. If it keeps happening, come back and start this step over.",
}

export function userNotice(raw: unknown): UserNotice {
  const text = extractText(raw)
  const lower = text.toLowerCase()

  if (!text) {
    return FALLBACK
  }

  if (looksTechnical(lower)) {
    return mapKnown(lower, text) ?? FALLBACK
  }

  return mapKnown(lower, text) ?? {
    title: "Just a moment",
    message: text,
  }
}

function extractText(raw: unknown): string {
  if (raw == null) {
    return ""
  }
  if (typeof raw === "string") {
    return raw.trim()
  }
  if (raw instanceof Error) {
    return raw.message.trim()
  }
  if (typeof raw === "object" && "detail" in raw) {
    const detail = (raw as { detail: unknown }).detail
    if (typeof detail === "string") {
      return detail.trim()
    }
    if (Array.isArray(detail)) {
      return "Please check the form and try again."
    }
  }
  return ""
}

function looksTechnical(lower: string): boolean {
  return (
    /\b(traceback|exception|fastapi|pydantic|uvicorn|status code|errno|econn|enotfound|typeerror|valueerror|keyerror|json|http\/|smtp|mlx|tavily|orchestrator|csv|company_name|required:)\b/.test(
      lower
    ) ||
    /\/[a-z0-9_\-]+\.(py|ts|tsx|js)\b/.test(lower) ||
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower.includes("aborterror")
  )
}

function mapKnown(lower: string, original: string): UserNotice | null {
  if (
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower.includes("load failed")
  ) {
    return {
      title: "We couldn’t reach the app",
      message:
        "Check that the app is running, then try this step again.",
    }
  }
  if (
    lower.includes("timeout") ||
    lower.includes("aborterror") ||
    lower.includes("timed out")
  ) {
    return {
      title: "This is taking longer than usual",
      message:
        "Research can take a few minutes. Leave this tab open and try again if nothing comes back.",
    }
  }
  if (lower.includes("email sending isn’t set up") || lower.includes("smtp")) {
    return {
      title: "We couldn’t send a code",
      message:
        "We can’t email a code right now. Try again in a moment, or continue if a code isn’t needed.",
    }
  }
  if (lower.includes("wait") && lower.includes("seconds")) {
    const wait = original.match(/\d+/)?.[0]
    return {
      title: "Please wait a moment",
      message: wait
        ? `Try again in ${wait} seconds.`
        : "A code was just sent. Wait a few seconds, then try again.",
    }
  }
  if (lower.includes("expired")) {
    return {
      title: "That code has expired",
      message: "Request a new code and enter the latest one from your inbox.",
    }
  }
  if (lower.includes("too many")) {
    return {
      title: "Too many tries",
      message: "Request a new code, then enter the latest one from your inbox.",
    }
  }
  if (
    lower.includes("doesn’t match") ||
    lower.includes("doesn't match") ||
    lower.includes("didn’t work") ||
    lower.includes("didn't work")
  ) {
    return {
      title: "That code didn’t match",
      message: "Check the latest email and try again, or send a new code.",
    }
  }
  if (lower.includes("send a code") && lower.includes("first")) {
    return {
      title: "Send a code first",
      message: "We’ll email a short code to that address before you can continue.",
    }
  }
  if (lower.includes("verify") && lower.includes("outreach")) {
    return {
      title: "Confirm the outreach email",
      message:
        "We’ll send a short code to that inbox so prospects see the right from-address.",
    }
  }
  if (lower.includes("valid work email") || (lower.includes("work email") && lower.includes("valid"))) {
    return {
      title: "Check your work email",
      message: "That doesn’t look like an email yet. Use an address like you@company.com.",
    }
  }
  if (lower.includes("valid outreach") || (lower.includes("outreach") && lower.includes("valid"))) {
    return {
      title: "Check the outreach email",
      message: "That doesn’t look like an email yet. Use an address like you@company.com.",
    }
  }
  if (lower.includes("header")) {
    return {
      title: "The first row should be column names",
      message:
        "Add a header row with company name, and optionally website and notes, then upload again.",
    }
  }
  if (lower.includes("company_name") && (lower.includes("missing") || lower.includes("row"))) {
    return {
      title: "A company is missing its name",
      message:
        "Every row needs a company name. Fill the blank rows and upload the list again.",
    }
  }
  if (lower.includes("company_name") || (lower.includes("company name") && lower.includes("column"))) {
    return {
      title: "We need a company name column",
      message:
        "The first row of your spreadsheet should include a company name column. Website and notes are optional.",
    }
  }
  if (lower.includes("does not contain any companies") || lower.includes("no companies")) {
    return {
      title: "We didn’t find any companies",
      message:
        "Add at least one company name and upload the list again.",
    }
  }
  if (lower.includes("server restarted") || lower.includes("research run was not found")) {
    return {
      title: "Research didn’t resume",
      message:
        "The last run is no longer available. Start research again from your list.",
    }
  }
  if (lower.includes("5 mb")) {
    return {
      title: "That file is too large",
      message: "Please upload a list under 5 MB.",
    }
  }
  if (
    lower.includes("upload a csv") ||
    (lower.includes("csv") && (lower.includes("file") || lower.includes("upload")))
  ) {
    return {
      title: "That file type won’t work",
      message: "Please upload a spreadsheet of companies.",
    }
  }
  if (lower.startsWith("please add") || lower.includes("please add your")) {
    return {
      title: "A few details are missing",
      message: original,
    }
  }
  if (lower.includes("6-digit") || lower.includes("enter the code")) {
    return {
      title: "Enter the code",
      message: "Type the 6-digit code from that inbox.",
    }
  }
  if (lower.includes("required:") || lower.includes(" is required")) {
    return {
      title: "A few details are missing",
      message: "Please add your name, phone, email, role, website, and company list.",
    }
  }
  if (lower.includes("not a title used") || lower.includes("isn’t used in") || lower.includes("isn't used in")) {
    return {
      title: "That title doesn’t match this industry",
      message: "Pick a title from the list for the industry you chose.",
    }
  }
  if (lower.includes("selected from the list") || lower.includes("choose an industry") || lower.includes("choose a title")) {
    return {
      title: "Pick from the list",
      message: "Industry and title have to be chosen from the suggestions.",
    }
  }
  if (lower.includes("company website") || (lower.includes("website") && lower.includes("please add"))) {
    return {
      title: "Add your company website",
      message: "A public site is enough, for example yourcompany.com.",
    }
  }
  if (lower.includes("spreadsheet") || lower.includes("company list") || lower.includes("prospect")) {
    if (lower.includes("upload") || lower.includes("review")) {
      return {
        title: "Add your company list",
        message: "Upload a spreadsheet, then review the companies before we start.",
      }
    }
  }
  if (lower.includes("couldn’t send") || lower.includes("couldn't send")) {
    return {
      title: "We couldn’t send a code",
      message: "Please try again in a moment.",
    }
  }
  if (lower.includes("couldn’t read") || lower.includes("couldn't read") || lower.includes("couldn’t finish") || lower.includes("couldn't finish")) {
    return {
      title: "We couldn’t finish that",
      message: "Please try again. If it keeps happening, upload the list once more.",
    }
  }
  return null
}
