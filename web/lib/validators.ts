import { z } from "zod"

import { isAllowedTitle, type Catalog } from "@/lib/catalog"
import type { ProspectReport, StagedProspect, StagingPreview } from "@/lib/types"

export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024

export function isEmail(value: string): boolean {
  const text = value.trim().toLowerCase()
  return text.includes("@") && text.split("@")[1]?.includes(".") === true
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
    outreachEmail: z.string(),
  })
  .superRefine((value, ctx) => {
    const missing = [
      !value.fullName.trim() && "name",
      !value.phone.trim() && "phone number",
      !value.email.trim() && "work email",
      !value.outreachEmail.trim() && "outreach email",
    ].filter((item): item is string => Boolean(item))

    if (missing.length) {
      ctx.addIssue({
        code: "custom",
        message:
          missing.length >= 3
            ? "Please add your name, phone, work email, and outreach email."
            : `Please add your ${missing.join(" and ")}.`,
      })
      return
    }
    if (!isEmail(value.email)) {
      ctx.addIssue({
        code: "custom",
        path: ["email"],
        message: "Please enter a valid work email.",
      })
    }
    if (!isEmail(value.outreachEmail)) {
      ctx.addIssue({
        code: "custom",
        path: ["outreachEmail"],
        message: "Please enter a valid outreach email.",
      })
    }
  })

export const youStepSchema = youDetailsSchema.and(
  z
    .object({
      otpRequired: z.boolean(),
      outreachVerified: z.boolean(),
    })
    .superRefine((value, ctx) => {
      if (value.otpRequired && !value.outreachVerified) {
        ctx.addIssue({
          code: "custom",
          path: ["outreachVerified"],
          message:
            "Please confirm the outreach email. We’ll send a short code there.",
        })
      }
    })
)

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
  company_name: z.string().trim().min(1, "Please add the company name."),
  executive_summary: z.string().trim().min(1, "Please add a short summary."),
  prospect_score: z.number(),
  recommendation: z.string(),
  key_signals: z
    .array(z.string().trim().min(1))
    .min(1, "Add at least one reason they look interesting."),
  risks: z.array(z.string().trim().min(1)).min(1, "Add at least one watch-out."),
  recommended_sales_approach: z
    .string()
    .trim()
    .min(1, "Please add a suggested approach."),
}) satisfies z.ZodType<ProspectReport>

export function validateYouDetails(input: {
  fullName: string
  phone: string
  email: string
  outreachEmail: string
}): string | null {
  return validateOrMessage(youDetailsSchema, input)
}

export function validateYouStep(input: {
  fullName: string
  phone: string
  email: string
  outreachEmail: string
  otpRequired: boolean
  outreachVerified: boolean
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

export function validateStaging(
  staging: StagingPreview | null
): string | null {
  if (!staging) {
    return "Add at least one company before starting research."
  }
  return validateOrMessage(stagingSchema, staging)
}

export function validateProspectsStep(
  file: File | null,
  staging: StagingPreview | null
): string | null {
  if (!file && !staging) {
    return "Please upload a spreadsheet of companies."
  }
  if (file) {
    const fileProblem = validateUploadFile(file)
    if (fileProblem) {
      return fileProblem
    }
  }
  return validateStaging(staging)
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

export function validateBriefing(report: ProspectReport): string | null {
  return validateOrMessage(briefingSchema, report)
}
