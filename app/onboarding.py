from __future__ import annotations

from pydantic import BaseModel, Field

from config.excon_schemas import (
    Product,
    SellerCompany,
    SenderVoice,
    User,
)
from llm.client import LLMClient
from llm.json_util import generate_model
from tools.website_reader import WebsiteReaderTool

from app.report_mapper import slug


class InferredProduct(BaseModel):
    name: str
    category: str = "Product"
    description: str
    icp: str = "Not specified on the company website."
    target_industries: list[str] = Field(default_factory=list)
    value_props: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)
    typical_buyers: list[str] = Field(default_factory=list)


class InferredSeller(BaseModel):
    title: str = "Account Executive"
    company: SellerCompany
    products: list[InferredProduct] = Field(default_factory=list)
    tone: str = "professional and concise"
    cta: str = "Suggest a 20-minute working session."


class OnboardingAgent:
    def __init__(self, llm=None, reader=None):
        self.llm = llm or LLMClient()
        self.reader = reader or WebsiteReaderTool()

    def enroll(
        self,
        full_name: str,
        phone: str,
        email: str,
        website: str,
        title: str | None = None,
    ) -> tuple[User, list[Product]]:
        page_text = self._read_site(website)
        inferred = self._infer(full_name, email, website, page_text)

        seller_title = (title or inferred.title or "Account Executive").strip()
        products = [
            self._to_product(item, index)
            for index, item in enumerate(inferred.products, start=1)
        ]
        if not products:
            products = [
                self._to_product(
                    InferredProduct(
                        name=inferred.company.name or "Core offering",
                        description=inferred.company.description,
                    ),
                    1,
                )
            ]

        user = User(
            user_id=slug(email or full_name, "us"),
            full_name=full_name.strip(),
            title=seller_title,
            email=email.strip(),
            phone=phone.strip() or None,
            company=inferred.company,
            voice=SenderVoice(
                tone=inferred.tone,
                signature=f"{full_name.strip()}\n{email.strip()}",
                cta=inferred.cta,
            ),
            product_ids=[product.product_id for product in products],
        )
        return user, products

    def _read_site(self, website: str) -> str:
        try:
            page = self.reader.execute(url=website)
        except Exception as exc:
            print(f"[Onboarding] Could not fetch website ({exc}). Using URL only.")
            return f"Website URL: {website}\nPage could not be fetched."

        text = page.content[:6000]
        return (
            f"Title: {page.title}\n"
            f"URL: {page.url}\n"
            f"Content:\n{text}"
        )

    def _infer(
        self,
        full_name: str,
        email: str,
        website: str,
        page_text: str,
    ) -> InferredSeller:
        prompt = f"""
You are onboarding a salesperson onto ProspectIQ.

Extract the seller's company and the products or services
it sells from the website text. Use ONLY this text.
Do not invent customers, metrics, or proof points.

Seller name: {full_name}
Seller email: {email}
Website: {website}

Website text:
{page_text}

Return ONLY valid JSON:
{{
  "title": "likely seller title or Account Executive",
  "company": {{
    "name": "...",
    "industry": "...",
    "website": "{website}",
    "size": "unknown if not stated",
    "headquarters": "unknown if not stated",
    "description": "2-4 sentences"
  }},
  "products": [
    {{
      "name": "...",
      "category": "...",
      "description": "...",
      "icp": "...",
      "target_industries": ["..."],
      "value_props": ["..."],
      "use_cases": ["..."],
      "differentiators": ["..."],
      "typical_buyers": ["..."]
    }}
  ],
  "tone": "professional and concise",
  "cta": "Suggest a 20-minute working session."
}}
"""
        inferred = generate_model(
            self.llm,
            InferredSeller,
            prompt,
            temperature=0.0,
            max_tokens=900,
        )
        inferred.company.website = website
        return inferred

    @staticmethod
    def _to_product(item: InferredProduct, index: int) -> Product:
        return Product(
            product_id=slug(item.name, "pd") + f"_{index}",
            name=item.name,
            category=item.category,
            description=item.description,
            icp=item.icp,
            target_industries=item.target_industries,
            value_props=item.value_props,
            use_cases=item.use_cases,
            differentiators=item.differentiators,
            objections=[],
            typical_buyers=item.typical_buyers,
        )
