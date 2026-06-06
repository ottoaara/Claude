"""
Pre-Meeting Intelligence Brief — PDF report generator.
Requires: reportlab  (pip install reportlab)
"""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ─── Brand colours ─────────────────────────────────────────────────────────────
WF_RED    = colors.HexColor("#D71E28")
WF_DARK   = colors.HexColor("#333333")
WF_GRAY   = colors.HexColor("#666666")
WF_LIGHT  = colors.HexColor("#F5F5F5")
WF_BORDER = colors.HexColor("#CCCCCC")
WF_GOLD   = colors.HexColor("#C8A951")
WF_WHITE  = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _fmt_usd(val) -> str:
    """Format a numeric value as $ with B/M suffix."""
    if val is None:
        return "N/A"
    try:
        n = float(val)
    except (TypeError, ValueError):
        return str(val)
    if abs(n) >= 1e9:
        return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"${n/1e6:.1f}M"
    return f"${n:,.0f}"


def _fmt_pct(val) -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.1f}%"
    except (TypeError, ValueError):
        return str(val)


def _trunc(text: str, max_len: int = 300) -> str:
    if not text:
        return ""
    return text[:max_len] + ("…" if len(text) > max_len else "")


def _net_margin(revenue, net_income) -> Optional[float]:
    try:
        r, n = float(revenue), float(net_income)
        if r != 0:
            return round(n / r * 100, 1)
    except (TypeError, ValueError):
        pass
    return None


# ─── Styles ──────────────────────────────────────────────────────────────────
def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_company": ParagraphStyle(
            "cover_company",
            fontName="Helvetica-Bold",
            fontSize=32,
            textColor=WF_WHITE,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontName="Helvetica",
            fontSize=14,
            textColor=WF_WHITE,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_date": ParagraphStyle(
            "cover_date",
            fontName="Helvetica",
            fontSize=11,
            textColor=colors.HexColor("#DDDDDD"),
            alignment=TA_CENTER,
        ),
        "section_heading": ParagraphStyle(
            "section_heading",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=WF_RED,
            spaceBefore=14,
            spaceAfter=4,
        ),
        "sub_heading": ParagraphStyle(
            "sub_heading",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=WF_DARK,
            spaceBefore=6,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=WF_DARK,
            spaceBefore=2,
            spaceAfter=2,
            leading=13,
        ),
        "body_small": ParagraphStyle(
            "body_small",
            fontName="Helvetica",
            fontSize=8,
            textColor=WF_GRAY,
            spaceBefore=1,
            spaceAfter=1,
            leading=11,
        ),
        "risk_flag": ParagraphStyle(
            "risk_flag",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.HexColor("#CC0000"),
            spaceBefore=1,
            spaceAfter=1,
        ),
        "caption": ParagraphStyle(
            "caption",
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=WF_GRAY,
            alignment=TA_RIGHT,
        ),
    }


# ─── Table styles ─────────────────────────────────────────────────────────────
def _table_style_header() -> TableStyle:
    return TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), WF_RED),
        ("TEXTCOLOR",   (0, 0), (-1, 0), WF_WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 8),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("TEXTCOLOR",   (0, 1), (-1, -1), WF_DARK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WF_WHITE, WF_LIGHT]),
        ("GRID",        (0, 0), (-1, -1), 0.3, WF_BORDER),
        ("ALIGN",       (1, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])


# ─── Cover page ──────────────────────────────────────────────────────────────
def _cover_page(company_name: str, ticker: Optional[str], styles: Dict) -> List:
    content = []

    # Full-bleed red banner (simulated via a table cell)
    banner_text = (
        f"<b>{company_name}</b>"
        + (f"  |  {ticker}" if ticker else "")
    )
    cover_table = Table(
        [[Paragraph(banner_text, styles["cover_company"]),]],
        colWidths=[PAGE_W - 2 * MARGIN],
    )
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WF_RED),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 60),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 60),
    ]))
    content.append(cover_table)
    content.append(Spacer(1, 0.5 * cm))

    content.append(Paragraph("Pre-Meeting Intelligence Brief", styles["cover_sub"]))
    content.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y  |  %H:%M UTC')}",
        styles["cover_date"],
    ))
    content.append(Spacer(1, 1 * cm))
    content.append(HRFlowable(width="100%", thickness=1, color=WF_BORDER))
    content.append(Spacer(1, 0.3 * cm))
    content.append(Paragraph(
        "CONFIDENTIAL — For Internal Use Only.  "
        "This document was generated by the Context Fabric intelligence platform.",
        styles["body_small"],
    ))
    content.append(PageBreak())
    return content


