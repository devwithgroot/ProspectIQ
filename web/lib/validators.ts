import { z } from "zod"

import { isAllowedTitle, type Catalog } from "@/lib/catalog"
import type { StagedProspect, StagingPreview } from "@/lib/types"

export type BriefingDraft = {
  company_id: string
  name: string
  executive_summary: string
  overall_score: number
  recommendation: string
  key_signals: string[]
  risks: string[]
  recommended_sales_approach: string
}

export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024

const PUBLIC_EMAIL_DOMAINS = new Set([
  "gmail.com",
  "googlemail.com",
  "yahoo.com",
  "yahoo.co.in",
  "yahoo.co.uk",
  "outlook.com",
  "hotmail.com",
  "live.com",
  "msn.com",
  "icloud.com",
  "me.com",
  "mac.com",
  "aol.com",
  "proton.me",
  "protonmail.com",
  "gmx.com",
  "mail.com",
  "yandex.com",
  "rediffmail.com",
])

export const INDIA_DIAL = "+91"
export const LOCAL_PHONE_LENGTH = 10

export function isEmail(value: string): boolean {
  const text = value.trim().toLowerCase()
  return text.includes("@") && text.split("@")[1]?.includes(".") === true
}

export function sanitizeName(value: string): string {
  return value.replace(/[^\p{L}\s.'’-]/gu, "")
}

export function sanitizeEmail(value: string): string {
  return value.replace(/\s+/g, "")
}

export function localPhoneDigits(value: string): string {
  let digits = value.replace(/\D/g, "")
  if (digits.startsWith("91") && digits.length >= 12) {
    digits = digits.slice(2)
  }
  if (digits.startsWith("0")) {
    digits = digits.replace(/^0+/, "")
  }
  return digits.slice(0, LOCAL_PHONE_LENGTH)
}

export function formatIndiaPhone(value: string): string {
  return `${INDIA_DIAL}${localPhoneDigits(value)}`
}

export function validateFullName(fullName: string): string | null {
  const name = fullName.trim()
  if (!name) {
    return "Please add your name."
  }
  if (name.replace(/[^\p{L}]/gu, "").length < 2) {
    return "Please enter your full name."
  }
  return null
}

export function validatePhone(phone: string): string | null {
  const local = localPhoneDigits(phone)
  if (!local) {
    return "Please add your phone number."
  }
  if (local.length !== LOCAL_PHONE_LENGTH) {
    return "Enter a 10-digit mobile number."
  }
  if (!/^[6-9]/.test(local)) {
    return "Enter a valid Indian mobile number."
  }
  return null
}

export function validateWorkEmail(email: string): string | null {
  if (!email.trim()) {
    return "Please add your work email."
  }
  if (!isEmail(email)) {
    return "Please enter a valid work email."
  }
  return null
}

export function youFieldErrors(input: {
  fullName: string
  phone: string
  email: string
}): { fullName: string | null; phone: string | null; email: string | null } {
  return {
    fullName: validateFullName(input.fullName),
    phone: validatePhone(input.phone),
    email: validateWorkEmail(input.email),
  }
}

export function websiteFromEmail(email: string): string | null {
  if (!isEmail(email)) {
    return null
  }
  const domain = email.split("@")[1]?.trim().toLowerCase()
  if (!domain || PUBLIC_EMAIL_DOMAINS.has(domain)) {
    return null
  }
  return domain
}

export function firstIssue(error: z.ZodError): string {
  return error.issues[0]?.message ?? "Please check the form and try again."
}

export function validateOrMessage<T>(
  schema: z.ZodType<T>,
  data: unknown
): string | null {
  const result = schema.safeParse(data)
  return result.success ? null : firstIssue(result.error)
}

export const youDetailsSchema = z
  .object({
    fullName: z.string(),
    phone: z.string(),
    email: z.string(),
  })
  .superRefine((value, ctx) => {
    const errors = youFieldErrors(value)
    if (errors.fullName) {
      ctx.addIssue({
        code: "custom",
        path: ["fullName"],
        message: errors.fullName,
      })
    }
    if (errors.phone) {
      ctx.addIssue({
        code: "custom",
        path: ["phone"],
        message: errors.phone,
      })
    }
    if (errors.email) {
      ctx.addIssue({
        code: "custom",
        path: ["email"],
        message: errors.email,
      })
    }
  })

export const youStepSchema = youDetailsSchema

export function roleStepSchema(catalog: Catalog) {
  return z
    .object({
      industry: z.string().trim().min(1, "Please choose an industry from the list."),
      title: z.string().trim().min(1, "Please choose a title from the list."),
    })
    .superRefine((value, ctx) => {
      if (!isAllowedTitle(catalog, value.industry, value.title)) {
        ctx.addIssue({
          code: "custom",
          path: ["title"],
          message: `“${value.title}” isn’t used in ${value.industry}. Pick another title.`,
        })
      }
    })
}

export const companyStepSchema = z.object({
  website: z
    .string()
    .trim()
    .min(1, "Please add your company website, for example yourcompany.com."),
})

export const uploadFileSchema = z
  .custom<File>((value) => value instanceof File, {
    message: "Please upload a spreadsheet of companies.",
  })
  .superRefine((file, ctx) => {
    if (file.size > MAX_UPLOAD_BYTES) {
      ctx.addIssue({
        code: "custom",
        message: "That file is over 5 MB. Please upload a smaller list.",
      })
    }
    if (!file.name.toLowerCase().endsWith(".csv")) {
      ctx.addIssue({
        code: "custom",
        message: "Please upload a spreadsheet of companies.",
      })
    }
  })

export const stagingSchema = z.object({
  companies: z
    .array(
      z.object({
        company_name: z.string().trim().min(1, "A company is missing its name."),
      })
    )
    .min(1, "Add at least one company before starting research."),
})

export const stagedCompanySchema = z.object({
  id: z.string(),
  company_name: z.string().trim().min(1, "A company is missing its name."),
  website: z.string().nullable(),
  notes: z.string().nullable(),
}) satisfies z.ZodType<StagedProspect>

export const verifyCodeSchema = z
  .string()
  .trim()
  .regex(/^\d{6}$/, "Type the 6-digit code from that inbox.")

export const briefingSchema = z.object({
  company_id: z.string(),
  name: z.string().trim().min(1, "Please add the company name."),
  executive_summary: z.string().trim().min(1, "Please add a short summary."),
  overall_score: z.number(),
  recommendation: z.string(),
  key_signals: z
    .array(z.string().trim().min(1))
    .min(1, "Add at least one reason they look interesting."),
  risks: z.array(z.string().trim().min(1)).min(1, "Add at least one watch-out."),
  recommended_sales_approach: z
    .string()
    .trim()
    .min(1, "Please add a suggested approach."),
}) satisfies z.ZodType<BriefingDraft>

export function validateYouDetails(input: {
  fullName: string
  phone: string
  email: string
}): string | null {
  return validateOrMessage(youDetailsSchema, input)
}

export function validateYouStep(input: {
  fullName: string
  phone: string
  email: string
}): string | null {
  return validateOrMessage(youStepSchema, input)
}

export function validateRoleStep(
  catalog: Catalog,
  industry: string,
  title: string
): string | null {
  return validateOrMessage(roleStepSchema(catalog), { industry, title })
}

export function validateCompanyStep(website: string): string | null {
  return validateOrMessage(companyStepSchema, { website })
}

export function validateUploadFile(file: File | null): string | null {
  if (!file) {
    return "Please upload a spreadsheet of companies."
  }
  return validateOrMessage(uploadFileSchema, file)
}

export function filledStagedCompanies(
  staging: StagingPreview | null
): StagedProspect[] {
  return (
    staging?.companies.filter((row) => row.company_name.trim().length > 0) ?? []
  )
}

export function validateStaging(
  staging: StagingPreview | null
): string | null {
  if (filledStagedCompanies(staging).length === 0) {
    return "Add at least one company before starting research."
  }
  return null
}

export function validateProspectsStep(
  file: File | null,
  staging: StagingPreview | null
): string | null {
  if (filledStagedCompanies(staging).length > 0) {
    return null
  }
  if (file) {
    return validateUploadFile(file)
  }
  return "Add at least one company before starting research."
}

export function validateStagedCompany(row: StagedProspect): string | null {
  return validateOrMessage(stagedCompanySchema, {
    ...row,
    website: row.website?.trim() || null,
    notes: row.notes?.trim() || null,
  })
}

export function validateVerifyCode(code: string): string | null {
  return validateOrMessage(verifyCodeSchema, code)
}

export function validateBriefing(draft: BriefingDraft): string | null {
  return validateOrMessage(briefingSchema, draft)
}
