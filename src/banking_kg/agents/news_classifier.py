"""
News Classifier — PRD Dimension 3: News & Sentiment

Responsibilities:
  - Sentiment classification (positive / neutral / negative)
  - Severity scoring (high / medium / low)
  - Key event extraction (acquisitions, lawsuits, leadership changes, etc.)
  - Noise / promotional content filtering
  - Material-event flagging for creditworthiness assessment
"""

from typing import Dict, List, Optional
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
import os
import json
from datetime import datetime


# ── Event taxonomy ─────────────────────────────────────────────────────────────
KEY_EVENT_TYPES = [
    "acquisition",
    "merger",
    "divestiture",
    "ipo",
    "bankruptcy",
    "restructuring",
    "layoffs",
    "leadership_change",       # CEO/CFO/board changes
    "lawsuit",
    "regulatory_action",       # fines, investigations, consent orders
    "fraud_allegation",
    "data_breach",
    "product_recall",
    "earnings_surprise",       # significant beat or miss
    "credit_rating_change",
    "strategic_partnership",
    "contract_win",
    "expansion",
    "other",
]

MATERIAL_EVENT_TYPES = {
    "bankruptcy", "fraud_allegation", "regulatory_action",
    "lawsuit", "data_breach", "credit_rating_change", "restructuring",
}


class NewsClassifier:
    """
    Classifies individual news items and computes an aggregate
    sentiment / risk profile for a company.
    """

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=api_key,
            temperature=0,
        )

        self._classify_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a commercial banking risk analyst classifying news items.

For each news item return a JSON object with these fields:
- sentiment: "positive" | "neutral" | "negative"
- severity: "high" | "medium" | "low"
  (high = material impact on creditworthiness or reputation;
   medium = noteworthy but manageable;
   low = minor or routine)
- event_types: list of event types from this set:
  {event_types}
  (may be empty list if no key event)
- is_material: true if the event could affect credit decisions, otherwise false
- is_noise: true if the article is promotional, sponsored, or clearly irrelevant
- key_facts: list of ≤3 concise bullet-point facts extracted from the snippet
- summary: 1-2 sentence plain-English summary

Return ONLY valid JSON — no markdown, no explanation."""),
            ("user",
             "Company: {company_name}\n\n"
             "Title: {title}\n"
             "Snippet: {snippet}\n"
             "URL: {url}"),
        ])

        self._batch_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a commercial banking risk analyst classifying a batch of news items.

For each item return a JSON object with:
- id: the item's id field (preserve exactly)
- sentiment: "positive" | "neutral" | "negative"
- severity: "high" | "medium" | "low"
- event_types: list from: {event_types}
- is_material: boolean
- is_noise: boolean
- key_facts: list of ≤3 bullet-point facts
- summary: 1-2 sentence summary

Return a JSON array — one object per input item, same order.
Return ONLY valid JSON — no markdown, no explanation."""),
            ("user",
             "Company: {company_name}\n\n"
             "News items:\n{items_json}"),
        ])

        self._aggregate_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a commercial banking risk analyst summarising classified news.

Given classified news items, return a JSON object with:
- overall_sentiment: "positive" | "neutral" | "negative"
- risk_level: "low" | "medium" | "high"
- key_concerns: list of top ≤3 concerns for a commercial lender
- positive_signals: list of positive signals (empty list if none)
- material_events: list of event_type strings that are material
- summary: 2-3 sentence overall assessment for a relationship manager

