"use client"

import { useEffect, useState } from "react"
import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

import { bundledCatalog, isAllowedTitle, type Catalog } from "@/lib/catalog"
import { emptyBook, mergeBook } from "@/lib/book"
import type {
  EngagementDraft,
  ResearchJob,
  ResearchResult,
  SellerBook,
  StagingPreview,
} from "@/lib/types"
import { userNotice, type UserNotice } from "@/lib/user-message"
import {
  localPhoneDigits,
  sanitizeEmail,
  sanitizeName,
  validateCompanyStep,
  validateProspectsStep,
  validateRoleStep,
  validateYouDetails,
  validateYouStep,
  websiteFromEmail,
} from "@/lib/validators"

export const RESEARCH_STORAGE_KEY = "prospectiq-draft-v1"

export type ResearchStore = {
  step: number
  notice: UserNotice | null
  otpError: string | null
  pending: boolean
  jobId: string | null
  job: ResearchJob | null
  result: ResearchResult | null
  book: SellerBook
  engagements: Record<string, EngagementDraft>
  catalog: Catalog
  fullName: string
  phone: string
  email: string
  industry: string
  title: string
  website: string
  websiteTouched: boolean
  file: File | null
  staging: StagingPreview | null
  previewBusy: boolean
  prospectsMode: "grid" | "upload"

  showError: (raw: unknown) => void
  showOtpError: (raw: unknown) => void
  clearMessages: () => void
  validateStep: (index: number) => string | null
  setStep: (step: number | ((current: number) => number)) => void
  setNotice: (notice: UserNotice | null) => void
  setOtpError: (otpError: string | null) => void
  setPending: (pending: boolean) => void
  setJobId: (jobId: string | null) => void
  setJob: (job: ResearchJob | null) => void
  setResult: (result: ResearchResult | null) => void
  setEngagement: (draft: EngagementDraft) => void
  clearEngagements: () => void
  setCatalog: (catalog: Catalog) => void
  setFullName: (fullName: string) => void
  setPhone: (phone: string) => void
  setEmail: (email: string) => void
  setIndustry: (industry: string) => void
  setTitle: (title: string) => void
  setWebsite: (website: string) => void
  applySuggestedWebsite: () => void
  setFile: (file: File | null) => void
  setStaging: (staging: StagingPreview | null) => void
  setPreviewBusy: (previewBusy: boolean) => void
  setProspectsMode: (prospectsMode: "grid" | "upload") => void
  startOver: () => void
}

type PersistedDraft = Pick<
  ResearchStore,
  | "step"
  | "fullName"
  | "phone"
  | "email"
  | "industry"
  | "title"
  | "website"
  | "websiteTouched"
  | "staging"
  | "prospectsMode"
  | "result"
  | "book"
  | "engagements"
  | "jobId"
>

function clampStep(step: unknown): number {
  return typeof step === "number" && step >= 0 && step <= 3
    ? Math.floor(step)
    : 0
}

