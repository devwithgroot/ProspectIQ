const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export type AppSettings = {
  otp_required: boolean
}

export async function fetchSettings(): Promise<AppSettings> {
  try {
    const response = await fetch(`${API_URL}/api/settings`)
    if (!response.ok) {
      return { otp_required: false }
    }
    const payload = await response.json()
    return { otp_required: payload.otp_required === true }
  } catch {
    return { otp_required: false }
  }
}
