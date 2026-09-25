import rawCatalog from "./catalog-data.json"

export type CatalogOption = {
  id: string
  label: string
}

export type TitleOption = CatalogOption & {
  group: "Common in this industry" | "Sales and leadership"
}

export type Catalog = {
  industries: CatalogOption[]
  titles: CatalogOption[]
  titles_by_industry: Record<string, TitleOption[]>
}

type RawCatalog = {
  industries: CatalogOption[]
  titles: CatalogOption[]
  common_title_ids: string[]
  titles_by_industry: Record<string, string[]>
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export function buildCatalog(raw: RawCatalog): Catalog {
  const titles = Object.fromEntries(
    raw.titles.map((title) => [title.id, title.label])
  )
  const titles_by_industry: Record<string, TitleOption[]> = {}

  for (const industry of raw.industries) {
    const specific = new Set(raw.titles_by_industry[industry.id] ?? [])
    const seen = new Set<string>()
    const options: TitleOption[] = []
    for (const titleId of [
      ...(raw.titles_by_industry[industry.id] ?? []),
      ...raw.common_title_ids,
    ]) {
      if (seen.has(titleId) || !titles[titleId]) {
        continue
      }
      seen.add(titleId)
      options.push({
        id: titleId,
        label: titles[titleId],
        group: specific.has(titleId)
          ? "Common in this industry"
          : "Sales and leadership",
      })
    }
    titles_by_industry[industry.id] = options
    titles_by_industry[industry.label] = options
  }

  return {
    industries: raw.industries,
    titles: raw.titles,
    titles_by_industry,
  }
}

export const bundledCatalog = buildCatalog(rawCatalog)

export async function fetchCatalog(): Promise<Catalog> {
  const response = await fetch(`${API_URL}/api/catalog`)
  if (!response.ok) {
    return bundledCatalog
  }
  return (await response.json()) as Catalog
}

export function titlesForIndustry(
  catalog: Catalog,
  industry: string
): TitleOption[] {
  return catalog.titles_by_industry[industry] ?? []
}

export function isAllowedTitle(
  catalog: Catalog,
  industry: string,
  title: string
): boolean {
  return titlesForIndustry(catalog, industry).some(
    (option) => option.label === title
  )
}

const STOP_WORDS = new Set(["of", "and", "the", "a", "an", "for", "to", "or"])

function compact(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "")
}

export function catalogInitials(label: string): string {
  const words = label
    .replace(/[()]/g, " ")
    .split(/[\s/,&-]+/)
    .filter((word) => word && !STOP_WORDS.has(word.toLowerCase()))
  if (words.length < 2) {
    return ""
  }
  return words.map((word) => word[0] ?? "").join("").toUpperCase()
}

export function catalogSearchTerms(option: {
  id: string
  label: string
}): string[] {
  return [
    option.label,
    option.id,
    option.id.replaceAll("_", " "),
    option.id.replaceAll("_", ""),
    catalogInitials(option.label),
  ]
}

function words(value: string): string[] {
  return value.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)
}

export function catalogOptionMatches(
  option: { id: string; label: string },
  query: string
): boolean {
  const needle = query.trim().toLowerCase()
  if (!needle) {
    return true
  }
  const compactNeedle = compact(needle)
  return catalogSearchTerms(option).some((term) => {
    const lower = term.toLowerCase()
    const squeezed = compact(term)
    if (lower === needle || squeezed === compactNeedle) {
      return true
    }
    if (lower.startsWith(needle) || squeezed.startsWith(compactNeedle)) {
      return true
    }
    if (words(term).some((word) => word.startsWith(needle))) {
      return true
    }
    if (needle.length >= 3 && lower.includes(needle)) {
      return true
    }
    return compactNeedle.length >= 3 && squeezed.includes(compactNeedle)
  })
}

export function rankCatalogMatch(
  option: { id: string; label: string },
  query: string
): number {
  const needle = query.trim().toLowerCase()
  const compactNeedle = compact(needle)
  const id = compact(option.id)
  const initials = catalogInitials(option.label).toLowerCase()
  const label = option.label.toLowerCase()
  if (id === compactNeedle || initials === compactNeedle) {
    return 0
  }
  if (id.startsWith(compactNeedle) || initials.startsWith(compactNeedle)) {
    return 1
  }
  if (label.startsWith(needle)) {
    return 2
  }
  return 3
}

export function catalogShortcut(option: {
  id: string
  label: string
}): string | null {
  if (!option.id.includes("_") && option.id.length >= 2 && option.id.length <= 4) {
    return option.id.toUpperCase()
  }
  return null
}
