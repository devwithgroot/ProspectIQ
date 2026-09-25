export type Product = {
  product_id: string
  name: string
  category: string
  description: string
}

export type Prospect = {
  prospect_id: string
  company_name: string
  website: string | null
  overall_score: number
  recommendation: string
}

export type ProspectReport = {
  company_name: string
  executive_summary: string
  prospect_score: number
  recommendation: string
  key_signals: string[]
  risks: string[]
  recommended_sales_approach: string
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
  prospects: Prospect[]
  reports: ProspectReport[]
}

export type ResearchJobStatus = "running" | "done" | "error" | "lost"

export type ResearchJob = {
  job_id: string
  status: ResearchJobStatus
  started_at: string
  companies: string[]
  current: string
  done: string[]
  percent: number
  result?: ResearchResult | null
  error?: string | null
}
