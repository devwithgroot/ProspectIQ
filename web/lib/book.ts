import type {
  Channel,
  ComposeMeta,
  Contact,
  ResearchResult,
  SellerBook,
} from "@/lib/types"

export function emptyBook(): SellerBook {
  return {
    user: null,
    products: [],
    companies: [],
    company_profiles: [],
    contacts: [],
    contact_profiles: [],
  }
}

export function normalizeCompanyName(name: string): string {
  return name.trim().toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()
}

export function normalizeWebsite(url: string): string {
  return url
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .replace(/\/+$/, "")
}

export function canReuseSeller(book: SellerBook, website: string): boolean {
  const saved = book.user?.company.website
  if (!saved || !book.products.length) {
    return false
  }
  return normalizeWebsite(saved) === normalizeWebsite(website)
}

export function mergeBook(book: SellerBook, result: ResearchResult): SellerBook {
  const incoming = new Set(
    (result.companies ?? []).map((company) => company.company_id),
  )
  return {
    user: result.user ?? book.user,
    products: result.products?.length ? result.products : book.products,
    companies: [
      ...book.companies.filter((item) => !incoming.has(item.company_id)),
      ...(result.companies ?? []),
    ],
    company_profiles: [
      ...book.company_profiles.filter((item) => !incoming.has(item.company_id)),
      ...(result.company_profiles ?? []),
    ],
    contacts: [
      ...book.contacts.filter((item) => !incoming.has(item.company_id)),
      ...(result.contacts ?? []),
    ],
    contact_profiles: [
      ...book.contact_profiles.filter((item) => !incoming.has(item.company_id)),
      ...(result.contact_profiles ?? []),
    ],
  }
}

export function isKnownCompany(book: SellerBook, name: string): boolean {
  const key = normalizeCompanyName(name)
  if (!key) {
    return false
  }
  return book.companies.some(
    (company) => normalizeCompanyName(company.name) === key,
  )
}

export function bookToResult(book: SellerBook): ResearchResult | null {
  if (!book.user) {
    return null
  }
  return {
    user: book.user,
    products: book.products,
    companies: book.companies,
    company_profiles: book.company_profiles,
    contacts: book.contacts,
    contact_profiles: book.contact_profiles,
  }
}

export function contactHandle(contact: Contact, channel: Channel): string | null {
  const mapping: Record<Channel, string | null | undefined> = {
    email: contact.email,
    linkedin: contact.linkedin_url,
    whatsapp: contact.whatsapp_number,
    slack: contact.slack_user_id,
    sms: contact.phone,
  }
  const value = mapping[channel]?.trim()
  return value || null
}

export function engagementKey(contactId: string, channel: string): string {
  return `${contactId}:${channel}`
}

export function composeMetaFor(
  book: SellerBook,
  contact: Contact | null,
  contactName = "",
): ComposeMeta {
  const user = book.user
  return {
    fromName: user?.full_name ?? "",
    fromEmail: user?.outreach_email || user?.email || "",
    fromTitle: user?.title,
    fromCompany: user?.company.name,
    toName: contact?.full_name || contactName,
    toTitle: contact?.title,
    toEmail: contact?.email ?? null,
    toLinkedIn: contact?.linkedin_url ?? null,
    toPhone: contact?.phone ?? null,
    toWhatsapp: contact?.whatsapp_number ?? contact?.phone ?? null,
    toSlack: contact?.slack_user_id ?? null,
  }
}
