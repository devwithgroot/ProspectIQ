import { fetchApi } from "@/lib/api";
import type {
  ContactRow,
  MockBundle,
  MockProduct,
  ProspectRow,
} from "@/lib/mock-types";

export const fetchMockBundle = async (): Promise<MockBundle> => {
  const response = await fetchApi("/api/mock/bundle", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Could not load mock dashboard data.");
  }
  return response.json();
};

export const buildProspectRows = (bundle: MockBundle): ProspectRow[] => {
  const profileByCompany = new Map(
    bundle.company_profiles.map((profile) => [profile.company_id, profile]),
  );
  const productById = new Map(
    bundle.products.map((product) => [product.product_id, product]),
  );
  const contactCountByCompany = bundle.contacts.reduce<Record<string, number>>(
    (acc, contact) => {
      acc[contact.company_id] = (acc[contact.company_id] ?? 0) + 1;
      return acc;
    },
    {},
  );

  return bundle.companies
    .map((company) => {
      const profile = profileByCompany.get(company.company_id) ?? null;
      const matched_products: MockProduct[] = (
        profile?.matched_product_ids ?? []
      )
        .map((id) => productById.get(id))
        .filter((product): product is MockProduct => Boolean(product));

      return {
        ...company,
        profile,
        matched_products,
        contact_count: contactCountByCompany[company.company_id] ?? 0,
      };
    })
    .sort(
      (a, b) =>
        (b.profile?.overall_score ?? 0) - (a.profile?.overall_score ?? 0),
    );
};

export const isContactSuppressed = (
  bundle: MockBundle,
  contactId: string,
): boolean => {
  const contact = bundle.contacts.find((item) => item.contact_id === contactId);
  if (!contact) {
    return true;
  }
  if (contact.do_not_contact) {
    return true;
  }

  return bundle.do_not_contact.some((entry) => {
    if (entry.kind === "contact_id") {
      return entry.value === contact.contact_id;
    }
    if (entry.kind === "email") {
      return Boolean(contact.email) && entry.value === contact.email;
    }
    if (entry.kind === "phone") {
      return (
        (Boolean(contact.phone) && entry.value === contact.phone) ||
        (Boolean(contact.whatsapp_number) &&
          entry.value === contact.whatsapp_number)
      );
    }
    return false;
  });
};

export const buildContactRows = (
  bundle: MockBundle,
  companyId?: string,
): ContactRow[] => {
  const profileByContact = new Map(
    bundle.contact_profiles.map((profile) => [profile.contact_id, profile]),
  );
  const companyById = new Map(
    bundle.companies.map((company) => [company.company_id, company]),
  );

  return bundle.contacts
    .filter((contact) => (companyId ? contact.company_id === companyId : true))
    .map((contact) => ({
      ...contact,
      profile: profileByContact.get(contact.contact_id) ?? null,
      company_name: companyById.get(contact.company_id)?.name ?? "Unknown",
      suppressed: isContactSuppressed(bundle, contact.contact_id),
    }));
};

export const recommendationVariant = (
  recommendation: string,
): "default" | "secondary" | "outline" => {
  const value = recommendation.toLowerCase();
  if (value.includes("high")) {
    return "default";
  }
  if (value.includes("potential")) {
    return "secondary";
  }
  return "outline";
};

export const formatRole = (role: string): string => role.replaceAll("_", " ");
