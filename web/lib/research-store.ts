"use client"

import { create } from "zustand"

import { bundledCatalog, isAllowedTitle, type Catalog } from "@/lib/catalog"
import type { ResearchResult, StagingPreview } from "@/lib/types"
import { userNotice, type UserNotice } from "@/lib/user-message"
import {
  validateCompanyStep,
  validateProspectsStep,
  validateRoleStep,
  validateYouDetails,
  validateYouStep,
} from "@/lib/validators"

export type ResearchStore = {
  step: number
  notice: UserNotice | null
  otpError: string | null
  pending: boolean
  result: ResearchResult | null
  catalog: Catalog
  otpRequired: boolean
  fullName: string
  phone: string
  email: string
  outreachEmail: string
  differentOutreach: boolean
  outreachVerified: boolean
  otpOpen: boolean
  verifyCode: string
  verifyBusy: boolean
  industry: string
  title: string
  website: string
  file: File | null
  staging: StagingPreview | null
  previewBusy: boolean

  outreach: () => string
  showError: (raw: unknown) => void
  showOtpError: (raw: unknown) => void
  clearMessages: () => void
  validateStep: (index: number) => string | null
  setStep: (step: number | ((current: number) => number)) => void
  setNotice: (notice: UserNotice | null) => void
  setOtpError: (otpError: string | null) => void
  setPending: (pending: boolean) => void
  setResult: (result: ResearchResult | null) => void
  setCatalog: (catalog: Catalog) => void
  setOtpRequired: (otpRequired: boolean) => void
  setFullName: (fullName: string) => void
  setPhone: (phone: string) => void
  setEmail: (email: string) => void
  setOutreachEmail: (outreachEmail: string) => void
  setDifferentOutreach: (differentOutreach: boolean) => void
  setOutreachVerified: (outreachVerified: boolean) => void
  setOtpOpen: (otpOpen: boolean) => void
  setVerifyCode: (verifyCode: string) => void
  setVerifyBusy: (verifyBusy: boolean) => void
  setIndustry: (industry: string) => void
  setTitle: (title: string) => void
  setWebsite: (website: string) => void
  setFile: (file: File | null) => void
  setStaging: (staging: StagingPreview | null) => void
  setPreviewBusy: (previewBusy: boolean) => void
  startOver: () => void
}

export const useResearchStore = create<ResearchStore>((set, get) => ({
  step: 0,
  notice: null,
  otpError: null,
  pending: false,
  result: null,
  catalog: bundledCatalog,
  otpRequired: false,
  fullName: "",
  phone: "",
  email: "",
  outreachEmail: "",
  differentOutreach: false,
  outreachVerified: false,
  otpOpen: false,
  verifyCode: "",
  verifyBusy: false,
  industry: "",
  title: "",
  website: "",
  file: null,
  staging: null,
  previewBusy: false,

  outreach: () => {
    const state = get()
    return (state.differentOutreach ? state.outreachEmail : state.email).trim()
  },

  showError: (raw) => set({ notice: userNotice(raw) }),
  showOtpError: (raw) => set({ otpError: userNotice(raw).message }),
  clearMessages: () => set({ notice: null, otpError: null }),

  validateStep: (index) => {
    const state = get()
    if (index === 0) {
      return validateYouStep({
        fullName: state.fullName,
        phone: state.phone,
        email: state.email,
        outreachEmail: state.outreach(),
        otpRequired: state.otpRequired,
        outreachVerified: state.outreachVerified,
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
  setResult: (result) => set({ result }),
  setCatalog: (catalog) => set({ catalog }),
  setOtpRequired: (otpRequired) => set({ otpRequired }),
  setFullName: (fullName) => set({ fullName }),
  setPhone: (phone) => set({ phone }),
  setEmail: (email) =>
    set((state) => ({
      email,
      outreachEmail: state.differentOutreach ? state.outreachEmail : email,
      outreachVerified: state.differentOutreach
        ? state.outreachVerified
        : false,
    })),
  setOutreachEmail: (outreachEmail) =>
    set({ outreachEmail, outreachVerified: false }),
  setDifferentOutreach: (differentOutreach) =>
    set((state) => ({
      differentOutreach,
      outreachVerified: false,
      outreachEmail: differentOutreach ? state.outreachEmail : state.email,
    })),
  setOutreachVerified: (outreachVerified) => set({ outreachVerified }),
  setOtpOpen: (otpOpen) => set({ otpOpen }),
  setVerifyCode: (verifyCode) => set({ verifyCode }),
  setVerifyBusy: (verifyBusy) => set({ verifyBusy }),
  setIndustry: (industry) =>
    set((state) => ({
      industry,
      title:
        state.title && !isAllowedTitle(state.catalog, industry, state.title)
          ? ""
          : state.title,
    })),
  setTitle: (title) => set({ title }),
  setWebsite: (website) => set({ website }),
  setFile: (file) => set({ file }),
  setStaging: (staging) => set({ staging }),
  setPreviewBusy: (previewBusy) => set({ previewBusy }),
  startOver: () => set({ result: null, pending: false, step: 3 }),
}))

export function youDetailsFromStore(): {
  fullName: string
  phone: string
  email: string
  outreachEmail: string
} {
  const state = useResearchStore.getState()
  return {
    fullName: state.fullName,
    phone: state.phone,
    email: state.email,
    outreachEmail: state.outreach(),
  }
}

export function validateCurrentYouDetails(): string | null {
  return validateYouDetails(youDetailsFromStore())
}
