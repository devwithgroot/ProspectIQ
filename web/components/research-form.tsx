"use client"

import { useEffect, useState } from "react"
import { CheckIcon, FileSpreadsheetIcon, UploadIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Combobox } from "@/components/ui/combobox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  bundledCatalog,
  fetchCatalog,
  titlesForIndustry,
  type Catalog,
} from "@/lib/catalog"
import {
  estimateResearch,
  formatElapsed,
  formatEstimateRange,
  formatMinutesLeft,
  researchTimeoutMs,
} from "@/lib/research-estimate"
import {
  useResearchStore,
  validateCurrentYouDetails,
} from "@/lib/research-store"
import { fetchSettings } from "@/lib/settings"
import type {
  ProspectReport,
  ResearchResult,
  StagedProspect,
  StagingPreview,
} from "@/lib/types"
import { cn } from "@/lib/utils"
import {
  validateBriefing,
  validateStagedCompany,
  validateUploadFile,
  validateVerifyCode,
} from "@/lib/validators"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

const STEPS = [
  {
    id: "you",
    title: "You",
    heading: "Tell us who you are",
    description:
      "Work email is how we know you. Outreach email is what prospects will see.",
  },
  {
    id: "role",
    title: "Role",
    heading: "What do you sell, and what’s your title?",
    description:
      "Type to search. Only titles that match the selected industry can be saved.",
  },
  {
    id: "company",
    title: "Company",
    heading: "Your company website",
    description:
      "We’ll read the public site and learn what you sell. No login needed.",
  },
  {
    id: "prospects",
    title: "Prospects",
    heading: "Upload the companies you care about",
    description:
      "We’ll research each company and score how well they fit what you sell.",
  },
] as const

