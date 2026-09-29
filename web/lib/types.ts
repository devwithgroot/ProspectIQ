export type Product = {
  product_id: string
  name: string
  category: string
  description: string
  icp?: string
  target_industries?: string[]
  value_props?: string[]
  use_cases?: string[]
  differentiators?: string[]
  objections?: string[]
  typical_buyers?: string[]
}

export type Channel = "email" | "linkedin" | "whatsapp" | "slack" | "sms"

export type Company = {
  company_id: string
  name: string
  website: string | null
  industry?: string
  headquarters?: string | null
  description?: string
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
  pain_points?: string[]
  risks: string[]
  recommended_sales_approach: string
  why_relevant_to_user?: string
  matched_product_ids?: string[]
}

export type ChannelConsent = {
  email?: boolean
  linkedin?: boolean
  whatsapp?: boolean
  slack?: boolean
  sms?: boolean
}

export type Contact = {
  contact_id: string
  company_id: string
  full_name: string
  title: string
  department?: string
  decision_role?: string
  email?: string | null
  phone?: string | null
  linkedin_url?: string | null
  whatsapp_number?: string | null
  slack_user_id?: string | null
  preferred_channel?: Channel
  consent?: ChannelConsent
  do_not_contact?: boolean
}

export type ContactProfile = {
  profile_id: string
  contact_id: string
  company_id: string
  bio: string
  talking_points: string[]
  risks?: string[]
  communication_style?: string
  likely_pain_vs_product?: string
  recommended_approach: string
}

export type User = {
  user_id?: string
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
    size?: string
    headquarters?: string | null
  }
  voice?: {
    tone: string
    signature: string
    cta: string
  }
  product_ids?: string[]
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
  user: User
  products: Product[]
  companies: Company[]
  company_profiles: CompanyProfile[]
  contacts: Contact[]
  contact_profiles: ContactProfile[]
}

export type SellerBook = {
  user: User | null
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

export type EngagementStatus = "draft" | "approved" | "sent"

export type EngagementDraft = {
  contact_id: string
  company_id: string
  contact_name: string
  channel: string
  subject: string
  body: string
  rationale: string
  status: EngagementStatus
  skipped_reason: string | null
  dry_run: boolean
}

export type ComposeMeta = {
  fromName: string
  fromEmail: string
  fromTitle?: string
  fromCompany?: string
  toName: string
  toTitle?: string
  toEmail: string | null
  toLinkedIn: string | null
  toPhone: string | null
  toWhatsapp: string | null
  toSlack: string | null
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
  error_detail?: string | null
  cancel_requested?: boolean
  skip_requested?: boolean
}
