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
