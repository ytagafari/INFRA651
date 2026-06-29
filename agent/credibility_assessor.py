"""Assess customer credibility from company name and meeting context."""

from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from agent.knowledge_retriever import SHEETS, tokenize

_INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "agriculture": ["silo", "grain", "agriculture", "farm", "senssilo", "storage"],
    "OEM weighbridge": ["oem", "weighbridge", "truck", "scale", "m740", "load cell"],
    "cement/industrial": ["cement", "industrial", "theft", "security", "plant"],
    "scales OEM": ["laumas", "scales", "slovakia", "modbus", "diniargeo"],
    "software/SaaS": ["saas", "subscription", "cloud", "pricing"],
}


@dataclass
class CredibilityResult:
    company: str
    industry: str
    estimated_size: str
    country: str
    credibility_score: int
    credibility_level: str
    signals: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _read_company_index() -> list[dict[str, str]]:
    path = SHEETS / "Company-Index.csv"
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _normalize_company(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _lookup_company(company: str, rows: list[dict[str, str]]) -> dict[str, str] | None:
    target = _normalize_company(company)
    for row in rows:
        if _normalize_company(row.get("company", "")) == target:
            return row
    for row in rows:
        indexed = _normalize_company(row.get("company", ""))
        if indexed and (indexed in target or target in indexed):
            return row
    return None


def _infer_industry(topics: str, notes: str) -> str:
    text = f"{topics} {notes}".lower()
    tokens = set(tokenize(text))
    best_industry = "general industrial"
    best_score = 0
    for industry, keywords in _INDUSTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in tokens or kw in text)
        if score > best_score:
            best_score = score
            best_industry = industry
    return best_industry


def _score_level(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 60:
        return "medium-high"
    if score >= 40:
        return "medium"
    return "low"


def assess_credibility(company: str, discussion_topics: str, notes: str = "") -> CredibilityResult:
    company = company.strip()
    topics = discussion_topics.strip()
    notes = notes.strip()
    rows = _read_company_index()
    match = _lookup_company(company, rows)

    industry = match.get("industry", "") if match else _infer_industry(topics, notes)
    size = match.get("size", "unknown") if match else "SME"
    country = match.get("country", "") if match else ""
    public_profile = match.get("public_profile", "") if match else ""

    score = 35
    signals: list[str] = []
    risks: list[str] = []

    if match:
        score += 25
        signals.append(f"Known company profile: {match.get('credibility_hint', 'indexed')}")
        if public_profile:
            signals.append(public_profile)
    else:
        risks.append("No indexed public company profile — verify independently")

    if re.search(r"\b(gmbh|s\.r\.o|ltd|inc|ag|s\.a\.)\b", company, re.I):
        score += 8
        signals.append("Registered company suffix in name")

    if re.search(r"\b\d+\b", notes):
        score += 10
        signals.append("Specific operational detail in notes (quantified need)")

    topic_tokens = tokenize(f"{topics} {notes}")
    if len(topic_tokens) >= 4:
        score += 8
        signals.append("Clear discussion topics aligned with UCS product lines")

    if any(k in topic_tokens for k in ("pricing", "saas", "quote", "certification", "oiml", "ce")):
        score += 7
        signals.append("Commercial or compliance intent mentioned")

    if any(k in topic_tokens for k in ("silo", "truck", "weighbridge", "m740", "sensweight", "senssilo")):
        score += 10
        signals.append("Strong product/application fit with UCS portfolio")

    if not notes.strip():
        score -= 5
        risks.append("No meeting notes — limited context for assessment")

    score = max(0, min(100, score))
    level = _score_level(score)

    summary_parts = [f"{company} assessed as {level} credibility ({score}/100)."]
    summary_parts.append(f"Industry: {industry}. Estimated size: {size}.")
    if country:
        summary_parts.append(f"Country/region: {country}.")
    if signals:
        summary_parts.append("Signals: " + "; ".join(signals[:3]) + ".")
    if risks:
        summary_parts.append("Risks: " + "; ".join(risks) + ".")

    return CredibilityResult(
        company=company,
        industry=industry,
        estimated_size=size,
        country=country,
        credibility_score=score,
        credibility_level=level,
        signals=signals,
        risks=risks,
        summary=" ".join(summary_parts),
    )