export const useResearchStore = create<ResearchStore>()(
  persist(
    (set, get) => ({
      step: 0,
      notice: null,
      otpError: null,
      pending: false,
      jobId: null,
      job: null,
      result: null,
      book: emptyBook(),
      engagements: {},
      catalog: bundledCatalog,
      fullName: "",
      phone: "",
      email: "",
      industry: "",
      title: "",
      website: "",
      websiteTouched: false,
      file: null,
      staging: null,
      previewBusy: false,
      prospectsMode: "grid",

      showError: (raw) => {
        const notice = userNotice(raw)
        console.error("[ProspectIQ]", notice.title, notice.message, raw)
        set({ notice })
      },
      showOtpError: (raw) => {
        const notice = userNotice(raw)
        console.error("[ProspectIQ] OTP", notice.message, raw)
        set({ otpError: notice.message })
      },
      clearMessages: () => set({ notice: null, otpError: null }),

      validateStep: (index) => {
        const state = get()
        if (index === 0) {
          return validateYouStep({
            fullName: state.fullName,
            phone: state.phone,
            email: state.email,
          })
        }
        if (index === 1) {
          return validateRoleStep(state.catalog, state.industry, state.title)
        }
        if (index === 2) {
          return validateCompanyStep(state.website)
        }
        return validateProspectsStep(state.file, state.staging)
      },

      setStep: (step) =>
        set((state) => ({
          step: typeof step === "function" ? step(state.step) : step,
        })),
      setNotice: (notice) => set({ notice }),
      setOtpError: (otpError) => set({ otpError }),
      setPending: (pending) => set({ pending }),
      setJobId: (jobId) => set({ jobId }),
      setJob: (job) => set({ job }),
      setResult: (result) =>
        set((state) => ({
          result,
          book: result ? mergeBook(state.book, result) : state.book,
        })),
      setEngagement: (draft) =>
        set((state) => ({
          engagements: {
            ...state.engagements,
            [`${draft.contact_id}:${draft.channel}`]: draft,
          },
        })),
      clearEngagements: () => set({ engagements: {} }),
      setCatalog: (catalog) => set({ catalog }),
      setFullName: (fullName) => set({ fullName: sanitizeName(fullName) }),
      setPhone: (phone) => set({ phone: localPhoneDigits(phone) }),
      setEmail: (email) =>
        set((state) => {
          const next = sanitizeEmail(email)
          return {
            email: next,
            website: state.websiteTouched
              ? state.website
              : websiteFromEmail(next) ?? "",
          }
        }),
      setIndustry: (industry) =>
        set((state) => ({
          industry,
          title:
            state.title && !isAllowedTitle(state.catalog, industry, state.title)
              ? ""
              : state.title,
        })),
      setTitle: (title) => set({ title }),
      setWebsite: (website) => set({ website, websiteTouched: true }),
      applySuggestedWebsite: () =>
        set((state) => {
          const suggested = websiteFromEmail(state.email)
          return suggested
            ? { website: suggested, websiteTouched: false }
            : {}
        }),
      setFile: (file) => set({ file }),
      setStaging: (staging) => set({ staging }),
      setPreviewBusy: (previewBusy) => set({ previewBusy }),
      setProspectsMode: (prospectsMode) => set({ prospectsMode }),
      startOver: () =>
        set({
          result: null,
          pending: false,
          jobId: null,
          job: null,
          step: 3,
        }),
    }),
    {
      name: RESEARCH_STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state): PersistedDraft => ({
        step: state.step,
        fullName: state.fullName,
        phone: state.phone,
        email: state.email,
        industry: state.industry,
        title: state.title,
        website: state.website,
        websiteTouched: state.websiteTouched,
        staging: state.staging,
        prospectsMode: state.prospectsMode,
        result: state.result,
        book: state.book,
        engagements: state.engagements,
        jobId: state.jobId,
      }),
      merge: (persisted, current) => {
        const saved = (persisted ?? {}) as Partial<PersistedDraft>
        const jobId = saved.jobId ?? null
        return {
          ...current,
          ...saved,
          step: clampStep(saved.step ?? current.step),
          file: null,
          book:
            saved.book?.companies.length
              ? saved.book
              : saved.result
                ? mergeBook(saved.book ?? emptyBook(), saved.result)
                : saved.book ?? emptyBook(),
          engagements: saved.engagements ?? {},
          jobId,
          job: null,
          pending: Boolean(jobId),
          previewBusy: false,
          notice: null,
          otpError: null,
        }
      },
    }
  )
)

export function useResearchHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const finish = () => setHydrated(true)
    if (useResearchStore.persist.hasHydrated()) {
      finish()
      return
    }
    return useResearchStore.persist.onFinishHydration(finish)
  }, [])

  return hydrated
}

export function validateCurrentYouDetails(): string | null {
  const state = useResearchStore.getState()
  return validateYouDetails({
    fullName: state.fullName,
    phone: state.phone,
    email: state.email,
  })
}