# ─── Section: Company Overview ────────────────────────────────────────────────
def _section_overview(company: Dict, styles: Dict) -> List:
    content = [Paragraph("1. Company Overview", styles["section_heading"])]
    content.append(HRFlowable(width="100%", thickness=1, color=WF_RED))
    content.append(Spacer(1, 0.2 * cm))

    rows = [
        ["Ticker",     company.get("ticker") or "—"],
        ["Sector",     company.get("sector") or "—"],
        ["NAICS",      company.get("naics") or "—"],
        ["Website",    company.get("website") or "—"],
        ["Employees",  str(company.get("employee_count") or "—")],
        ["HQ",         company.get("headquarters") or "—"],
        ["Founded",    str(company.get("founded") or "—")],
    ]
    col_w = [(PAGE_W - 2 * MARGIN) * x for x in [0.28, 0.72]]
    tbl = Table(rows, colWidths=col_w)
    tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), WF_DARK),
        ("GRID",      (0, 0), (-1, -1), 0.3, WF_BORDER),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WF_LIGHT, WF_WHITE]),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    content.append(tbl)

    summary = company.get("company_summary") or company.get("description") or company.get("summary")
    if summary:
        content.append(Spacer(1, 0.3 * cm))
        content.append(Paragraph(_trunc(str(summary), 600), styles["body"]))

    return content


# ─── Section: Financial Highlights ───────────────────────────────────────────
def _section_financials(financials: List[Dict], styles: Dict) -> List:
    if not financials:
        return []

    content = [Spacer(1, 0.4 * cm), Paragraph("2. Financial Highlights", styles["section_heading"])]
    content.append(HRFlowable(width="100%", thickness=1, color=WF_RED))
    content.append(Spacer(1, 0.2 * cm))

    # Sort by filing_date desc, show up to 4
    def _sort_key(f):
        return f.get("filing_date") or f.get("period") or ""
    sorted_f = sorted(financials, key=_sort_key, reverse=True)[:4]

    header = ["Period", "Type", "Revenue", "Net Income", "Total Assets", "Net Margin"]
    rows = [header]
    for f in sorted_f:
        rev = f.get("revenue")
        ni  = f.get("net_income")
        rows.append([
            f.get("period") or f.get("filing_date") or "—",
            f.get("filing_type") or "—",
            _fmt_usd(rev),
            _fmt_usd(ni),
            _fmt_usd(f.get("total_assets")),
            _fmt_pct(_net_margin(rev, ni)),
        ])

    col_w = [(PAGE_W - 2 * MARGIN) * x for x in [0.18, 0.10, 0.18, 0.18, 0.18, 0.18]]
    tbl = Table(rows, colWidths=col_w)
    tbl.setStyle(_table_style_header())
    content.append(tbl)
    return content


# ─── Section: Peer Comparison ─────────────────────────────────────────────────
def _section_peers(peer_data: Dict, styles: Dict) -> List:
    if not peer_data:
        return []

    target  = peer_data.get("target", {})
    peers   = peer_data.get("peers", [])
    if not target and not peers:
        return []

    content = [Spacer(1, 0.4 * cm), Paragraph("3. Peer Comparison", styles["section_heading"])]
    content.append(HRFlowable(width="100%", thickness=1, color=WF_RED))
    content.append(Spacer(1, 0.2 * cm))

    header = ["Company", "Revenue", "Net Income", "Total Assets", "Net Margin", "Filing"]
    rows   = [header]

    def _row(rec: Dict, bold: bool = False) -> List:
        rev = rec.get("revenue")
        ni  = rec.get("net_income")
        return [
            rec.get("name") or "—",
            _fmt_usd(rev),
            _fmt_usd(ni),
            _fmt_usd(rec.get("total_assets")),
            _fmt_pct(_net_margin(rev, ni)),
            rec.get("filing_period") or rec.get("period") or "—",
        ]

    if target:
        rows.append(_row(target))
    for p in peers[:8]:
        rows.append(_row(p))

    col_w = [(PAGE_W - 2 * MARGIN) * x for x in [0.24, 0.16, 0.16, 0.16, 0.14, 0.14]]
    tbl = Table(rows, colWidths=col_w)
    style = _table_style_header()
    # Bold the target row (row index 1)
    if target:
        style.add("FONTNAME",   (0, 1), (-1, 1), "Helvetica-Bold")
        style.add("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FFF0F0"))
    tbl.setStyle(style)
    content.append(tbl)
    return content


