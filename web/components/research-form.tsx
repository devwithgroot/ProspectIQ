"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import Link from "next/link";
import { CheckIcon, FileSpreadsheetIcon, UploadIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Combobox } from "@/components/ui/combobox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { canReuseSeller, isKnownCompany, normalizeCompanyName } from "@/lib/book";
import { API_URL } from "@/lib/api";
import {
  bundledCatalog,
  fetchCatalog,
  titlesForIndustry,
  type Catalog,
} from "@/lib/catalog";
import {
  activityFromJob,
  estimateResearch,
  formatEstimateRange,
  researchActivity,
  waitingHint,
} from "@/lib/research-estimate";
import {
  cancelResearchJob,
  fetchResearchJob,
  skipResearchCompany,
  sleep,
} from "@/lib/research-job";
import {
  useResearchHydrated,
  useResearchStore,
  validateCurrentYouDetails,
} from "@/lib/research-store";
import type {
  Company,
  CompanyProfile,
  Contact,
  ContactProfile,
  ResearchJob,
  ResearchResult,
  StagedProspect,
  StagingPreview,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  filledStagedCompanies,
  formatIndiaPhone,
  isEmail,
  localPhoneDigits,
  validateBriefing,
  type BriefingDraft,
  validateFullName,
  validatePhone,
  validateUploadFile,
  validateWorkEmail,
  websiteFromEmail,
} from "@/lib/validators";

function firstFieldSelector(stepIndex: number): string {
  if (stepIndex === 0) return "#full_name";
  if (stepIndex === 1) return "#industry";
  if (stepIndex === 2) return "#website";
  return '[data-sheet-cell="0-0"]';
}

function onEnterKey(
  event: KeyboardEvent<HTMLElement>,
  next: string | (() => void),
) {
  if (event.key !== "Enter" || event.nativeEvent.isComposing) {
    return;
  }
  event.preventDefault();
  if (typeof next === "string") {
    document.getElementById(next)?.focus();
    return;
  }
  next();
}

const STEPS = [
  {
    id: "you",
    title: "You",
    heading: "Tell us who you are",
    description: "A few details so we know who is running this research.",
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
      "We’ll suggest this from your work email. Change it if that’s not the site.",
  },
  {
    id: "prospects",
    title: "Prospects",
    heading: "Companies you want researched",
    description: "Type the list, or upload a spreadsheet.",
  },
] as const;

