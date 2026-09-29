const GREETING =
  /^(hi|hello|hey|dear)\s+[^,.\n—–]{1,80}?\s*[,—–]/i
const SIGN_OFF =
  /\b(best regards|kind regards|warm regards|regards|thanks|thank you|sincerely|best),?\s+/i
const STOP = /reply stop/i

export function formatDraftBody(_channel: string, body: string): string {
  return formatEmailBody(body)
}

export function formatEmailBody(body: string): string {
  const text = body.replace(/\r\n/g, "\n").replace(/[ \t]+/g, " ").trim()
  if (!text) {
    return ""
  }
  if (/\n\s*\n/.test(body)) {
    return body.replace(/\r\n/g, "\n").trim()
  }

  let rest = text
  const parts: string[] = []
  const greet = rest.match(GREETING)
  if (greet) {
    parts.push(normalizeGreeting(greet[0]))
    rest = capitalize(rest.slice(greet[0].length).trim())
  }

  let stop = ""
  const stopAt = rest.search(STOP)
  if (stopAt >= 0) {
    stop = rest.slice(stopAt).trim()
    rest = rest.slice(0, stopAt).trim()
  }

  let signoff = ""
  const sign = rest.match(SIGN_OFF)
  if (sign && sign.index != null) {
    signoff = formatSignOff(rest.slice(sign.index).trim())
    rest = rest.slice(0, sign.index).trim()
  }

  parts.push(...splitParagraphs(rest))
  if (signoff) {
    parts.push(signoff)
  }
  if (stop) {
    parts.push(stop)
  }
  return parts.filter(Boolean).join("\n\n")
}

function capitalize(text: string): string {
  if (!text) {
    return text
  }
  return text[0].toUpperCase() + text.slice(1)
}

function normalizeGreeting(raw: string): string {
  const trimmed = raw.trim()
  if (/[,—–]$/.test(trimmed)) {
    return trimmed.replace(/\s*[,—–]$/, ",")
  }
  return trimmed
}

function formatSignOff(block: string): string {
  const email = block.match(/[\w.+-]+@[\w.-]+/)
  const label = block.match(
    /^(best regards|kind regards|warm regards|regards|thanks|thank you|sincerely|best),?/i,
  )
  if (!label) {
    return block
  }
  let leftover = block.slice(label[0].length).trim()
  if (email) {
    leftover = leftover.replace(email[0], "").trim()
  }
  return [label[1].replace(/^\w/, (ch) => ch.toUpperCase()) + ",", leftover, email?.[0]]
    .filter(Boolean)
    .join("\n")
}

function splitParagraphs(text: string): string[] {
  if (!text) {
    return []
  }
  const sentences = text.split(/(?<=[.!?])\s+/).filter(Boolean)
  const chunks: string[] = []
  let buffer: string[] = []
  for (const sentence of sentences) {
    buffer.push(sentence)
    if (buffer.join(" ").length >= 160) {
      chunks.push(buffer.join(" "))
      buffer = []
    }
  }
  if (buffer.length) {
    chunks.push(buffer.join(" "))
  }
  return chunks
}