# ─── Section: Industry ────────────────────────────────────────────────────────
def _section_industry(industries: List[Dict], styles: Dict) -> List:
    if not industries:
        return []

    content = [Spacer(1, 0.4 * cm), Paragraph("4. Industry & Market Position", styles["section_heading"])]
    content.append(HRFlowable(width="100%", thickness=1, color=WF_RED))
    content.append(Spacer(1, 0.2 * cm))

    for ind in industries[:2]:
        name = ind.get("industry_name") or ind.get("name") or "—"
        code = ind.get("naics_code") or ind.get("naics") or ""
        content.append(Paragraph(f"<b>{name}</b> {('(NAICS: ' + code + ')') if code else ''}", styles["sub_heading"]))

        trends = ind.get("trends") or ind.get("industry_trends")
        if trends:
            if isinstance(trends, list):
                for t in trends[:5]:
                    content.append(Paragraph(f"• {t}", styles["body"]))
            else:
                content.append(Paragraph(_trunc(str(trends), 400), styles["body"]))

        drivers = ind.get("key_drivers")
        if drivers:
            content.append(Paragraph("<b>Key Drivers:</b>", styles["sub_heading"]))
            items = drivers if isinstance(drivers, list) else [drivers]
            for d in items[:4]:
                content.append(Paragraph(f"• {d}", styles["body"]))

    return content


# ─── Section: News & Risk ─────────────────────────────────────────────────────
def _section_news(news: List[Dict], styles: Dict) -> List:
    if not news:
        return []

    content = [Spacer(1, 0.4 * cm), Paragraph("5. News & Risk Signals", styles["section_heading"])]
    content.append(HRFlowable(width="100%", thickness=1, color=WF_RED))
    content.append(Spacer(1, 0.2 * cm))

    SENT_COLOR = {"negative": "#CC0000", "positive": "#006600", "neutral": "#666666"}

    # Sort: material first, then by date
    sorted_news = sorted(
        news,
        key=lambda n: (-(1 if n.get("is_material") else 0), n.get("date") or ""),
        reverse=False
    )[:12]

    for item in sorted_news:
        title    = item.get("title") or item.get("headline") or "Untitled"
        date_str = item.get("date") or item.get("published_at") or ""
        sent     = (item.get("sentiment") or "neutral").lower()
        severity = item.get("severity") or ""
        is_mat   = item.get("is_material")
        source   = item.get("source") or item.get("publisher") or ""

        sent_color = SENT_COLOR.get(sent, "#666666")
        mat_badge  = " [MATERIAL]" if is_mat else ""
        sev_badge  = f" [{severity.upper()}]" if severity else ""

        header_text = (
            f'<font color="{sent_color}"><b>{title}{mat_badge}{sev_badge}</b></font>'
        )
        meta = f"{date_str}  |  {source}  |  Sentiment: {sent.capitalize()}"
        content.append(Paragraph(header_text, styles["body"]))
        content.append(Paragraph(meta, styles["body_small"]))

        summary = item.get("summary") or item.get("description") or item.get("content")
        if summary:
            content.append(Paragraph(_trunc(str(summary), 200), styles["body_small"]))

        content.append(Spacer(1, 0.15 * cm))

    return content


# ─── Section: Officers ────────────────────────────────────────────────────────
def _section_officers(officers: List[Dict], styles: Dict) -> List:
    if not officers:
        return []

    content = [Spacer(1, 0.4 * cm), Paragraph("6. Key Officers", styles["section_heading"])]
    content.append(HRFlowable(width="100%", thickness=1, color=WF_RED))
    content.append(Spacer(1, 0.2 * cm))

    for officer in officers[:8]:
        name  = officer.get("name") or "—"
        role  = officer.get("role") or ""
        conf  = officer.get("confidence") or "low"
        since = officer.get("tenure_since")
        years = officer.get("tenure_years")

        header = f"<b>{name}</b>  —  {role}"
        if since:
            header += f"  (since {since})"
        elif years:
            header += f"  ({years}yr tenure)"
        header += f"  <font color='#888888'>[{conf} confidence]</font>"

        content.append(Paragraph(header, styles["sub_heading"]))

        bg = officer.get("background_summary")
        if bg and bg != "Profile unavailable.":
            content.append(Paragraph(_trunc(bg, 300), styles["body"]))

        br = officer.get("banking_relevance")
        if br:
            content.append(Paragraph(f"<i>Banking Relevance: {_trunc(br, 200)}</i>", styles["body_small"]))

        risk = officer.get("risk_flags")
        if risk:
            flags = risk if isinstance(risk, list) else [risk]
            for f in flags[:3]:
                content.append(Paragraph(f"⚠ {f}", styles["risk_flag"]))

        linkedin = officer.get("linkedin_url")
        if linkedin:
            content.append(Paragraph(f"LinkedIn: {linkedin}", styles["body_small"]))

        content.append(Spacer(1, 0.2 * cm))

    return content


