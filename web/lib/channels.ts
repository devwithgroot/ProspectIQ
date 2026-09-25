import type { Channel } from "@/lib/types"

export const CHANNELS: Channel[] = [
  "email",
  "linkedin",
  "whatsapp",
  "slack",
  "sms",
]

export const CHANNEL_LABELS: Record<Channel, string> = {
  email: "Email",
  linkedin: "LinkedIn",
  whatsapp: "WhatsApp",
  slack: "Slack",
  sms: "SMS",
}

export const CHANNEL_TITLES: Record<Channel, string> = {
  email: "Email Message",
  linkedin: "LinkedIn Message",
  whatsapp: "WhatsApp Message",
  slack: "Slack Message",
  sms: "SMS Message",
}

export const CHANNEL_LIMITS: Partial<Record<Channel, number>> = {
  linkedin: 300,
  whatsapp: 400,
  slack: 400,
  sms: 160,
}

export const CHANNEL_MISSING: Record<Channel, string> = {
  email: "no email",
  linkedin: "no profile",
  whatsapp: "no number",
  slack: "no handle",
  sms: "no number",
}