export function ResearchForm() {
  const store = useResearchStore()
  const {
    step,
    notice,
    otpError,
    pending,
    result,
    catalog,
    otpRequired,
    fullName,
    phone,
    email,
    outreachEmail,
    differentOutreach,
    outreachVerified,
    otpOpen,
    verifyCode,
    verifyBusy,
    industry,
    title,
    website,
    file,
    staging,
    previewBusy,
    showError,
    showOtpError,
    clearMessages,
    validateStep,
    setStep,
    setNotice,
    setOtpError,
    setPending,
    setResult,
    setCatalog,
    setOtpRequired,
    setFullName,
    setPhone,
    setEmail,
    setOutreachEmail,
    setDifferentOutreach,
    setOutreachVerified,
    setOtpOpen,
    setVerifyCode,
    setVerifyBusy,
    setIndustry,
    setTitle,
    setWebsite,
    setFile,
    setStaging,
    setPreviewBusy,
    startOver,
  } = store

  useEffect(() => {
    fetchCatalog()
      .then(setCatalog)
      .catch(() => setCatalog(bundledCatalog))
    fetchSettings()
      .then((settings) => setOtpRequired(settings.otp_required))
      .catch(() => setOtpRequired(false))
  }, [setCatalog, setOtpRequired])

  useEffect(() => {
    if (result) {
      document.getElementById("research-results")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      })
    }
  }, [result])

  const titleOptions = titlesForIndustry(catalog, industry)
  const current = STEPS[step]
  const outreach = store.outreach()

  function selectStep(index: number) {
    if (index === step) return
    if (index < step) {
      clearMessages()
      setStep(index)
      return
    }
    for (let i = step; i < index; i += 1) {
      if (i === STEPS.length - 1) continue
      const problem = validateStep(i)
      if (problem) {
        showError(problem)
        setStep(i)
        return
      }
    }
    clearMessages()
    setStep(index)
  }

  async function goNext() {
    if (step === 0) {
      const ready = await finishYouStep()
      if (!ready) {
        return
      }
    } else {
      const problem = validateStep(step)
      if (problem) {
        showError(problem)
        return
      }
    }
    clearMessages()
    setStep((currentStep) => Math.min(currentStep + 1, STEPS.length - 1))
  }

  async function finishYouStep(): Promise<boolean> {
    const problem = validateCurrentYouDetails()
    if (problem) {
      showError(problem)
      return false
    }
    if (!otpRequired || outreachVerified) {
      return true
    }
    await sendOutreachCode()
    return false
  }

  async function sendOutreachCode(): Promise<boolean> {
    const problem = validateCurrentYouDetails()
    if (problem) {
      showError(problem)
      return false
    }
    setVerifyBusy(true)
    setOtpError(null)
    setOtpOpen(true)
    try {
      const response = await fetch(`${API_URL}/api/verify-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: outreach }),
      })
      const payload = await response.json().catch(() => null)
      if (!response.ok) {
        throw payload ?? new Error("We couldn’t send a code.")
      }
      setVerifyCode("")
      return true
    } catch (err) {
      showOtpError(err)
      return false
    } finally {
      setVerifyBusy(false)
    }
  }

  async function confirmOutreachCode(): Promise<void> {
    const problem = validateVerifyCode(verifyCode)
    if (problem) {
      showOtpError(problem)
      return
    }
    setVerifyBusy(true)
    setOtpError(null)
    try {
      const response = await fetch(`${API_URL}/api/verify-email/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: outreach, code: verifyCode.trim() }),
      })
      const payload = await response.json().catch(() => null)
      if (!response.ok) {
        throw payload ?? new Error("That code didn’t work.")
      }
      setOutreachVerified(true)
      setOtpOpen(false)
      setOtpError(null)
      setVerifyCode("")
      setStep((currentStep) => Math.min(currentStep + 1, STEPS.length - 1))
    } catch (err) {
      showOtpError(err)
    } finally {
      setVerifyBusy(false)
    }
  }

  function goBack() {
    clearMessages()
    if (step === STEPS.length - 1 && staging) {
      setStaging(null)
      return
    }
    setStep((currentStep) => Math.max(currentStep - 1, 0))
  }

  async function previewFile(next: File | null) {
    setFile(next)
    setStaging(null)
    setResult(null)
    if (!next) {
      return
    }
    const fileProblem = validateUploadFile(next)
    if (fileProblem) {
      showError(fileProblem)
      return
    }

    setPreviewBusy(true)
    clearMessages()
    const data = new FormData()
    data.set("prospects", next)
    try {
      const response = await fetch(`${API_URL}/api/preview`, {
        method: "POST",
        body: data,
      })
      const payload = await response.json().catch(() => null)
      if (!response.ok) {
        throw payload ?? new Error("We couldn’t read that file.")
      }
      setStaging(withRowIds(payload as StagingPreview))
    } catch (err) {
      showError(err)
    } finally {
      setPreviewBusy(false)
    }
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const problem = validateStep(step)
    if (problem) {
      showError(problem)
      return
    }
    if (!staging || staging.companies.length === 0) {
      showError("Add at least one company before starting research.")
      return
    }

    clearMessages()
    setResult(null)
    setPending(true)

    const data = new FormData()
    data.set("full_name", fullName.trim())
    data.set("phone", phone.trim())
    data.set("email", email.trim())
    data.set("outreach_email", outreach)
    data.set("industry", industry)
    data.set("title", title)
    data.set("website", website.trim())
    data.set("prospects", fileFromStaging(staging))

    try {
      const estimate = estimateResearch(staging?.count ?? 1)
      const response = await fetch(`${API_URL}/api/research`, {
        method: "POST",
        body: data,
        signal: AbortSignal.timeout(researchTimeoutMs(estimate)),
      })
      const payload = await response.json().catch(() => null)
      if (!response.ok) {
        throw payload ?? new Error("We couldn’t finish research.")
      }
      setResult(payload as ResearchResult)
    } catch (err) {
      showError(err)
    } finally {
      setPending(false)
    }
  }

  const heading =
    current.id === "prospects" && staging
      ? "Review this list"
      : current.heading
  const estimate = estimateResearch(staging?.count ?? 1)
  const description =
    current.id === "prospects" && staging
      ? `${staging.count} compan${staging.count === 1 ? "y" : "ies"} from ${staging.file_name}. Research usually takes ${formatEstimateRange(estimate)}, including a little extra time.`
      : current.description

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-6 py-8 sm:py-10">
      <div className="space-y-2">
        <h1 className="font-heading text-2xl tracking-tight sm:text-3xl">
          Research your prospects
        </h1>
        <p className="max-w-xl text-sm leading-6 text-muted-foreground">
          Four short steps. We’ll learn your company from your website, then
          brief you on every company in your list.
        </p>
      </div>

      {result && !pending ? (
        <Results
          result={result}
          onChange={setResult}
          onStartOver={startOver}
        />
      ) : (
        <>
      <StepNav step={step} onSelect={selectStep} />

      <Card>
        <CardHeader>
          <p className="text-xs font-medium text-muted-foreground">
            Step {step + 1} of {STEPS.length}
          </p>
          <CardTitle className="text-lg sm:text-xl">{heading}</CardTitle>
          <CardDescription className="text-sm leading-6">
            {description}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {pending ? (
            <ResearchingState companyCount={staging?.count ?? 1} />
          ) : (
            <form className="space-y-6" onSubmit={onSubmit}>
              {current.id === "you" ? (
                <YouSection
                  fullName={fullName}
                  phone={phone}
                  email={email}
                  outreachEmail={outreachEmail}
                  differentOutreach={differentOutreach}
                  outreachVerified={outreachVerified}
                  otpRequired={otpRequired}
                  onFullName={setFullName}
                  onPhone={setPhone}
                  onEmail={setEmail}
                  onOutreachEmail={setOutreachEmail}
                  onDifferentOutreach={setDifferentOutreach}
                />
              ) : null}
              {current.id === "role" ? (
                <RoleSection
                  catalog={catalog}
                  industry={industry}
                  title={title}
                  titleOptions={titleOptions}
                  onIndustry={setIndustry}
                  onTitle={setTitle}
                />
              ) : null}
              {current.id === "company" ? (
                <CompanySection website={website} onWebsite={setWebsite} />
              ) : null}
              {current.id === "prospects" ? (
                <ProspectsSection
                  file={file}
                  staging={staging}
                  previewBusy={previewBusy}
                  summary={{
                    fullName,
                    email,
                    outreachEmail: outreach,
                    industry,
                    title,
                    website,
                  }}
                  onFile={(next) => void previewFile(next)}
                  onEditDetails={() => {
                    clearMessages()
                    setStep(0)
                  }}
                  onStagingChange={setStaging}
                  onError={showError}
                />
              ) : null}

              <div className="flex flex-wrap items-center justify-between gap-3">
                {step > 0 || staging ? (
                  <Button type="button" variant="outline" onClick={goBack}>
                    Back
                  </Button>
                ) : (
                  <span />
                )}
                {step < STEPS.length - 1 ? (
                  <Button
                    type="button"
                    onClick={() => void goNext()}
                    disabled={verifyBusy}
                  >
                    {otpRequired && !outreachVerified ? "Send code" : "Continue"}
                  </Button>
                ) : staging ? (
                  <div className="flex flex-col items-end gap-1">
                    <Button type="submit" size="lg">
                      Start research
                    </Button>
                    <p className="text-xs text-muted-foreground">
                      Usually {formatEstimateRange(estimate)}
                    </p>
                  </div>
                ) : (
                  <Button
                    type="button"
                    size="lg"
                    disabled={previewBusy}
                    onClick={() => {
                      if (!file) {
                        showError("Please upload a spreadsheet of companies.")
                        return
                      }
                      void previewFile(file)
                    }}
                  >
                    {previewBusy ? "Reading file…" : "Review list"}
                  </Button>
                )}
              </div>
            </form>
          )}
        </CardContent>
      </Card>
        </>
      )}

      <Dialog
        open={notice !== null && !otpOpen}
        onOpenChange={(open) => {
          if (!open) {
            setNotice(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{notice?.title}</DialogTitle>
            <DialogDescription>{notice?.message}</DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-row justify-end">
            <Button type="button" onClick={() => setNotice(null)}>
              OK
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={otpOpen}
        onOpenChange={(open) => {
          setOtpOpen(open)
          if (!open) {
            setVerifyCode("")
            setOtpError(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Enter the code</DialogTitle>
            <DialogDescription>
              We sent a 6-digit code to {outreach || "that inbox"}. Outreach
              will come from this address later.
            </DialogDescription>
          </DialogHeader>
          <Field
            id="verify_code"
            name="verify_code"
            label="Verification code"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="123456"
            value={verifyCode}
            onChange={(event) => setVerifyCode(event.target.value)}
          />
          {otpError ? (
            <p className="text-sm leading-6 text-destructive">{otpError}</p>
          ) : null}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => void sendOutreachCode()}
              disabled={verifyBusy}
            >
              Resend
            </Button>
            <Button
              type="button"
              onClick={() => void confirmOutreachCode()}
              disabled={verifyBusy}
            >
              {verifyBusy ? "Checking…" : "Verify"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function withRowIds(preview: StagingPreview): StagingPreview {
  return {
    ...preview,
    count: preview.companies.length,
    companies: preview.companies.map((row, index) => ({
      ...row,
      id: row.id || `${preview.file_name}-${index}-${row.company_name}`,
    })),
  }
}

function blankStagedCompany(): StagedProspect {
  return {
    id: `new-${Date.now()}`,
    company_name: "",
    website: null,
    notes: null,
  }
}

function upsertStagedCompany(
  staging: StagingPreview,
  row: StagedProspect
): StagingPreview {
  const next = {
    ...row,
    company_name: row.company_name.trim(),
    website: row.website?.trim() || null,
    notes: row.notes?.trim() || null,
  }
  const companies = staging.companies.some((item) => item.id === next.id)
    ? staging.companies.map((item) => (item.id === next.id ? next : item))
    : [...staging.companies, next]
  return { ...staging, companies, count: companies.length }
}

function removeStagedCompany(
  staging: StagingPreview,
  id: string
): StagingPreview {
  const companies = staging.companies.filter((item) => item.id !== id)
  return { ...staging, companies, count: companies.length }
}

function csvCell(value: string): string {
  if (/[",\n]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

function fileFromStaging(staging: StagingPreview): File {
  const lines = [
    "company_name,website,notes",
    ...staging.companies.map((row) =>
      [
        csvCell(row.company_name),
        csvCell(row.website ?? ""),
        csvCell(row.notes ?? ""),
      ].join(",")
    ),
  ]
  return new File([`${lines.join("\n")}\n`], staging.file_name || "prospects.csv", {
    type: "text/csv",
  })
}

function CompanyEditDialog({
  row,
  onClose,
  onSave,
}: {
  row: StagedProspect | null
  onClose: () => void
  onSave: (row: StagedProspect) => void
}) {
  const [draft, setDraft] = useState<StagedProspect | null>(row)

  useEffect(() => {
    setDraft(row)
  }, [row])

  if (!draft) {
    return null
  }

  return (
    <Dialog open={row !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {draft.company_name ? "Edit company" : "Add a company"}
          </DialogTitle>
          <DialogDescription>
            Change the name, website, or why you care about this company.
          </DialogDescription>
        </DialogHeader>
        <Field
          id="edit_company_name"
          name="edit_company_name"
          label="Company name"
          value={draft.company_name}
          onChange={(event) =>
            setDraft({ ...draft, company_name: event.target.value })
          }
        />
        <Field
          id="edit_website"
          name="edit_website"
          label="Website"
          placeholder="company.com"
          value={draft.website ?? ""}
          onChange={(event) =>
            setDraft({ ...draft, website: event.target.value })
          }
        />
        <div className="space-y-2">
          <Label htmlFor="edit_notes">Notes</Label>
          <Textarea
            id="edit_notes"
            value={draft.notes ?? ""}
            onChange={(event) =>
              setDraft({ ...draft, notes: event.target.value })
            }
          />
        </div>
        <DialogFooter className="flex-row justify-end">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" onClick={() => onSave(draft)}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function BriefingEditDialog({
  report,
  onClose,
  onSave,
}: {
  report: ProspectReport | null
  onClose: () => void
  onSave: (report: ProspectReport) => void
}) {
  const [draft, setDraft] = useState<ProspectReport | null>(report)

  useEffect(() => {
    setDraft(report)
  }, [report])

  if (!draft) {
    return null
  }

  return (
    <Dialog open={report !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit briefing</DialogTitle>
          <DialogDescription>
            Fix names or wording. This stays on this page only.
          </DialogDescription>
        </DialogHeader>
        <Field
          id="edit_briefing_name"
          name="edit_briefing_name"
          label="Company name"
          value={draft.company_name}
          onChange={(event) =>
            setDraft({ ...draft, company_name: event.target.value })
          }
        />
        <div className="space-y-2">
          <Label htmlFor="edit_summary">Summary</Label>
          <Textarea
            id="edit_summary"
            value={draft.executive_summary}
            onChange={(event) =>
              setDraft({ ...draft, executive_summary: event.target.value })
            }
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="edit_signals">Why they look interesting</Label>
          <Textarea
            id="edit_signals"
            value={draft.key_signals.join("\n")}
            onChange={(event) =>
              setDraft({
                ...draft,
                key_signals: linesFromText(event.target.value),
              })
            }
          />
          <p className="text-xs text-muted-foreground">One point per line.</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="edit_risks">Watch-outs</Label>
          <Textarea
            id="edit_risks"
            value={draft.risks.join("\n")}
            onChange={(event) =>
              setDraft({ ...draft, risks: linesFromText(event.target.value) })
            }
          />
          <p className="text-xs text-muted-foreground">One point per line.</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="edit_approach">Suggested approach</Label>
          <Textarea
            id="edit_approach"
            value={draft.recommended_sales_approach}
            onChange={(event) =>
              setDraft({
                ...draft,
                recommended_sales_approach: event.target.value,
              })
            }
          />
        </div>
        <DialogFooter className="flex-row justify-end">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" onClick={() => onSave(draft)}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function linesFromText(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
}

function StepNav({
  step,
  onSelect,
}: {
  step: number
  onSelect: (index: number) => void
}) {
  const progress = ((step + 1) / STEPS.length) * 100
  return (
    <div className="space-y-3">
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>
      <ol className="grid grid-cols-4 gap-2">
        {STEPS.map((item, index) => {
          const active = index === step
          const done = index < step
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onSelect(index)}
                className={cn(
                  "flex w-full flex-col items-start gap-1.5 rounded-xl px-1 py-1 text-left sm:flex-row sm:items-center sm:gap-2 sm:px-2 sm:py-2",
                  active ? "text-foreground" : "text-muted-foreground"
                )}
              >
                <span
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                    done || active
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  {done ? <CheckIcon className="size-3.5" /> : index + 1}
                </span>
                <span className="text-xs font-medium sm:text-sm">
                  {item.title}
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

function YouSection({
  fullName,
  phone,
  email,
  outreachEmail,
  differentOutreach,
  outreachVerified,
  otpRequired,
  onFullName,
  onPhone,
  onEmail,
  onOutreachEmail,
  onDifferentOutreach,
}: {
  fullName: string
  phone: string
  email: string
  outreachEmail: string
  differentOutreach: boolean
  outreachVerified: boolean
  otpRequired: boolean
  onFullName: (value: string) => void
  onPhone: (value: string) => void
  onEmail: (value: string) => void
  onOutreachEmail: (value: string) => void
  onDifferentOutreach: (value: boolean) => void
}) {
  const outreach = differentOutreach ? outreachEmail : email

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          id="full_name"
          name="full_name"
          label="Full name"
          placeholder="Priya Mehta"
          value={fullName}
          onChange={(event) => onFullName(event.target.value)}
          required
        />
        <Field
          id="phone"
          name="phone"
          label="Phone"
          placeholder="+91 98455 12210"
          value={phone}
          onChange={(event) => onPhone(event.target.value)}
          required
        />
      </div>
      <Field
        id="email"
        name="email"
        label="Work email"
        type="email"
        placeholder="you@company.com"
        hint="This is your login identity. It can stay different from outreach."
        value={email}
        onChange={(event) => onEmail(event.target.value)}
        required
      />
      <label className="flex items-start gap-2.5 text-sm leading-6">
        <input
          type="checkbox"
          className="mt-1 size-4 accent-foreground"
          checked={differentOutreach}
          onChange={(event) => onDifferentOutreach(event.target.checked)}
        />
        <span>Use a different email when we write to prospects</span>
      </label>
      {differentOutreach ? (
        <Field
          id="outreach_email"
          name="outreach_email"
          label="Outreach email"
          type="email"
          placeholder="you.sales@company.com"
          hint={
            otpRequired
              ? "Prospects will see this as the from-address. We’ll send a code to confirm it."
              : "Prospects will see this as the from-address."
          }
          value={outreachEmail}
          onChange={(event) => onOutreachEmail(event.target.value)}
          required
        />
      ) : (
        <p className="text-xs text-muted-foreground">
          {`Outreach will use ${email || "your work email"}${
            otpRequired ? " after we send a code there." : "."
          }`}
        </p>
      )}
      {otpRequired && outreachVerified ? (
        <p className="text-sm font-medium">
          {outreach} is verified for outreach.
        </p>
      ) : null}
    </div>
  )
}

function RoleSection({
  catalog,
  industry,
  title,
  titleOptions,
  onIndustry,
  onTitle,
}: {
  catalog: Catalog
  industry: string
  title: string
  titleOptions: { id: string; label: string; group: string }[]
  onIndustry: (value: string) => void
  onTitle: (value: string) => void
}) {
  return (
    <div className="space-y-4">
      <Combobox
        id="industry"
        name="industry"
        label="Industry"
        value={industry}
        options={catalog.industries}
        placeholder="Start typing, for example Manufacturing"
        emptyText="No industry matches that."
        hint="This is your company’s industry, not your customer’s."
        required
        onChange={onIndustry}
      />
      <Combobox
        id="title"
        name="title"
        label="Your title"
        value={title}
        options={titleOptions}
        placeholder={
          industry
            ? "Start typing, for example Account Executive"
            : "Choose an industry first"
        }
        emptyText="No title matches that in this industry."
        hint={
          industry
            ? `Showing titles commonly used in ${industry}.`
            : undefined
        }
        disabled={!industry}
        required
        onChange={onTitle}
      />
    </div>
  )
}

function CompanySection({
  website,
  onWebsite,
}: {
  website: string
  onWebsite: (value: string) => void
}) {
  return (
    <Field
      id="website"
      name="website"
      label="Company website"
      placeholder="yourcompany.com"
      hint="We’ll add https:// if you leave it off."
      value={website}
      onChange={(event) => onWebsite(event.target.value)}
      required
    />
  )
}

function ProspectsSection({
  file,
  staging,
  previewBusy,
  summary,
  onFile,
  onEditDetails,
  onStagingChange,
  onError,
}: {
  file: File | null
  staging: StagingPreview | null
  previewBusy: boolean
  summary: {
    fullName: string
    email: string
    outreachEmail: string
    industry: string
    title: string
    website: string
  }
  onFile: (file: File | null) => void
  onEditDetails: () => void
  onStagingChange: (next: StagingPreview) => void
  onError: (raw: unknown) => void
}) {
  const [over, setOver] = useState(false)
  const [editing, setEditing] = useState<StagedProspect | null>(null)

  if (staging) {
    return (
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3 rounded-xl bg-muted/60 px-4 py-3 text-sm leading-6">
          <div>
            <p className="font-medium">
              {summary.fullName} · {summary.title}
            </p>
            <p className="text-muted-foreground">
              {summary.industry} · Outreach {summary.outreachEmail}
            </p>
            <p className="text-muted-foreground">{summary.website}</p>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={onEditDetails}>
            Edit
          </Button>
        </div>
        <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Company</TableHead>
                <TableHead>Website</TableHead>
                <TableHead>Notes</TableHead>
                <TableHead className="w-28 text-right"> </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {staging.companies.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="font-medium whitespace-normal">
                    {row.company_name}
                  </TableCell>
                  <TableCell className="whitespace-normal text-muted-foreground">
                    {row.website || "—"}
                  </TableCell>
                  <TableCell className="max-w-xs whitespace-normal text-muted-foreground">
                    {row.notes || "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        className="text-xs text-muted-foreground underline-offset-4 hover:underline"
                        onClick={() => setEditing(row)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="text-xs text-muted-foreground underline-offset-4 hover:underline"
                        onClick={() =>
                          onStagingChange(removeStagedCompany(staging, row.id))
                        }
                      >
                        Remove
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <button
            type="button"
            className="text-muted-foreground underline-offset-4 hover:underline"
            onClick={() => {
              const blank = blankStagedCompany()
              onStagingChange(upsertStagedCompany(staging, blank))
              setEditing(blank)
            }}
          >
            Add a company
          </button>
          <label className="text-muted-foreground underline-offset-4 hover:underline">
            <span className="cursor-pointer">Replace file</span>
            <Input
              id="prospects-replace"
              name="prospects"
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              onChange={(event) => onFile(event.target.files?.[0] ?? null)}
            />
          </label>
        </div>
        <CompanyEditDialog
          row={editing}
          onClose={() => setEditing(null)}
          onSave={(next) => {
            const problem = validateStagedCompany(next)
            if (problem) {
              onError(problem)
              return
            }
            onStagingChange(upsertStagedCompany(staging, next))
            setEditing(null)
          }}
        />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-muted/60 px-4 py-3 text-sm leading-6">
        <p className="font-medium">
          {summary.fullName} · {summary.title}
        </p>
        <p className="text-muted-foreground">
          {summary.industry} · Outreach {summary.outreachEmail}
        </p>
        <p className="text-muted-foreground">{summary.website}</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="prospects">Company list</Label>
        <label
          htmlFor="prospects"
          onDragOver={(event) => {
            event.preventDefault()
            setOver(true)
          }}
          onDragLeave={() => setOver(false)}
          onDrop={(event) => {
            event.preventDefault()
            setOver(false)
            onFile(event.dataTransfer.files?.[0] ?? null)
          }}
          className={cn(
            "flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed px-4 py-8 text-center transition-colors",
            over
              ? "border-foreground/40 bg-muted"
              : "border-input bg-background hover:bg-muted/40"
          )}
        >
          {previewBusy ? (
            <>
              <FileSpreadsheetIcon className="size-6 text-muted-foreground" />
              <p className="text-sm font-medium">Reading {file?.name}…</p>
            </>
          ) : file ? (
            <>
              <FileSpreadsheetIcon className="size-6 text-muted-foreground" />
              <p className="text-sm font-medium">{file.name}</p>
              <p className="text-xs text-muted-foreground">
                {(file.size / 1024).toFixed(1)} KB · click or drop to replace
              </p>
            </>
          ) : (
            <>
              <UploadIcon className="size-6 text-muted-foreground" />
              <p className="text-sm font-medium">
                Drop a CSV here, or click to browse
              </p>
              <p className="max-w-sm text-xs leading-5 text-muted-foreground">
                Include a company name column. Website and notes are optional.
                Up to 5 MB.
              </p>
            </>
          )}
        </label>
        <Input
          id="prospects"
          name="prospects"
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          onChange={(event) => onFile(event.target.files?.[0] ?? null)}
        />
      </div>
    </div>
  )
}

function ResearchingState({ companyCount }: { companyCount: number }) {
  const estimate = estimateResearch(companyCount)
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const started = Date.now()
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [])

  const typicalSeconds = estimate.typicalMinutes * 60
  const remaining = typicalSeconds - elapsed
  const progress = Math.min(90, Math.round((elapsed / typicalSeconds) * 100))
  const companies =
    companyCount === 1 ? "1 company" : `${companyCount} companies`

  return (
    <div className="space-y-4 py-2 text-sm">
      <div className="space-y-1">
        <p className="font-medium">Research is running</p>
        <p className="leading-6 text-muted-foreground">
          First we learn your company from the website, then we brief each
          company on the list. Usually {formatEstimateRange(estimate)} for{" "}
          {companies}, including a little extra time. You can leave this tab
          open.
        </p>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${Math.max(6, progress)}%` }}
        />
      </div>
      <p className="text-muted-foreground">
        {formatElapsed(elapsed)}
        {remaining > 30
          ? ` · usually about ${formatMinutesLeft(remaining)} left`
          : elapsed > typicalSeconds
            ? " · still working on the last companies"
            : " · wrapping up"}
      </p>
    </div>
  )
}

function Field({
  id,
  name,
  label,
  hint,
  ...props
}: React.ComponentProps<typeof Input> & { label: string; hint?: string }) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} name={name} {...props} />
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  )
}

function Results({
  result,
  onChange,
  onStartOver,
}: {
  result: ResearchResult
  onChange: (next: ResearchResult) => void
  onStartOver: () => void
}) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const editing = editingIndex === null ? null : result.reports[editingIndex]

  return (
    <div id="research-results" className="space-y-6">
      <Alert>
        <AlertTitle>
          Check these briefings for {result.user.company.name}
        </AlertTitle>
        <AlertDescription>
          {result.prospects.length} compan
          {result.prospects.length === 1 ? "y" : "ies"} researched for{" "}
          {result.user.full_name}. Edit anything that looks off before you keep
          it.
        </AlertDescription>
      </Alert>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Your company</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm leading-6">
            <p className="font-medium">
              {result.user.full_name} · {result.user.title}
            </p>
            <p>Work {result.user.email}</p>
            <p>Outreach {result.user.outreach_email}</p>
            <p>{result.user.company.industry}</p>
            <p>{result.user.company.website}</p>
            <p className="text-muted-foreground">
              {result.user.company.description}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>What you sell</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {result.products.map((product) => (
              <div key={product.product_id}>
                <p className="text-sm font-medium">{product.name}</p>
                <p className="text-xs leading-5 text-muted-foreground">
                  {product.description}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-3">
        <h2 className="font-heading text-lg">Company briefings</h2>
        {result.reports.map((report, index) => {
          const prospect = result.prospects[index]
          return (
            <Card key={`${report.company_name}-${index}`}>
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle>{report.company_name}</CardTitle>
                  <Badge variant="secondary">
                    Score{" "}
                    {prospect?.overall_score.toFixed(0) ?? report.prospect_score}
                  </Badge>
                  <Badge variant="outline">{report.recommendation}</Badge>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="ml-auto"
                    onClick={() => setEditingIndex(index)}
                  >
                    Edit
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm leading-6">
                <p>{report.executive_summary}</p>
                <div>
                  <p className="font-medium">Why they look interesting</p>
                  <ul className="list-disc pl-5 text-muted-foreground">
                    {report.key_signals.map((signal) => (
                      <li key={signal}>{signal}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="font-medium">Watch-outs</p>
                  <ul className="list-disc pl-5 text-muted-foreground">
                    {report.risks.map((risk) => (
                      <li key={risk}>{risk}</li>
                    ))}
                  </ul>
                </div>
                <p>
                  <span className="font-medium">Suggested approach. </span>
                  {report.recommended_sales_approach}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="flex justify-end">
        <Button type="button" variant="outline" onClick={onStartOver}>
          Research another list
        </Button>
      </div>

      <BriefingEditDialog
        report={editing}
        onClose={() => setEditingIndex(null)}
        onSave={(next) => {
          const problem = validateBriefing(next)
          if (problem) {
            useResearchStore.getState().showError(problem)
            return
          }
          if (editingIndex === null) {
            return
          }
          const reports = result.reports.slice()
          reports[editingIndex] = next
          const prospects = result.prospects.slice()
          if (prospects[editingIndex]) {
            prospects[editingIndex] = {
              ...prospects[editingIndex],
              company_name: next.company_name,
            }
          }
          onChange({ ...result, reports, prospects })
          setEditingIndex(null)
        }}
      />
    </div>
  )
}