Return ONLY valid JSON — no markdown."""),
            ("user",
             "Company: {company_name}\n\n"
             "Classified news items:\n{items_json}"),
        ])

    # ── Public API ──────────────────────────────────────────────────────────────

    def classify_item(
        self,
        company_name: str,
        title: str,
        snippet: str,
        url: str = "",
    ) -> Dict:
        """Classify a single news item."""
        try:
            chain = self._classify_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "title": title,
                "snippet": snippet,
                "url": url,
                "event_types": ", ".join(KEY_EVENT_TYPES),
            })
            return self._parse_json(response.content)
        except Exception as e:
            return self._fallback_classification(str(e))

    def classify_batch(
        self,
        company_name: str,
        items: List[Dict],
    ) -> List[Dict]:
        """
        Classify a list of news items in a single LLM call.

        Each item should have at minimum: id, title, snippet.
        Returns the original items enriched with classification fields.
        """
        if not items:
            return []

        # Attach sequential IDs if missing
        for i, item in enumerate(items):
            item.setdefault("id", i)

        slim = [
            {"id": it["id"], "title": it.get("title", ""), "snippet": it.get("snippet", it.get("summary", ""))}
            for it in items
        ]

        try:
            chain = self._batch_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "items_json": json.dumps(slim, indent=2),
                "event_types": ", ".join(KEY_EVENT_TYPES),
            })
            classifications = self._parse_json(response.content)
            if not isinstance(classifications, list):
                raise ValueError("Expected a JSON array")

            # Merge classifications back onto the original items
            cls_by_id = {c["id"]: c for c in classifications}
            enriched = []
            for item in items:
                cls = cls_by_id.get(item["id"], self._fallback_classification())
                enriched.append({**item, **cls})
            return enriched

        except Exception as e:
            print(f"[NewsClassifier] batch classify error: {e}")
            return [{**it, **self._fallback_classification(str(e))} for it in items]

    def filter_noise(self, items: List[Dict]) -> List[Dict]:
        """Remove items flagged as noise/promotional."""
        return [it for it in items if not it.get("is_noise", False)]

    def material_events(self, items: List[Dict]) -> List[Dict]:
        """Return only items flagged as material (credit-relevant)."""
        return [it for it in items if it.get("is_material", False)]

    def aggregate(self, company_name: str, classified_items: List[Dict]) -> Dict:
        """
        Produce an aggregate sentiment / risk profile from a list
        of already-classified news items.
        """
        if not classified_items:
            return {
                "overall_sentiment": "neutral",
                "risk_level": "low",
                "key_concerns": [],
                "positive_signals": [],
                "material_events": [],
                "summary": "No significant news found.",
                "analyzed_at": datetime.now().isoformat(),
            }

        try:
            chain = self._aggregate_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "items_json": json.dumps(classified_items, indent=2),
            })
            result = self._parse_json(response.content)
            result["analyzed_at"] = datetime.now().isoformat()
            return result
        except Exception as e:
            print(f"[NewsClassifier] aggregate error: {e}")
            return self._fallback_aggregate(classified_items)

    # ── Helpers ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json(text: str) -> any:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # strip opening/closing fence
            inner = [l for l in lines if not l.startswith("```")]
            text = "\n".join(inner).strip()
        return json.loads(text)

    @staticmethod
    def _fallback_classification(error: Optional[str] = None) -> Dict:
        return {
            "sentiment": "neutral",
            "severity": "low",
            "event_types": [],
            "is_material": False,
            "is_noise": False,
            "key_facts": [],
            "summary": "Classification unavailable.",
            **({"_error": error} if error else {}),
        }

    @staticmethod
    def _fallback_aggregate(items: List[Dict]) -> Dict:
        """Rule-based fallback when LLM aggregation fails."""
        sentiments = [it.get("severity") for it in items]
        risk = "high" if "high" in sentiments else ("medium" if "medium" in sentiments else "low")
        neg = sum(1 for it in items if it.get("sentiment") == "negative")
        pos = sum(1 for it in items if it.get("sentiment") == "positive")
        overall = "negative" if neg > pos else ("positive" if pos > neg else "neutral")
        material = list({
            et for it in items if it.get("is_material")
            for et in it.get("event_types", [])
        })
        return {
            "overall_sentiment": overall,
            "risk_level": risk,
            "key_concerns": [],
            "positive_signals": [],
            "material_events": material,
            "summary": f"Found {len(items)} news items ({neg} negative, {pos} positive).",
            "analyzed_at": datetime.now().isoformat(),
        }