# ─── Section: Products ────────────────────────────────────────────────────────
def _section_products(products: List[Dict], styles: Dict) -> List:
    if not products:
        return []

    content = [Spacer(1, 0.4 * cm), Paragraph("7. Product & Service Portfolio", styles["section_heading"])]
    content.append(HRFlowable(width="100%", thickness=1, color=WF_RED))
    content.append(Spacer(1, 0.2 * cm))

    for p in products[:10]:
        name = p.get("name") or p.get("product_name") or "—"
        cat  = p.get("category") or p.get("type") or ""
        desc = p.get("description") or ""
        label = f"<b>{name}</b>" + (f"  <font color='#888888'>({cat})</font>" if cat else "")
        content.append(Paragraph(label, styles["sub_heading"]))
        if desc:
            content.append(Paragraph(_trunc(desc, 200), styles["body_small"]))

    return content


# ─── Footer callback ──────────────────────────────────────────────────────────
class _FooterCanvas:
    """Adds page numbers and confidentiality footer."""

    def __init__(self, company_name: str):
        self.company_name = company_name

    def __call__(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(WF_GRAY)

        # Left footer
        canvas.drawString(
            MARGIN, 0.8 * cm,
            f"CONFIDENTIAL — {self.company_name} | Pre-Meeting Intelligence Brief"
        )
        # Right footer — page number
        canvas.drawRightString(
            PAGE_W - MARGIN, 0.8 * cm,
            f"Page {doc.page}"
        )
        # Top banner stripe (thin red line)
        canvas.setFillColor(WF_RED)
        canvas.rect(0, PAGE_H - 0.35 * cm, PAGE_W, 0.35 * cm, fill=1, stroke=0)
        canvas.restoreState()


# ─── Main entry point ─────────────────────────────────────────────────────────
def generate_pdf(
    company_name: str,
    graph_data: Dict,
    peer_data: Optional[Dict] = None,
    officers: Optional[List[Dict]] = None,
) -> bytes:
    """
    Generate a PDF intelligence brief and return raw bytes.

    Parameters
    ----------
    company_name : str
    graph_data   : result of BankingKnowledgeGraph.get_company_graph()
    peer_data    : result of BankingKnowledgeGraph.get_peer_comparison() — optional
    officers     : result of BankingKnowledgeGraph.get_officers() — optional
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN + 0.6 * cm,
        bottomMargin=MARGIN,
        title=f"{company_name} — Intelligence Brief",
        author="Context Fabric Platform",
    )

    styles = _styles()
    company  = graph_data.get("company", {})
    ticker   = company.get("ticker")

    story: List = []

    # Cover
    story.extend(_cover_page(company_name, ticker, styles))

    # Overview
    story.extend(_section_overview(company, styles))

    # Financials
    story.extend(_section_financials(graph_data.get("financials", []), styles))

    # Peer comparison
    if peer_data:
        story.extend(_section_peers(peer_data, styles))

    story.append(PageBreak())

    # Industry
    story.extend(_section_industry(graph_data.get("industries", []), styles))

    # News
    story.extend(_section_news(graph_data.get("news", []), styles))

    story.append(PageBreak())

    # Officers
    story.extend(_section_officers(officers or [], styles))

    # Products
    story.extend(_section_products(graph_data.get("products", []), styles))

    # Final footnote
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=WF_BORDER))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Report generated by the Context Fabric Platform on "
        f"{datetime.now().strftime('%Y-%m-%d at %H:%M')}. "
        "Data sourced from SEC EDGAR, public news, and web research. "
        "For internal sales preparation only.",
        styles["body_small"],
    ))

    footer = _FooterCanvas(company_name)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    buf.seek(0)
    return buf.read()
