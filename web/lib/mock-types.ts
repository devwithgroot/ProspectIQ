export type Channel = "email" | "linkedin" | "whatsapp" | "slack" | "sms";

export type DecisionRole =
  | "economic_buyer"
  | "champion"
  | "influencer"
  | "blocker";

export type ChannelConsent = {
  email: boolean;
  linkedin: boolean;
  whatsapp: boolean;
  slack: boolean;
  sms: boolean;
};

export type MockProduct = {
  product_id: string;
  name: string;
  category: string;
  description: string;
  icp: string;
  target_industries: string[];
  value_props: string[];
  use_cases: string[];
  differentiators: string[];
  objections: string[];
  typical_buyers: string[];
  pricing_model: string | null;
  proof_points: string[];
};

export type MockCompany = {
  company_id: string;
  name: string;
  website: string | null;
  industry: string;
  headquarters: string | null;
  employee_count: number | null;
  founded_year: number | null;
  description: string;
  products_services: string[];
  sources: string[];
};

export type CompanySignal = {
  type: string;
  description: string;
  strength: string;
  evidence?: string | null;
};

export type MockCompanyProfile = {
  profile_id: string;
  company_id: string;
  executive_summary: string;
  overall_score: number;
  recommendation: string;
  signals: CompanySignal[];
  pain_points: string[];
  risks: string[];
  recommended_sales_approach: string;
  why_relevant_to_user: string;
  matched_product_ids: string[];
};

export type MockContact = {
  contact_id: string;
  company_id: string;
  full_name: string;
  title: string;
  seniority: string;
  department: string;
  decision_role: DecisionRole;
  email: string | null;
  phone: string | null;
  linkedin_url: string | null;
  whatsapp_number: string | null;
  slack_user_id: string | null;
  preferred_channel: Channel;
  consent: ChannelConsent;
  do_not_contact: boolean;
  timezone: string;
};

export type MockContactProfile = {
  profile_id: string;
  contact_id: string;
  company_id: string;
  bio: string;
  responsibilities: string[];
  interests: string[];
  recent_activity: string[];
  communication_style: string;
  likely_pain_vs_product: string;
  talking_points: string[];
  risks: string[];
  recommended_approach: string;
  language: string;
};

export type DoNotContactEntry = {
  kind: "contact_id" | "email" | "phone";
  value: string;
  reason: string | null;
};

export type MockUser = {
  user_id: string;
  full_name: string;
  title: string;
  email: string;
  outreach_email: string;
  outreach_email_verified: boolean;
  phone: string | null;
  linkedin_url: string | null;
  locale: string;
  product_ids: string[];
  company: {
    name: string;
    industry: string;
    website: string;
    size: string;
    description: string;
    headquarters: string | null;
  };
  voice: {
    tone: string;
    signature: string;
    calendar_link: string | null;
    cta: string;
  };
};

export type MockBundle = {
  user: MockUser;
  products: MockProduct[];
  companies: MockCompany[];
  company_profiles: MockCompanyProfile[];
  contacts: MockContact[];
  contact_profiles: MockContactProfile[];
  do_not_contact: DoNotContactEntry[];
};

export type ProspectRow = MockCompany & {
  profile: MockCompanyProfile | null;
  matched_products: MockProduct[];
  contact_count: number;
};

export type ContactRow = MockContact & {
  profile: MockContactProfile | null;
  company_name: string;
  suppressed: boolean;
};