export function ResearchForm() {
  const store = useResearchStore();
  const {
    step,
    notice,
    pending,
    jobId,
    job,
    result,
    book,
    catalog,
    fullName,
    phone,
    email,
    industry,
    title,
    website,
    file,
    staging,
    previewBusy,
    prospectsMode,
    showError,
    clearMessages,
    validateStep,
    setStep,
    setNotice,
    setPending,
    setJobId,
    setJob,
    setResult,
    setCatalog,
    setFullName,
    setPhone,
    setEmail,
    setIndustry,
    setTitle,
    setWebsite,
    applySuggestedWebsite,
    setFile,
    setStaging,
    setPreviewBusy,
    setProspectsMode,
  } = store;
  const hydrated = useResearchHydrated();
  const [youShowErrors, setYouShowErrors] = useState(false);
  const [focusStep, setFocusStep] = useState<number | null>(null);

  useEffect(() => {
    fetchCatalog()
      .then(setCatalog)
      .catch(() => setCatalog(bundledCatalog));
  }, [setCatalog]);

  useEffect(() => {
    if (result) {
      document.getElementById("research-results")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [result]);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    if (step === STEPS.length - 1 && !staging) {
      setStaging(emptySheet());
    }
  }, [hydrated, step, staging, setStaging]);

  useEffect(() => {
    if (!hydrated || !jobId) {
      return;
    }

    let cancelled = false;
    setPending(true);

    async function watchJob(id: string) {
      let failures = 0;
      while (!cancelled) {
        try {
          const next = await fetchResearchJob(id);
          if (cancelled) {
            return;
          }
          failures = 0;
          setJob(next);
          if (next.status === "done" && next.result) {
            setResult(next.result);
            setJobId(null);
            setJob(null);
            setPending(false);
            return;
          }
          if (next.status === "cancelled") {
            const finished = next.result?.companies ?? [];
            if (finished.length && next.result) {
              setResult(next.result);
            } else {
              setNotice({
                title: "Research stopped",
                message:
                  "You can start again from your list whenever you’re ready.",
              });
            }
            setJobId(null);
            setJob(null);
            setPending(false);
            return;
          }
          if (next.status === "error" || next.status === "lost") {
            console.error("[ProspectIQ] research job ended", {
              job_id: next.job_id,
              status: next.status,
              error: next.error,
              error_detail: next.error_detail,
              current: next.current,
            });
            showError(next.error || "We couldn’t finish research.");
            setJobId(null);
            setJob(null);
            setPending(false);
            return;
          }
        } catch (err) {
          failures += 1;
          console.warn("[ProspectIQ] research poll failed", failures, err);
          if (failures >= 8) {
            showError(err);
            return;
          }
        }
        await sleep(800);
      }
    }

    void watchJob(jobId);
    return () => {
      cancelled = true;
    };
  }, [
    hydrated,
    jobId,
    setJob,
    setJobId,
    setPending,
    setNotice,
    setResult,
    showError,
  ]);

  useEffect(() => {
    if (focusStep === null || focusStep !== step) {
      return;
    }
    if (step === STEPS.length - 1 && prospectsMode === "grid" && !staging) {
      return;
    }

    let cancelled = false;
    const focusFirstField = () => {
      if (cancelled) {
        return false;
      }
      const node = document.querySelector<HTMLElement>(
        firstFieldSelector(step),
      );
      if (!node) {
        return false;
      }
      node.focus();
      if (
        step !== STEPS.length - 1 &&
        (node instanceof HTMLInputElement ||
          node instanceof HTMLTextAreaElement)
      ) {
        node.select();
      }
      return document.activeElement === node;
    };

    const frame = window.requestAnimationFrame(() => {
      if (focusFirstField()) {
        setFocusStep(null);
      }
    });
    const retry = window.setTimeout(() => {
      if (focusFirstField()) {
        setFocusStep(null);
      }
    }, 50);

    return () => {
      cancelled = true;
      window.cancelAnimationFrame(frame);
      window.clearTimeout(retry);
    };
  }, [focusStep, step, staging, prospectsMode]);

  const titleOptions = titlesForIndustry(catalog, industry);
  const current = STEPS[step];
  const suggestedWebsite = websiteFromEmail(email);

  function selectStep(index: number) {
    if (index === step) return;
    if (index < step) {
      clearMessages();
      setStep(index);
      return;
    }
    for (let i = step; i < index; i += 1) {
      if (i === STEPS.length - 1) continue;
      const problem = validateStep(i);
      if (problem) {
        showError(problem);
        setStep(i);
        return;
      }
    }
    clearMessages();
    prepareStep(index);
    setStep(index);
    setFocusStep(index);
  }

  function prepareStep(index: number) {
    if (index === STEPS.length - 1 && !staging) {
      setStaging(emptySheet());
    }
  }

  async function goNext() {
    if (step === 0) {
      const ready = await finishYouStep();
      if (!ready) {
        return;
      }
    } else {
      const problem = validateStep(step);
      if (problem) {
        showError(problem);
        return;
      }
    }
    clearMessages();
    const next = Math.min(step + 1, STEPS.length - 1);
    prepareStep(next);
    setStep(next);
    setFocusStep(next);
  }

  async function finishYouStep(): Promise<boolean> {
    const problem = validateCurrentYouDetails();
    if (problem) {
      setYouShowErrors(true);
      return false;
    }
    setYouShowErrors(false);
    return true;
  }

  function goBack() {
    clearMessages();
    setStep((currentStep) => Math.max(currentStep - 1, 0));
  }

  async function previewFile(next: File | null) {
    setFile(next);
    setStaging(null);
    setResult(null);
    if (!next) {
      return;
    }
    const fileProblem = validateUploadFile(next);
    if (fileProblem) {
      showError(fileProblem);
      return;
    }

    setPreviewBusy(true);
    clearMessages();
    const data = new FormData();
    data.set("prospects", next);
    try {
      const response = await fetch(`${API_URL}/api/preview`, {
        method: "POST",
        body: data,
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw payload ?? new Error("We couldn’t read that file.");
      }
      setStaging(withRowIds(payload as StagingPreview));
      setProspectsMode("grid");
    } catch (err) {
      showError(err);
    } finally {
      setPreviewBusy(false);
    }
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (step !== STEPS.length - 1) {
      return;
    }
    const companies = filledStagedCompanies(staging);
    if (companies.length === 0) {
      return;
    }
    const fresh = companies.filter(
      (row) => !isKnownCompany(book, row.company_name),
    );
    const known = companies.filter((row) =>
      isKnownCompany(book, row.company_name),
    );
    if (fresh.length === 0) {
      setNotice({
        title: "Already in Companies",
        message:
          "Those companies already have briefings. Open Companies to see people and engage.",
      });
      return;
    }

    clearMessages();
    setResult(null);
    setJob(null);
    setPending(true);
    if (known.length) {
      setNotice({
        title: "Skipping saved companies",
        message: `${known.map((row) => row.company_name).join(", ")} already researched. Looking up the rest.`,
      });
    }

    const data = new FormData();
    data.set("full_name", fullName.trim());
    data.set("phone", formatIndiaPhone(phone));
    data.set("email", email.trim());
    data.set("outreach_email", email.trim());
    data.set("industry", industry);
    data.set("title", title);
    data.set("website", website.trim());
    if (canReuseSeller(book, website) && book.user) {
      data.set(
        "seller",
        JSON.stringify({ user: book.user, products: book.products }),
      );
    }
    data.set(
      "prospects",
      fileFromStaging({
        file_name: staging?.file_name || "prospects.csv",
        count: fresh.length,
        companies: fresh,
      }),
    );

    try {
      const response = await fetch(`${API_URL}/api/research`, {
        method: "POST",
        body: data,
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw payload ?? new Error("We couldn’t start research.");
      }
      const started = payload as { job_id?: string };
      if (!started.job_id) {
        throw new Error("We couldn’t start research.");
      }
      setJobId(started.job_id);
    } catch (err) {
      setPending(false);
      showError(err);
    }
  }

  const filledCompanies = filledStagedCompanies(staging);
  const heading =
    current.id === "prospects" && filledCompanies.length
      ? "Review this list"
      : current.heading;
  const freshCompanies = filledCompanies.filter(
    (row) => !isKnownCompany(book, row.company_name),
  );
  const reuseSeller = canReuseSeller(book, website);
  const estimate = estimateResearch(freshCompanies.length || 1, {
    skipOnboard: reuseSeller,
  });
  const alreadyCount = filledCompanies.length - freshCompanies.length;
  const description =
    current.id === "prospects" && filledCompanies.length
      ? freshCompanies.length === 0
        ? `${filledCompanies.length} already in Companies. No need to research them again.`
        : `${freshCompanies.length} new compan${freshCompanies.length === 1 ? "y" : "ies"}${alreadyCount ? `, ${alreadyCount} already saved` : ""}${staging?.file_name && staging.file_name !== "prospects.csv" ? ` from ${staging.file_name}` : ""}. Research usually takes ${formatEstimateRange(estimate)}.`
      : current.description;

  if (!hydrated) {
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
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-6 py-8 sm:py-10">
      <div className="space-y-2">
        <h1 className="font-heading text-2xl tracking-tight sm:text-3xl">
          {pending ? "Researching your prospects" : "Research your prospects"}
        </h1>
        <p className="max-w-xl text-sm leading-6 text-muted-foreground">
          {pending
            ? "You can refresh this page, skip a company, or stop. Research keeps running until you stop it."
            : "Four short steps. We’ll learn your company from your website, then brief you on every company in your list."}
        </p>
      </div>

      {result && !pending ? (
        <Results result={result} onChange={setResult} />
      ) : pending ? (
        <Card>
          <CardContent className="pt-6">
            <ResearchingState
              companies={
                job?.companies ?? filledCompanies.map((row) => row.company_name)
              }
              job={job}
              skipOnboard={canReuseSeller(book, website)}
            />
          </CardContent>
        </Card>
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
              <form className="space-y-6" onSubmit={onSubmit}>
                {current.id === "you" ? (
                  <YouSection
                    fullName={fullName}
                    phone={phone}
                    email={email}
                    showErrors={youShowErrors}
                    onFullName={setFullName}
                    onPhone={setPhone}
                    onEmail={setEmail}
                    onContinue={() => void goNext()}
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
                    onContinue={() => void goNext()}
                  />
                ) : null}
                {current.id === "company" ? (
                  <CompanySection
                    website={website}
                    suggested={suggestedWebsite}
                    savedName={
                      reuseSeller ? book.user?.company.name ?? null : null
                    }
                    savedDescription={
                      reuseSeller ? book.user?.company.description ?? null : null
                    }
                    onWebsite={setWebsite}
                    onUseSuggested={applySuggestedWebsite}
                    onContinue={() => void goNext()}
                  />
                ) : null}
                {current.id === "prospects" ? (
                  <ProspectsSection
                    file={file}
                    staging={staging}
                    previewBusy={previewBusy}
                    summary={{
                      fullName,
                      email,
                      industry,
                      title,
                      website,
                    }}
                    mode={prospectsMode}
                    onMode={setProspectsMode}
                    onFile={(next) => void previewFile(next)}
                    onEditDetails={() => {
                      clearMessages();
                      setStep(0);
                    }}
                    onStagingChange={setStaging}
                    knownNames={book.companies.map((item) => item.name)}
                  />
                ) : null}

                <div className="flex flex-wrap items-center justify-between gap-3">
                  {step > 0 ? (
                    <Button type="button" variant="outline" onClick={goBack}>
                      Back
                    </Button>
                  ) : (
                    <span />
                  )}
                  {step < STEPS.length - 1 ? (
                    <Button type="button" onClick={() => void goNext()}>
                      Continue
                    </Button>
                  ) : filledCompanies.length > 0 ? (
                    <div className="flex flex-col items-end gap-1">
                      <Button type="submit" size="lg">
                        Start research
                      </Button>
                      <p className="text-xs text-muted-foreground">
                        Usually {formatEstimateRange(estimate)}
                      </p>
                    </div>
                  ) : prospectsMode === "upload" ? (
                    <Button
                      type="button"
                      size="lg"
                      disabled={previewBusy}
                      onClick={() => {
                        if (!file) {
                          showError(
                            "Please upload a spreadsheet of companies.",
                          );
                          return;
                        }
                        void previewFile(file);
                      }}
                    >
                      {previewBusy ? "Reading file…" : "Review list"}
                    </Button>
                  ) : (
                    <Button type="button" size="lg" disabled>
                      Start research
                    </Button>
                  )}
                </div>
              </form>
            </CardContent>
          </Card>
        </>
      )}

      <Dialog
        open={notice !== null}
        onOpenChange={(open) => {
          if (!open) {
            setNotice(null);
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
    </div>
  );
}

function withRowIds(preview: StagingPreview): StagingPreview {
  return {
    ...preview,
    count: preview.companies.length,
    companies: preview.companies.map((row, index) => ({
      ...row,
      id: row.id || `${preview.file_name}-${index}-${row.company_name}`,
    })),
  };
}

let sheetRow = 0;

function blankStagedCompany(): StagedProspect {
  sheetRow += 1;
  return {
    id: `row-${sheetRow}`,
    company_name: "",
    website: null,
    notes: null,
  };
}

function emptySheet(fileName = "prospects.csv"): StagingPreview {
  return {
    file_name: fileName,
    count: 0,
    companies: [blankStagedCompany()],
  };
}

function withSheetCount(staging: StagingPreview): StagingPreview {
  return {
    ...staging,
    count: staging.companies.filter((row) => row.company_name.trim()).length,
  };
}

function addSheetRow(staging: StagingPreview): StagingPreview {
  return withSheetCount({
    ...staging,
    companies: [...staging.companies, blankStagedCompany()],
  });
}

function upsertStagedCompany(
  staging: StagingPreview,
  row: StagedProspect,
): StagingPreview {
  const next = {
    ...row,
    company_name: row.company_name.trim(),
    website: row.website?.trim() || null,
    notes: row.notes?.trim() || null,
  };
  const companies = staging.companies.some((item) => item.id === next.id)
    ? staging.companies.map((item) => (item.id === next.id ? next : item))
    : [...staging.companies, next];
  return { ...staging, companies, count: companies.length };
}

function removeStagedCompany(
  staging: StagingPreview,
  id: string,
): StagingPreview {
  const companies = staging.companies.filter((item) => item.id !== id);
  return { ...staging, companies, count: companies.length };
}

function isBlankRow(row: StagedProspect): boolean {
  return !row.company_name.trim() && !row.website?.trim() && !row.notes?.trim();
}

function removeBlankRows(staging: StagingPreview): StagingPreview {
  const companies = staging.companies.filter((row) => !isBlankRow(row));
  if (companies.length === 0) {
    return emptySheet(staging.file_name);
  }
  return withSheetCount({ ...staging, companies });
}

function csvCell(value: string): string {
  if (/[",\n]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function fileFromStaging(staging: StagingPreview): File {
  const lines = [
    "company_name,website,notes",
    ...staging.companies.map((row) =>
      [
        csvCell(row.company_name),
        csvCell(row.website ?? ""),
        csvCell(row.notes ?? ""),
      ].join(","),
    ),
  ];
  return new File(
    [`${lines.join("\n")}\n`],
    staging.file_name || "prospects.csv",
    {
      type: "text/csv",
    },
  );
}

function CompanyEditDialog({
  row,
  onClose,
  onSave,
}: {
  row: StagedProspect | null;
  onClose: () => void;
  onSave: (row: StagedProspect) => void;
}) {
  const [draft, setDraft] = useState<StagedProspect | null>(row);

  useEffect(() => {
    setDraft(row);
  }, [row]);

  if (!draft) {
    return null;
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
  );
}

function BriefingEditDialog({
  report,
  onClose,
  onSave,
}: {
  report: BriefingDraft | null;
  onClose: () => void;
  onSave: (report: BriefingDraft) => void;
}) {
  const [draft, setDraft] = useState<BriefingDraft | null>(report);

  useEffect(() => {
    setDraft(report);
  }, [report]);

  if (!draft) {
    return null;
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
          value={draft.name}
          onChange={(event) => setDraft({ ...draft, name: event.target.value })}
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
  );
}

function linesFromText(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function StepNav({
  step,
  onSelect,
}: {
  step: number;
  onSelect: (index: number) => void;
}) {
  const progress = ((step + 1) / STEPS.length) * 100;
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
          const active = index === step;
          const done = index < step;
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onSelect(index)}
                className={cn(
                  "flex w-full flex-col items-start gap-1.5 rounded-xl px-1 py-1 text-left sm:flex-row sm:items-center sm:gap-2 sm:px-2 sm:py-2",
                  active ? "text-foreground" : "text-muted-foreground",
                )}
              >
                <span
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                    done || active
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {done ? <CheckIcon className="size-3.5" /> : index + 1}
                </span>
                <span className="text-xs font-medium sm:text-sm">
                  {item.title}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function YouSection({
  fullName,
  phone,
  email,
  showErrors,
  onFullName,
  onPhone,
  onEmail,
  onContinue,
}: {
  fullName: string;
  phone: string;
  email: string;
  showErrors: boolean;
  onFullName: (value: string) => void;
  onPhone: (value: string) => void;
  onEmail: (value: string) => void;
  onContinue: () => void;
}) {
  const [touched, setTouched] = useState({
    fullName: false,
    phone: false,
    email: false,
  });

  const nameError =
    showErrors || touched.fullName ? validateFullName(fullName) : null;
  const phoneError =
    showErrors || touched.phone || localPhoneDigits(phone).length === 10
      ? validatePhone(phone)
      : null;
  const emailError =
    showErrors || touched.email || isEmail(email)
      ? validateWorkEmail(email)
      : null;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          id="full_name"
          name="full_name"
          label="Full name"
          placeholder="Priya Mehta"
          autoComplete="name"
          value={fullName}
          error={nameError}
          onChange={(event) => onFullName(event.target.value)}
          onBlur={() =>
            setTouched((current) => ({ ...current, fullName: true }))
          }
          onKeyDown={(event) => onEnterKey(event, "phone")}
          required
        />
        <PhoneField
          value={phone}
          error={phoneError}
          onChange={onPhone}
          onBlur={() => setTouched((current) => ({ ...current, phone: true }))}
          onKeyDown={(event) => onEnterKey(event, "email")}
        />
      </div>
      <Field
        id="email"
        name="email"
        label="Work email"
        type="email"
        autoComplete="email"
        placeholder="you@company.com"
        value={email}
        error={emailError}
        onChange={(event) => onEmail(event.target.value)}
        onBlur={() => setTouched((current) => ({ ...current, email: true }))}
        onKeyDown={(event) => onEnterKey(event, onContinue)}
        required
      />
    </div>
  );
}

function RoleSection({
  catalog,
  industry,
  title,
  titleOptions,
  onIndustry,
  onTitle,
  onContinue,
}: {
  catalog: Catalog;
  industry: string;
  title: string;
  titleOptions: { id: string; label: string; group: string }[];
  onIndustry: (value: string) => void;
  onTitle: (value: string) => void;
  onContinue: () => void;
}) {
  return (
    <div className="space-y-4">
      <Combobox
        id="industry"
        name="industry"
        label="Industry"
        autoFocus
        value={industry}
        options={catalog.industries}
        placeholder="Start typing, for example Manufacturing"
        emptyText="No industry matches that."
        required
        onChange={onIndustry}
        onAdvance={() => {
          window.requestAnimationFrame(() => {
            document.getElementById("title")?.focus();
          });
        }}
      />
      <Combobox
        id="title"
        name="title"
        label="Your title"
        value={title}
        options={titleOptions}
        placeholder={
          industry
            ? "Type SDR, AE, or the full title"
            : "Choose an industry first"
        }
        emptyText="No title matches that in this industry."
        disabled={!industry}
        required
        onChange={onTitle}
        onAdvance={onContinue}
      />
    </div>
  );
}

function CompanySection({
  website,
  suggested,
  savedName,
  savedDescription,
  onWebsite,
  onUseSuggested,
  onContinue,
}: {
  website: string;
  suggested: string | null;
  savedName: string | null;
  savedDescription: string | null;
  onWebsite: (value: string) => void;
  onUseSuggested: () => void;
  onContinue: () => void;
}) {
  return (
    <div className="space-y-3">
      <Field
        id="website"
        name="website"
        label="Company website"
        placeholder={suggested ?? "yourcompany.com"}
        value={website}
        onChange={(event) => onWebsite(event.target.value)}
        onKeyDown={(event) => onEnterKey(event, onContinue)}
        autoFocus
        required
      />
      {suggested && website !== suggested ? (
        <button
          type="button"
          className="text-sm text-muted-foreground underline-offset-4 hover:underline"
          onClick={onUseSuggested}
        >
          Use {suggested}
        </button>
      ) : null}
      {savedName ? (
        <div className="rounded-xl bg-muted/50 px-3 py-2 text-sm leading-6">
          <p className="font-medium">Saved: {savedName}</p>
          {savedDescription ? (
            <p className="text-muted-foreground">{savedDescription}</p>
          ) : null}
          <p className="text-xs text-muted-foreground">
            We’ll use this instead of reading the site again. Change the
            website if this is a different company.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function sheetCell(row: StagedProspect, col: number): string {
  if (col === 0) return row.company_name;
  if (col === 1) return row.website ?? "";
  return row.notes ?? "";
}

function setSheetCell(
  row: StagedProspect,
  col: number,
  value: string,
): StagedProspect {
  if (col === 0) return { ...row, company_name: value };
  if (col === 1) return { ...row, website: value };
  return { ...row, notes: value };
}

function isSheetHeader(cells: string[]): boolean {
  const first = cells[0]?.trim().toLowerCase();
  return (
    first === "company_name" || first === "company" || first === "company name"
  );
}

function parseSheetPaste(text: string): string[][] {
  const rows = text
    .replace(/\r/g, "")
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => line.split("\t"));
  if (rows[0] && isSheetHeader(rows[0])) {
    return rows.slice(1);
  }
  return rows;
}

function applySheetPaste(
  staging: StagingPreview,
  startRow: number,
  startCol: number,
  pasted: string[][],
): StagingPreview {
  const companies = staging.companies.map((row) => ({ ...row }));
  pasted.forEach((cells, rowOffset) => {
    const index = startRow + rowOffset;
    while (companies.length <= index) {
      companies.push(blankStagedCompany());
    }
    cells.forEach((cell, colOffset) => {
      const col = startCol + colOffset;
      if (col > 2) {
        return;
      }
      companies[index] = setSheetCell(companies[index], col, cell);
    });
  });
  return withSheetCount({
    ...staging,
    companies,
  });
}

function focusSheetCell(row: number, col: number) {
  document
    .querySelector<HTMLInputElement>(`[data-sheet-cell="${row}-${col}"]`)
    ?.focus();
}

function UserSummary({
  summary,
  onEditDetails,
}: {
  summary: {
    fullName: string;
    email: string;
    industry: string;
    title: string;
    website: string;
  };
  onEditDetails: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl bg-muted/60 px-4 py-3 text-sm leading-6">
      <div>
        <p className="font-medium">
          {summary.fullName} · {summary.title}
        </p>
        <p className="text-muted-foreground">
          {summary.industry} · {summary.email}
        </p>
        <p className="text-muted-foreground">{summary.website}</p>
      </div>
      <Button type="button" variant="ghost" size="sm" onClick={onEditDetails}>
        Edit
      </Button>
    </div>
  );
}

function ProspectsSection({
  file,
  staging,
  previewBusy,
  mode,
  summary,
  knownNames,
  onMode,
  onFile,
  onEditDetails,
  onStagingChange,
}: {
  file: File | null;
  staging: StagingPreview | null;
  previewBusy: boolean;
  mode: "grid" | "upload";
  summary: {
    fullName: string;
    email: string;
    industry: string;
    title: string;
    website: string;
  };
  knownNames: string[];
  onMode: (mode: "grid" | "upload") => void;
  onFile: (file: File | null) => void;
  onEditDetails: () => void;
  onStagingChange: (next: StagingPreview) => void;
}) {
  const [over, setOver] = useState(false);
  const sheet = staging ?? emptySheet();

  function updateRow(index: number, col: number, value: string) {
    const companies = sheet.companies.map((row, rowIndex) =>
      rowIndex === index ? setSheetCell(row, col, value) : row,
    );
    onStagingChange(
      withSheetCount({
        ...sheet,
        file_name: sheet.file_name || "prospects.csv",
        companies,
      }),
    );
  }

  if (mode === "upload") {
    return (
      <div className="space-y-4">
        <UserSummary summary={summary} onEditDetails={onEditDetails} />
        <div className="flex items-center justify-between gap-3">
          <Label htmlFor="prospects">Upload a spreadsheet</Label>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onMode("grid")}
          >
            Type a list
          </Button>
        </div>
        <label
          htmlFor="prospects"
          onDragOver={(event) => {
            event.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setOver(false);
            onFile(event.dataTransfer.files?.[0] ?? null);
          }}
          className={cn(
            "flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed px-4 py-8 text-center transition-colors",
            over
              ? "border-foreground/40 bg-muted"
              : "border-input bg-background hover:bg-muted/40",
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
    );
  }

  return (
    <div className="space-y-4">
      <UserSummary summary={summary} onEditDetails={onEditDetails} />
      <div className="flex items-center justify-between gap-3">
        <Label>Company list</Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onMode("upload")}
        >
          <UploadIcon data-icon="inline-start" className="size-3.5" />
          Upload
        </Button>
      </div>
      <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">#</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Website</TableHead>
              <TableHead>Notes</TableHead>
              <TableHead className="w-16"> </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sheet.companies.map((row, rowIndex) => (
              <TableRow key={row.id}>
                <TableCell className="text-xs text-muted-foreground">
                  <div className="flex flex-col gap-0.5">
                    <span>{rowIndex + 1}</span>
                    {knownNames.some(
                      (name) =>
                        normalizeCompanyName(name) ===
                        normalizeCompanyName(row.company_name),
                    ) ? (
                      <span className="text-[10px] uppercase tracking-wide">
                        Saved
                      </span>
                    ) : null}
                  </div>
                </TableCell>
                {[0, 1, 2].map((col) => (
                  <TableCell key={col} className="p-0">
                    <Input
                      data-sheet-cell={`${rowIndex}-${col}`}
                      autoFocus={rowIndex === 0 && col === 0}
                      value={sheetCell(row, col)}
                      placeholder={
                        col === 0
                          ? "Company"
                          : col === 1
                            ? "company.com"
                            : "Optional"
                      }
                      className="h-10 rounded-none border-0 bg-transparent shadow-none focus-visible:ring-0"
                      onChange={(event) =>
                        updateRow(rowIndex, col, event.target.value)
                      }
                      onPaste={(event) => {
                        const text = event.clipboardData.getData("text");
                        if (!text.includes("\t") && !text.includes("\n")) {
                          return;
                        }
                        event.preventDefault();
                        onStagingChange(
                          applySheetPaste(
                            sheet,
                            rowIndex,
                            col,
                            parseSheetPaste(text),
                          ),
                        );
                      }}
                      onKeyDown={(event) => {
                        if (
                          event.key !== "Enter" ||
                          event.nativeEvent.isComposing
                        ) {
                          return;
                        }
                        event.preventDefault();
                        const nextRow = event.shiftKey
                          ? rowIndex - 1
                          : rowIndex + 1;
                        if (nextRow < 0) {
                          return;
                        }
                        if (nextRow >= sheet.companies.length) {
                          onStagingChange(addSheetRow(sheet));
                        }
                        window.requestAnimationFrame(() => {
                          focusSheetCell(nextRow, col);
                        });
                      }}
                    />
                  </TableCell>
                ))}
                <TableCell className="text-right">
                  {sheet.companies.length > 1 ? (
                    <button
                      type="button"
                      className="text-xs text-muted-foreground underline-offset-4 hover:underline"
                      onClick={() => {
                        const next = removeStagedCompany(sheet, row.id);
                        onStagingChange(
                          next.companies.length
                            ? withSheetCount(next)
                            : emptySheet(sheet.file_name),
                        );
                      }}
                    >
                      Remove
                    </button>
                  ) : null}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          className="text-sm text-muted-foreground underline-offset-4 hover:underline"
          onClick={() => onStagingChange(addSheetRow(sheet))}
        >
          Add row
        </button>
        {sheet.companies.some(isBlankRow) &&
        sheet.companies.some((row) => !isBlankRow(row)) ? (
          <button
            type="button"
            className="text-sm text-muted-foreground underline-offset-4 hover:underline"
            onClick={() => onStagingChange(removeBlankRows(sheet))}
          >
            Remove blank rows
          </button>
        ) : null}
      </div>
    </div>
  );
}

function isReasonLine(text: string): boolean {
  return text.trim().toLowerCase().startsWith("why:");
}

function displayProgressText(text: string): string {
  return text
    .replace(/^(Choosing what to look up next on .+)\s+\(\d+\/\d+\)\s*$/, "$1")
    .replace(/^(Looking into .+)\s+\(1\/1\)\s*$/, "$1");
}

function ProgressLine({
  text,
  active,
  hint,
}: {
  text: string;
  active: boolean;
  hint?: string;
}) {
  const shown = displayProgressText(text);
  const reason = isReasonLine(shown);
  const body = reason ? shown.replace(/^why:\s*/i, "") : shown;

  if (reason) {
    return (
      <li
        className={cn(
          "ml-6 border-l-2 border-border pl-3 text-xs leading-5 italic",
          active ? "text-foreground" : "text-muted-foreground",
        )}
      >
        <span className="not-italic font-medium text-muted-foreground">
          Because.{" "}
        </span>
        {body}
        {active ? (
          <span className="mt-1 block not-italic text-muted-foreground">
            {hint}
          </span>
        ) : null}
      </li>
    );
  }

  return (
    <li
      className={cn(
        "flex items-start gap-2",
        active ? "font-medium" : "text-muted-foreground",
      )}
    >
      {active ? (
        <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" />
      ) : (
        <CheckIcon className="mt-0.5 size-3.5 shrink-0" />
      )}
      <span>
        {body}
        {active ? (
          <>
            <span className="inline-flex w-4 overflow-hidden">
              <span className="animate-pulse">…</span>
            </span>
            <span className="mt-1 block text-xs font-normal text-muted-foreground">
              {hint}
            </span>
          </>
        ) : null}
      </span>
    </li>
  );
}

function ResearchingState({
  companies,
  job,
  skipOnboard = false,
}: {
  companies: string[];
  job: ResearchJob | null;
  skipOnboard?: boolean;
}) {
  const setJob = useResearchStore((state) => state.setJob);
  const estimate = estimateResearch(companies.length || 1, { skipOnboard });
  const [now, setNow] = useState(Date.now());
  const [localStart] = useState(() => Date.now());
  const [control, setControl] = useState<"skip" | "stop" | null>(null);
  const logRef = useRef<HTMLUListElement>(null);
  const currentCompany = job?.current_company?.trim() || null;
  const stopping =
    Boolean(job?.cancel_requested) ||
    control === "stop" ||
    job?.current === "Stopping research";
  const skipping =
    Boolean(job?.skip_requested) ||
    control === "skip" ||
    Boolean(currentCompany && job?.current === `Skipping ${currentCompany}`);
  const canControl =
    Boolean(job?.job_id) && job?.status === "running" && !stopping;

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const elapsed = job
    ? Math.max(
        0,
        Math.floor((now - (Date.parse(job.started_at) || now)) / 1000),
      )
    : Math.floor((now - localStart) / 1000);
  const activity = job
    ? activityFromJob(job, estimate.typicalMinutes, now)
    : researchActivity(elapsed, companies, estimate.typicalMinutes);
  const hint = waitingHint(activity.current, elapsed);

  useEffect(() => {
    const node = logRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [activity.done.length, activity.current, hint]);

  async function sendControl(action: "skip" | "stop") {
    if (!job?.job_id || !canControl) {
      return;
    }
    setControl(action);
    try {
      const next =
        action === "skip"
          ? await skipResearchCompany(job.job_id)
          : await cancelResearchJob(job.job_id);
      setJob(next);
    } catch {
      setControl(null);
    }
  }

  return (
    <div className="space-y-5 py-1 text-sm">
      <div className="space-y-2">
        <div className="flex items-end justify-between gap-3">
          <p className="font-medium">
            {activity.percent === null ? "Starting…" : `${activity.percent}%`}
          </p>
          <p className="shrink-0 text-right text-muted-foreground">
            {activity.timeLeft ?? "Starting research"}
          </p>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-700"
            style={{ width: `${activity.percent ?? 0}%` }}
          />
        </div>
      </div>
      <ul ref={logRef} className="max-h-80 space-y-2 overflow-y-auto pr-1">
        {activity.done.map((step, index) => (
          <ProgressLine key={`${index}-${step}`} text={step} active={false} />
        ))}
        <ProgressLine text={activity.current} active hint={hint} />
      </ul>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-4">
        {canControl && currentCompany && !skipping ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="max-w-[16rem] text-muted-foreground"
            onClick={() => void sendControl("skip")}
          >
            <span className="truncate">Skip {currentCompany}</span>
          </Button>
        ) : (
          <span />
        )}
        {canControl ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="ml-auto text-muted-foreground"
            onClick={() => void sendControl("stop")}
          >
            Stop research
          </Button>
        ) : stopping ? (
          <p className="ml-auto text-xs text-muted-foreground">Stopping…</p>
        ) : null}
      </div>
    </div>
  );
}

function PhoneField({
  value,
  error,
  onChange,
  onBlur,
  onKeyDown,
}: {
  value: string;
  error: string | null;
  onChange: (value: string) => void;
  onBlur: () => void;
  onKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor="phone">Phone</Label>
      <div
        className={cn(
          "flex h-10 overflow-hidden rounded-lg border border-input bg-background transition-colors",
          "focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50",
          error &&
            "border-destructive ring-3 ring-destructive/20 focus-within:border-destructive focus-within:ring-destructive/20",
        )}
      >
        <span className="flex items-center px-3 text-sm text-muted-foreground select-none">
          +91
        </span>
        <div className="w-px self-stretch bg-border" />
        <Input
          id="phone"
          name="phone"
          type="tel"
          inputMode="numeric"
          autoComplete="tel-national"
          placeholder="9845512210"
          className="h-full rounded-none border-0 bg-transparent focus-visible:border-0 focus-visible:ring-0"
          value={value}
          aria-invalid={Boolean(error)}
          onChange={(event) => onChange(event.target.value)}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          required
        />
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}

function Field({
  id,
  name,
  label,
  hint,
  error,
  ...props
}: React.ComponentProps<typeof Input> & {
  label: string;
  hint?: string;
  error?: string | null;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} name={name} aria-invalid={Boolean(error)} {...props} />
      {error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}

function PeopleList({
  contacts,
  profiles,
}: {
  contacts: Contact[];
  profiles: ContactProfile[];
}) {
  if (contacts.length === 0) {
    return (
      <p className="text-muted-foreground">
        No people listed for this company yet.
      </p>
    );
  }

  return (
    <div>
      <p className="font-medium">People</p>
      <ul className="mt-2 space-y-3">
        {contacts.map((contact) => {
          const profile = profiles.find(
            (item) => item.contact_id === contact.contact_id,
          );
          return (
            <li key={contact.contact_id} className="text-muted-foreground">
              <p className="font-medium text-foreground">
                {contact.full_name}
                {contact.title ? ` · ${contact.title}` : ""}
              </p>
              {profile?.bio ? <p>{profile.bio}</p> : null}
              {profile?.recommended_approach ? (
                <p>
                  <span className="font-medium text-foreground">
                    Approach.{" "}
                  </span>
                  {profile.recommended_approach}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function briefingDraftFrom(
  companies: Company[],
  profiles: CompanyProfile[],
  index: number,
): BriefingDraft | null {
  const profile = profiles[index];
  if (!profile) {
    return null;
  }
  const company = companies.find(
    (item) => item.company_id === profile.company_id,
  );
  return {
    company_id: profile.company_id,
    name: company?.name ?? "",
    executive_summary: profile.executive_summary,
    overall_score: profile.overall_score,
    recommendation: profile.recommendation,
    key_signals: (profile.signals ?? []).map((signal) => signal.description),
    risks: profile.risks,
    recommended_sales_approach: profile.recommended_sales_approach,
  };
}

function Results({
  result,
  onChange,
}: {
  result: ResearchResult;
  onChange: (next: ResearchResult) => void;
}) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const companies = result.companies ?? [];
  const profiles = result.company_profiles ?? [];
  const editing =
    editingIndex === null
      ? null
      : briefingDraftFrom(companies, profiles, editingIndex);

  return (
    <div id="research-results" className="space-y-6">
      <Alert>
        <AlertTitle>
          Check these briefings for {result.user.company.name}
        </AlertTitle>
        <AlertDescription>
          {companies.length} compan
          {companies.length === 1 ? "y" : "ies"} researched for{" "}
          {result.user.full_name}. Edit anything that looks off, then open
          Companies to see people and engage.
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
            <p>{result.user.email}</p>
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
        {profiles.map((profile, index) => {
          const company = companies.find(
            (item) => item.company_id === profile.company_id,
          );
          const signals = (profile.signals ?? []).map(
            (signal) => signal.description,
          );
          return (
            <Card key={profile.profile_id || `${profile.company_id}-${index}`}>
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle>{company?.name ?? "Company"}</CardTitle>
                  <Badge variant="secondary">
                    Score {profile.overall_score.toFixed(0)}
                  </Badge>
                  <Badge variant="outline">{profile.recommendation}</Badge>
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
                <p>{profile.executive_summary}</p>
                <div>
                  <p className="font-medium">Why they look interesting</p>
                  <ul className="list-disc pl-5 text-muted-foreground">
                    {signals.map((signal) => (
                      <li key={signal}>{signal}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="font-medium">Watch-outs</p>
                  <ul className="list-disc pl-5 text-muted-foreground">
                    {profile.risks.map((risk) => (
                      <li key={risk}>{risk}</li>
                    ))}
                  </ul>
                </div>
                <p>
                  <span className="font-medium">Suggested approach. </span>
                  {profile.recommended_sales_approach}
                </p>
                <PeopleList
                  contacts={(result.contacts ?? []).filter(
                    (contact) => contact.company_id === profile.company_id,
                  )}
                  profiles={(result.contact_profiles ?? []).filter(
                    (item) => item.company_id === profile.company_id,
                  )}
                />
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="flex justify-end">
        <Link href="/companies" className={buttonVariants()}>
          Open companies
        </Link>
      </div>

      <BriefingEditDialog
        report={editing}
        onClose={() => setEditingIndex(null)}
        onSave={(next) => {
          const problem = validateBriefing(next);
          if (problem) {
            useResearchStore.getState().showError(problem);
            return;
          }
          if (editingIndex === null) {
            return;
          }
          const nextCompanies = companies.slice();
          const nextProfiles = profiles.slice();
          const companyIndex = nextCompanies.findIndex(
            (item) => item.company_id === next.company_id,
          );
          if (companyIndex >= 0) {
            nextCompanies[companyIndex] = {
              ...nextCompanies[companyIndex],
              name: next.name,
            };
          }
          nextProfiles[editingIndex] = {
            ...nextProfiles[editingIndex],
            executive_summary: next.executive_summary,
            overall_score: next.overall_score,
            recommendation: next.recommendation,
            signals: next.key_signals.map((description) => ({
              type: "research",
              description,
              strength: "medium",
            })),
            risks: next.risks,
            recommended_sales_approach: next.recommended_sales_approach,
          };
          onChange({
            ...result,
            companies: nextCompanies,
            company_profiles: nextProfiles,
          });
          setEditingIndex(null);
        }}
      />
    </div>
  );
}
