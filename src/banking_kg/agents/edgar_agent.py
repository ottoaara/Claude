from sec_edgar_downloader import Downloader
import os
from pathlib import Path
from typing import Dict, List, Optional
import re
from datetime import datetime
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate


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
        self.company_name = os.getenv("COMPANY_NAME", "WellsFargoBank")
        self.download_dir = Path("./data/edgar_downloads")
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Version 5.x API - takes company_name and email_address separately
        print(f"📊 Edgar: Initializing with company={self.company_name}, email={self.email}")

        self.downloader = Downloader(self.company_name, self.email)

        # Initialize Claude for financial data extraction
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=api_key,
            temperature=0
        )

    def fetch_filings(self, ticker: str, filing_type: str = "10-K",
                     num_filings: int = 1) -> List[Path]:
        """Download SEC filings for a company"""
        try:
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
            # Version 5.x saves to current directory / sec-edgar-filings
            # We changed to download_dir, so files should be there
            company_dir = self.download_dir / "sec-edgar-filings" / ticker / filing_type

            # But also check the project root in case it didn't respect the chdir
            if not company_dir.exists():
                # Try project root
                alt_company_dir = Path("./sec-edgar-filings") / ticker / filing_type
                if alt_company_dir.exists():
                    print(f"   ℹ️  Found files in project root: {alt_company_dir}")
                    company_dir = alt_company_dir
                else:
                    print(f"   ❌ Directory not found: {company_dir}")
                    print(f"   ❌ Also checked: {alt_company_dir}")
                    return []

            # Get all filing directories
            filing_dirs = sorted([d for d in company_dir.iterdir() if d.is_dir()],
                               key=lambda x: x.name, reverse=True)

            print(f"   Found {len(filing_dirs)} filing directories")

            filings = []
            for filing_dir in filing_dirs[:num_filings]:
                # Version 5.x might save as different filename
                # Try common names
                for filename in ["full-submission.txt", "primary-document.html", "filing-details.xml"]:
                    file_path = filing_dir / filename
                    if file_path.exists():
                        print(f"   ✅ Found file: {file_path.name} in {filing_dir.name}")
                        filings.append(file_path)
                        break
                else:
                    # List what's actually in the directory
                    files_in_dir = list(filing_dir.glob("*"))
                    if files_in_dir:
                        print(f"   📁 Files in {filing_dir.name}: {[f.name for f in files_in_dir[:5]]}")
                        # Just use the first file we find
                        filings.append(files_in_dir[0])

            return filings

        except Exception as e:
            print(f"❌ Error fetching {filing_type} for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def extract_financial_metrics(self, filing_path: Path) -> Dict:
        """Extract key financial metrics from filing using Claude"""
        try:
            content = filing_path.read_text(encoding='utf-8', errors='ignore')

            # Truncate to manageable size to avoid rate limits
            # First 30k chars usually contain the key financial data
            content = content[:30000]

            extraction_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a financial analyst extracting key metrics from SEC filings.
Extract the following information in JSON format:

**Income Statement:**
- filing_period: The period covered (e.g., "2024-Q1", "2023")
- filing_date: Date of filing (YYYY-MM-DD)
- revenue: Total revenue/sales (in millions, numeric only)
- operating_income: Operating income (in millions, numeric only)
- net_income: Net income (in millions, numeric only)

**Balance Sheet:**
- total_assets: Total assets (in millions, numeric only)
- total_liabilities: Total liabilities (in millions, numeric only)
- stockholders_equity: Stockholders equity (in millions, numeric only)
- cash_and_equivalents: Cash and cash equivalents (in millions, numeric only)

**Cash Flow Statement:**
- operating_cash_flow: Cash from operating activities (in millions, numeric only)
- investing_cash_flow: Cash from investing activities (in millions, numeric only)
- financing_cash_flow: Cash from financing activities (in millions, numeric only)

**Additional:**
- key_risks: List of top 3-5 risk factors mentioned
- business_summary: 2-3 sentence summary of the business

Return valid JSON only. For all numeric values, provide just the number (no $ or M). If a value is not found, use null."""),
                ("user", "Extract financial metrics from this SEC filing:\n\n{filing_content}")
            ])

            chain = extraction_prompt | self.llm
            response = chain.invoke({"filing_content": content})

            # Parse the response
            import json
            # Extract JSON from markdown code blocks if present
            response_text = response.content
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            metrics = json.loads(response_text)
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

    def get_company_financials(self, ticker: str, filing_types: List[str] = None) -> Dict:
        """Get comprehensive financial data for a company"""
        if filing_types is None:
            filing_types = ["10-K", "10-Q"]

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
                metrics = self.extract_financial_metrics(filing_path)
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
            response_text = response.content
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)

        except Exception as e:
            print(f"Error analyzing financial health: {e}")
            return {
                "error": str(e),
                "overall_rating": "unknown"
            }
