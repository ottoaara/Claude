import httpx
from bs4 import BeautifulSoup
from typing import Dict, Optional
from ..llm_factory import get_llm, robust_parse_json
from langchain_core.prompts import ChatPromptTemplate
import os
import json


class WebScraperAgent:
    """Agent for scraping company information from public websites"""

    def __init__(self):
        self.llm = get_llm(temperature=0)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    def fetch_website(self, url: str) -> Optional[str]:
        """Fetch website content"""
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_text_from_html(self, html: str) -> str:
        """Extract clean text from HTML"""
        soup = BeautifulSoup(html, 'lxml')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text[:50000]  # Limit size

    def extract_company_info(self, company_name: str, website_url: str = None) -> Dict:
        """Extract company information from website"""

        # Try to construct website URL if not provided
        if not website_url:
            company_slug = company_name.lower().replace(" ", "").replace(",", "").replace(".", "")
            website_url = f"https://www.{company_slug}.com"

        html = self.fetch_website(website_url)
        if not html:
            # Try alternative URLs
            alt_urls = [
                f"https://{company_name.lower().replace(' ', '')}.com",
                f"https://www.{company_name.lower().replace(' ', '-')}.com"
            ]
            for alt_url in alt_urls:
                html = self.fetch_website(alt_url)
                if html:
                    website_url = alt_url
                    break

        if not html:
            return {
                "error": f"Could not fetch website for {company_name}",
                "attempted_url": website_url
            }

        text_content = self.extract_text_from_html(html)

        # Use Claude to extract structured information
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are extracting company information from a website.
Extract the following in JSON format:
- company_name: Official company name
- description: 2-3 sentence description of what the company does
- industry: Primary industry
- headquarters: Location of headquarters
- founded: Year founded (if available)
- size: Employee count or size description
- products_services: List of main products/services mentioned
- key_facts: List of 3-5 notable facts about the company

Return valid JSON only."""),
            ("user", "Extract company information for {company_name} from this website content:\n\n{content}")
        ])

        try:
            chain = extraction_prompt | self.llm
            response = chain.invoke({
                "company_name": company_name,
                "content": text_content
            })

            response_text = response.content
            info = robust_parse_json(response_text, {})
            if not isinstance(info, dict):
                info = {}
            info["source_url"] = website_url
            info["scraped_at"] = __import__('datetime').datetime.now().isoformat()

            return info

        except Exception as e:
            print(f"Error extracting company info: {e}")
            return {
                "error": str(e),
                "source_url": website_url,
                "raw_text_preview": text_content[:500]
            }

    def find_about_page(self, base_url: str) -> Optional[str]:
        """Try to find and scrape the about page"""
        about_paths = ["/about", "/about-us", "/company", "/who-we-are", "/our-company"]

        for path in about_paths:
            url = f"{base_url.rstrip('/')}{path}"
            html = self.fetch_website(url)
            if html and len(html) > 1000:  # Has substantial content
                return self.extract_text_from_html(html)

        return None

    def get_company_overview(self, company_name: str, website_url: str = None) -> Dict:
        """Get comprehensive company overview from web sources"""

        # Get main website info
        main_info = self.extract_company_info(company_name, website_url)

        if "error" not in main_info and "source_url" in main_info:
            # Try to get about page for more details
            about_text = self.find_about_page(main_info["source_url"])

            if about_text:
                # Enhance description with about page content
                enhance_prompt = ChatPromptTemplate.from_messages([
                    ("system", """Based on the about page content, enhance the company description
with additional relevant details. Keep it concise (3-4 sentences).
Return only the enhanced description text, no JSON."""),
                    ("user", "Current description: {description}\n\nAbout page content:\n{about_content}")
                ])

                try:
                    chain = enhance_prompt | self.llm
                    response = chain.invoke({
                        "description": main_info.get("description", ""),
                        "about_content": about_text[:5000]
                    })
                    main_info["enhanced_description"] = response.content
                except Exception as e:
                    print(f"Error enhancing description: {e}")

        return main_info
