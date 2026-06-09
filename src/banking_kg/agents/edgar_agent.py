from sec_edgar_downloader import Downloader
import os
from pathlib import Path
from typing import Dict, List, Optional
import re
from datetime import datetime
from ..llm_factory import get_llm, robust_parse_json
from langchain_core.prompts import ChatPromptTemplate


class EdgarFinancialAgent:
    """Agent for extracting financial data from SEC EDGAR (10-K, 10-Q)"""

    # Common ticker aliases / normalisation: LLM sometimes returns display names
    # instead of the official EDGAR ticker.
    TICKER_ALIASES = {
        "3M": "MMM",
        "3M CO": "MMM",
        "3M COMPANY": "MMM",
        "BRK.A": "BRK-A",
        "BRK.B": "BRK-B",
        "GOOGL": "GOOGL",
        "META": "META",
    }

    # Foreign-exchange suffixes that have no EDGAR CIK — skip gracefully
    FOREIGN_SUFFIXES = (".KS", ".HK", ".TYO", ".L", ".DE", ".PA", ".AS", ".TO", ".AX")

    @classmethod
    def _normalise_ticker(cls, ticker: str) -> str | None:
        """Return canonical EDGAR ticker, or None if foreign/invalid."""
        t = ticker.strip().upper()
        # Foreign exchange
        for suffix in cls.FOREIGN_SUFFIXES:
            if t.endswith(suffix.upper()):
                return None
        # Known aliases
        return cls.TICKER_ALIASES.get(t, t)

    def __init__(self, company_email: str = None):
        self.email = company_email or os.getenv("USER_EMAIL", "user@example.com")
        self.company_name = os.getenv("COMPANY_NAME", "ResearchApp")
        self.download_dir = Path("./data/edgar_downloads")
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Version 5.x API - takes company_name and email_address separately
        print(f"📊 Edgar: Initializing with email={self.email}")

        self.downloader = Downloader(self.company_name, self.email)

        from ..llm_factory import get_llm
        self.llm = get_llm(temperature=0)

    def get_latest_filing_date(self, ticker: str, filing_type: str = "10-K") -> str | None:
        """Check SEC EDGAR submissions API to get the date of the most recent filing.
        Returns ISO date string (e.g. '2025-12-31') or None on failure.
        Does NOT download anything — reads lightweight JSON metadata only (~20KB).
        """
        import requests

        canonical = self._normalise_ticker(ticker)
        if not canonical:
            return None

        headers = {"User-Agent": f"{self.company_name} {self.email}"}
        try:
            # Step 1: resolve ticker → CIK via SEC company_tickers.json
            tickers_r = requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers=headers, timeout=10
            )
            tickers_r.raise_for_status()
            tickers_data = tickers_r.json()

            cik = None
            for entry in tickers_data.values():
                if entry.get("ticker", "").upper() == canonical.upper():
                    cik = str(entry["cik_str"]).zfill(10)
                    break
            if not cik:
                return None

            # Step 2: fetch submissions metadata
            sub_r = requests.get(
                f"https://data.sec.gov/submissions/CIK{cik}.json",
                headers=headers, timeout=15
            )
            sub_r.raise_for_status()
            sub_data = sub_r.json()

            recent = sub_data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])

            for form, date in zip(forms, dates):
                if form == filing_type:
                    return date  # list is most-recent-first
        except Exception as e:
            print(f"   ⚠️  EDGAR freshness check failed for {ticker}: {e}")

        return None

    def is_filing_stale(self, ticker: str, cached_period: str,
                        filing_type: str = "10-K") -> bool:
        """Return True if EDGAR has a newer filing than what we have cached.

        Fast path: if the filing already exists on disk, skip the SEC API call
        entirely — the disk file is the source of truth for what we downloaded.
        cached_period: the filing_period string we stored (e.g. 'FY2024', 'Q1 2026').
        """
        # ── Disk fast-path ────────────────────────────────────────────────
        # If we already have the file on disk the downloader would just re-download
        # the same thing anyway.  Trust the Neo4j TTL to decide freshness instead.
        for base in [self.download_dir / "sec-edgar-filings", Path("./sec-edgar-filings")]:
            company_dir = base / ticker / filing_type
            if company_dir.exists():
                filing_dirs = [d for d in company_dir.iterdir() if d.is_dir()]
                if filing_dirs:
                    return False  # files on disk — let Neo4j TTL decide
        # ─────────────────────────────────────────────────────────────────

        latest_date = self.get_latest_filing_date(ticker, filing_type)
        if not latest_date:
            return False  # can't determine — keep cache

        # Normalise cached period to year for simple comparison
        import re
        cached_year_match = re.search(r"20\d{2}", cached_period or "")
        if not cached_year_match:
            return True  # unknown format — refresh to be safe
        cached_year = int(cached_year_match.group())
        latest_year = int(latest_date[:4])
        return latest_year > cached_year

    def fetch_filings(self, ticker: str, filing_type: str = "10-K",
                     num_filings: int = 1) -> List[Path]:
        """Return paths to SEC filings, downloading only if not already on disk."""
        try:
            # ── Disk cache check ──────────────────────────────────────────
            # sec-edgar-filings may be under download_dir or project root
            for base in [self.download_dir / "sec-edgar-filings", Path("./sec-edgar-filings")]:
                company_dir = base / ticker / filing_type
                if company_dir.exists():
                    filing_dirs = sorted(
                        [d for d in company_dir.iterdir() if d.is_dir()],
                        key=lambda x: x.name, reverse=True
                    )
                    cached_filings: List[Path] = []
                    for filing_dir in filing_dirs[:num_filings]:
                        for filename in ["full-submission.txt", "primary-document.html",
                                         "filing-details.xml"]:
                            fp = filing_dir / filename
                            if fp.exists():
                                cached_filings.append(fp)
                                break
                        else:
                            files_in_dir = list(filing_dir.glob("*"))
                            if files_in_dir:
                                cached_filings.append(files_in_dir[0])
                    if cached_filings:
                        print(f"   ✅ Disk cache hit: {len(cached_filings)} {filing_type} filing(s) for {ticker} — skipping download")
                        return cached_filings
            # ─────────────────────────────────────────────────────────────

            print(f"   Downloading {filing_type} for {ticker} to {self.download_dir}")

            # Version 5.x saves to current directory / sec-edgar-filings
            # Change to download directory first
            original_dir = os.getcwd()
            os.chdir(self.download_dir)

            try:
                # Version 5.x API: get(filing_type, ticker, limit=X)
                num_downloaded = self.downloader.get(filing_type, ticker, limit=num_filings)
                print(f"   Downloader returned: {num_downloaded}")
            finally:
                os.chdir(original_dir)

            # Check where files were actually saved
            company_dir = self.download_dir / "sec-edgar-filings" / ticker / filing_type

            if not company_dir.exists():
                alt_company_dir = Path("./sec-edgar-filings") / ticker / filing_type
                if alt_company_dir.exists():
                    print(f"   ℹ️  Found files in project root: {alt_company_dir}")
                    company_dir = alt_company_dir
                else:
                    print(f"   ❌ Directory not found: {company_dir}")
                    return []

            filing_dirs = sorted([d for d in company_dir.iterdir() if d.is_dir()],
                               key=lambda x: x.name, reverse=True)
            print(f"   Found {len(filing_dirs)} filing directories")

            filings = []
            for filing_dir in filing_dirs[:num_filings]:
                for filename in ["full-submission.txt", "primary-document.html", "filing-details.xml"]:
                    file_path = filing_dir / filename
                    if file_path.exists():
                        print(f"   ✅ Found file: {file_path.name} in {filing_dir.name}")
                        filings.append(file_path)
                        break
                else:
                    files_in_dir = list(filing_dir.glob("*"))
                    if files_in_dir:
                        print(f"   📁 Files in {filing_dir.name}: {[f.name for f in files_in_dir[:5]]}")
                        filings.append(files_in_dir[0])

            return filings

        except Exception as e:
            print(f"❌ Error fetching {filing_type} for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def _smart_extract(filing_path: Path, max_chars: int) -> str:
        """
        Smart text extraction from SEC full-submission.txt (SGML or HTML wrapper).

        Strategy:
        1. Scan raw bytes for 'ixt:num-dot-decimal' — the XBRL marker that only
           appears on actual financial-statement table cells (not notes/MD&A prose).
        2. If found, read 5 KB before → 80 KB after that byte offset; strip HTML.
        3. If not found (older plain-text filing), fall back to keyword search in
           the stripped full document text.

        Returns up to max_chars of financial-table content.
        """
        import re as _re

        # ── Step 1: Scan for the EARLIEST iXBRL financial-statement anchor ──────
        # Large filers (GM, Ford, JPMorgan…) split the 10-K into separate HTML
        # sections: the income statement can be 100–200 KB before the balance
        # sheet in the raw file.  Scanning for the income-statement anchor first
        # ensures the 14k text window starts there, not mid-balance-sheet.
        #
        # Priority order — scan ALL anchors in one pass and keep the minimum offset:
        #   IS anchors  : Revenues, OperatingIncomeLoss  (appear before the BS)
        #   BS anchors  : Assets, StockholdersEquity     (fallback if IS not tagged)
        IS_ANCHORS = [
            b'name="us-gaap:Revenues"',
            b"name='us-gaap:Revenues'",
            b'name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"',
            b'name="us-gaap:OperatingIncomeLoss"',
            b"name='us-gaap:OperatingIncomeLoss'",
        ]
        BS_ANCHORS = [
            b'name="us-gaap:Assets"',
            b"name='us-gaap:Assets'",
            b'name="us-gaap:StockholdersEquity"',
            b'name="us-gaap:NetIncomeLoss"',
        ]
        ALL_ANCHORS = IS_ANCHORS + BS_ANCHORS

        xbrl_offset = -1
        chunk_size = 300_000
        scan_limit = 12_000_000

        # Collect ALL anchor positions in one sequential scan, then pick the min.
        candidate_offsets = {}  # anchor_bytes → file_offset
        with filing_path.open('rb') as fh:
            overlap = b''
            pos = 0
            remaining = set(ALL_ANCHORS)
            while pos < scan_limit and remaining:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                combined = overlap + chunk
                found_this_chunk = set()
                for anchor in list(remaining):
                    idx = combined.find(anchor)
                    if idx != -1:
                        candidate_offsets[anchor] = pos - len(overlap) + idx
                        found_this_chunk.add(anchor)
                remaining -= found_this_chunk
                # Stop early once we have at least one IS anchor
                if any(a in candidate_offsets for a in IS_ANCHORS):
                    break
                overlap = combined[-50:]
                pos += len(chunk)

        if candidate_offsets:
            # Prefer the earliest IS anchor; fall back to earliest BS anchor
            is_hits = {a: o for a, o in candidate_offsets.items() if a in IS_ANCHORS}
            xbrl_offset = min(is_hits.values()) if is_hits else min(candidate_offsets.values())

        if xbrl_offset > 0:
            # ── Step 2a: Read raw window starting at the earliest anchor ─────
            # Go back 2 KB to catch the statement header, then read 155 KB to
            # cover BS + equity + cash flow statements that follow.
            read_start = max(0, xbrl_offset - 2_000)
            read_len = 155_000
            with filing_path.open('rb') as fh:
                fh.seek(read_start)
                raw = fh.read(read_len).decode('utf-8', errors='ignore')
        else:
            # ── Step 2b: Fallback — read first 12 MB and locate TEXT section ──
            with filing_path.open('rb') as fh:
                raw = fh.read(scan_limit).decode('utf-8', errors='ignore')
            # Extract primary 10-K/10-Q document from SGML wrapper
            if '<SEC-DOCUMENT' in raw[:200] or '<DOCUMENT>' in raw[:2000]:
                doc_m = _re.search(
                    r'<DOCUMENT>.*?<TYPE>\s*(10-[KQ][^\s<]*)',
                    raw[:500_000], _re.DOTALL | _re.IGNORECASE
                )
                if doc_m:
                    txt_m = _re.search(
                        r'<TEXT>(.*)', raw[doc_m.start():], _re.DOTALL | _re.IGNORECASE
                    )
                    if txt_m:
                        raw = txt_m.group(1)

        # ── Step 3: Strip HTML and clean whitespace ─────────────────────────────
        text = _re.sub(r'<[^>]+>', ' ', raw)
        text = _re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
        text = _re.sub(r'\s{3,}', '\n', text).strip()

        # ── Step 4: In fallback mode, jump to the first actual financial table ──
        if xbrl_offset <= 0:
            fin_keywords = [
                'CONSOLIDATED BALANCE SHEETS',
                'CONSOLIDATED BALANCE SHEET',
                'CONDENSED CONSOLIDATED BALANCE SHEETS',
                'CONSOLIDATED STATEMENTS OF OPERATIONS',
                'CONSOLIDATED STATEMENTS OF INCOME',
            ]
            lower = text.lower()
            table_pos = -1
            for kw in fin_keywords:
                search_from = 0
                while True:
                    pos = lower.find(kw.lower(), search_from)
                    if pos == -1:
                        break
                    # Require "December"/"ASSETS"/dollar+digit within 600 chars
                    after = text[pos:pos + 600]
                    if _re.search(r'(December|March|June|September|ASSETS|\$\s*\d)', after, _re.IGNORECASE):
                        table_pos = pos
                        break
                    search_from = pos + 1
                if table_pos != -1:
                    break
            if table_pos > 0:
                text = text[max(0, table_pos - 100):]

        return text[:max_chars]

    def extract_financial_metrics(self, filing_path: Path, max_chars: int = 150000) -> Dict:
        """Extract key financial metrics from filing using Claude."""
        import time as _time
        import os as _os
        # Ollama has a small context window — use smart extraction targeting financial sections
        is_ollama = _os.getenv("LLM_PROVIDER", "anthropic").lower() == "ollama"
        if is_ollama:
            max_chars = 14000
        try:
            if is_ollama:
                # Smart extraction: find financial statements section in SGML/HTML filing
                content = self._smart_extract(filing_path, max_chars)
            else:
                raw = filing_path.read_text(encoding='utf-8', errors='ignore')
                import re as _re
                plain = _re.sub(r'<[^>]+>', ' ', raw)
                plain = _re.sub(r'&[a-zA-Z0-9#]+;', ' ', plain)
                plain = _re.sub(r'\s{3,}', '\n', plain).strip()
                content = plain[:max_chars]

            extraction_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a financial analyst extracting data from an SEC filing (10-K or 10-Q).
Extract ALL of the following fields and return ONLY a valid JSON object — no markdown, no explanation.

All dollar amounts must be in MILLIONS USD (numeric, no commas or symbols). Use null for any field not found.

--- FILING META ---
filing_period: fiscal year or quarter string (e.g. "FY2024", "Q3 2024")
filing_date: period end date as YYYY-MM-DD
filing_type: "10-K" or "10-Q"

--- INCOME STATEMENT ---
revenue: total revenues / net revenues
gross_profit: revenue minus cost of goods sold
operating_income: income from operations
ebitda: earnings before interest, taxes, depreciation, and amortization (calculate if not stated)
net_income: net income / net earnings
eps_basic: basic earnings per share (numeric)
eps_diluted: diluted earnings per share (numeric)

--- BALANCE SHEET ---
cash_and_equivalents: cash and cash equivalents
short_term_investments: short-term marketable securities / investments
total_current_assets: total current assets
total_assets: total assets
total_current_liabilities: total current liabilities
long_term_debt: long-term debt / notes payable
total_liabilities: total liabilities
stockholders_equity: total stockholders equity / shareholders equity
shares_outstanding: diluted shares outstanding in millions

--- CASH FLOW STATEMENT ---
operating_cash_flow: net cash provided by / used in operating activities
capital_expenditures: purchases of property plant and equipment (positive number)
free_cash_flow: operating_cash_flow minus capital_expenditures (calculate if not stated)
investing_cash_flow: net cash used in / provided by investing activities
financing_cash_flow: net cash used in / provided by financing activities
dividends_paid: dividends paid to shareholders (positive number, null if none)
share_repurchases: repurchase of common stock (positive number, null if none)

--- QUALITATIVE ---
key_risks: list of up to 5 short risk strings (each under 15 words)
business_summary: one sentence describing what the company does

Return ONLY the JSON object."""),
                ("user", "SEC filing:\n\n{filing_content}")
            ])

            chain = extraction_prompt | self.llm

            # Retry with exponential backoff on 429 rate-limit errors
            response = None
            for attempt in range(4):
                try:
                    response = chain.invoke({"filing_content": content})
                    break
                except Exception as llm_err:
                    err_str = str(llm_err)
                    if "429" in err_str or "rate_limit" in err_str:
                        wait = 20 * (2 ** attempt)  # 20s, 40s, 80s, 160s
                        print(f"   ⏳ Rate limited — waiting {wait}s before retry (attempt {attempt+1}/4)...")
                        _time.sleep(wait)
                    else:
                        raise
            if response is None:
                raise ValueError("All retry attempts failed due to rate limiting")

            metrics = robust_parse_json(response.content, {})
            if not metrics:
                raise ValueError("LLM returned empty/non-JSON response")
            metrics["source_file"] = str(filing_path)
            metrics["extracted_at"] = datetime.now().isoformat()
            return metrics

        except Exception as e:
            print(f"❌ Error extracting metrics from {filing_path}: {e}")
            return {
                "error": str(e),
                "source_file": str(filing_path),
                "extracted_at": datetime.now().isoformat()
            }

    def get_company_financials(self, ticker: str, filing_types: List[str] = None,
                               peer_mode: bool = False) -> Dict:
        """Get comprehensive financial data for a company.

        peer_mode=True uses a smaller context slice (60k chars) to reduce token
        usage when processing multiple peer companies back-to-back.
        """
        if filing_types is None:
            filing_types = ["10-K", "10-Q"]

        # Peer companies: only pull 10-K (latest annual), smaller slice
        max_chars = 60000 if peer_mode else 150000

        canonical = self._normalise_ticker(ticker)
        if canonical is None:
            print(f"   ⏭️  Skipping {ticker}: foreign exchange ticker, no EDGAR CIK")
            return {"ticker": ticker, "filings": [], "skipped": "foreign_ticker"}

        print(f"\n📊 Edgar Agent: Starting financial research for ticker '{canonical}'")

        results = {
            "ticker": canonical,
            "filings": []
        }

        for filing_type in filing_types:
            print(f"   Fetching {filing_type} filings...")
            filings = self.fetch_filings(canonical, filing_type, num_filings=1)
            print(f"   Found {len(filings)} {filing_type} filing(s)")

            for filing_path in filings:
                print(f"   Processing {filing_type} from {filing_path.parent.name}...")
                metrics = self.extract_financial_metrics(filing_path, max_chars=max_chars)
                metrics["filing_type"] = filing_type

                # Log what we extracted
                if "error" in metrics:
                    print(f"   ❌ Error extracting metrics: {metrics['error']}")
                else:
                    print(f"   ✅ Extracted: Period={metrics.get('filing_period')}, Revenue={metrics.get('revenue')}")

                results["filings"].append(metrics)

        print(f"📊 Edgar Agent: Completed. Total filings extracted: {len(results['filings'])}\n")
        return results

    def analyze_financial_health(self, financials: Dict) -> Dict:
        """Analyze financial health using Claude"""
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a commercial banking analyst assessing company financial health.
Based on the financial data provided, analyze:
1. Financial strength (liquidity, solvency)
2. Growth trends
3. Risk factors for a commercial lender
4. Credit worthiness indicators

Provide a concise analysis in JSON format with:
- overall_rating: "strong" | "moderate" | "weak"
- liquidity_score: 1-10
- key_strengths: list of 2-3 strengths
- key_concerns: list of 2-3 concerns
- lending_recommendation: brief recommendation for a commercial banker"""),
            ("user", "Analyze this financial data:\n\n{financial_data}")
        ])

        try:
            import json
            chain = analysis_prompt | self.llm
            response = chain.invoke({"financial_data": json.dumps(financials, indent=2)})

            # Parse response
            result = robust_parse_json(response.content, {"overall_rating": "unknown"})
            return result

        except Exception as e:
            print(f"Error analyzing financial health: {e}")
            return {
                "error": str(e),
                "overall_rating": "unknown"
            }
