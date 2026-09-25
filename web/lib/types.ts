export type Product = {
  product_id: string
  name: string
  category: string
  description: string
}

export type Company = {
  company_id: string
  name: string
  website: string | null
}

export type CompanySignal = {
  type: string
  description: string
  strength: string
  evidence?: string | null
}

export type CompanyProfile = {
  profile_id: string
  company_id: string
  executive_summary: string
  overall_score: number
  recommendation: string
  signals: CompanySignal[]
  risks: string[]
  recommended_sales_approach: string
}

export type Contact = {
  contact_id: string
  company_id: string
  full_name: string
  title: string
  linkedin_url?: string | null
}

export type ContactProfile = {
  profile_id: string
  contact_id: string
  company_id: string
  bio: string
  talking_points: string[]
  recommended_approach: string
}

export type Seller = {
  full_name: string
  title: string
  email: string
  outreach_email: string
  outreach_email_verified: boolean
  phone: string | null
  company: {
    name: string
    industry: string
    website: string
    description: string
  }
}

export type StagedProspect = {
  id: string
  company_name: string
  website: string | null
  notes: string | null
}

export type StagingPreview = {
  file_name: string
  count: number
  companies: StagedProspect[]
}

export type ResearchResult = {
  user: Seller
  products: Product[]
  companies: Company[]
  company_profiles: CompanyProfile[]
  contacts: Contact[]
  contact_profiles: ContactProfile[]
}

export type OutreachDraft = {
  draft_id: string
  contact_id: string
  company_id: string
  channel: string
  subject: string | null
  body: string
  rationale: string
  status: string
}

export type OutreachDraftResponse = {
  batch_id: string
  company_id: string
  contact_id: string
  contact_name: string
  skipped_reason: string | null
  drafts: OutreachDraft[]
  dry_run: boolean
}

export type ResearchJobStatus =
  | "running"
  | "done"
  | "error"
  | "lost"
  | "cancelled"

export type ResearchJob = {
  job_id: string
  status: ResearchJobStatus
  started_at: string
  companies: string[]
  current: string
  current_company?: string | null
  done: string[]
  percent: number
  result?: ResearchResult | null
  error?: string | null
  cancel_requested?: boolean
  skip_requested?: boolean
}
