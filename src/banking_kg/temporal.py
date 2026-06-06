from datetime import datetime, timedelta
from typing import Dict, List, Any
import json


class TemporalDimension:
    """Manages temporal aspects: recency, relevance scoring, and data pruning"""

    def __init__(self):
        # Define relevance windows (in days)
        self.relevance_windows = {
            "news": 90,  # News older than 90 days is less relevant
            "financial": 365,  # Annual financial data
            "quarterly_financial": 120,  # Quarterly data
            "products": 730,  # Product data valid for ~2 years
            "industry_trends": 180,  # Industry trends refresh every 6 months
            "company_info": 365  # Company info yearly refresh
        }

        # Decay factors for scoring
        self.decay_rates = {
            "news": 0.05,  # News decays quickly
            "financial": 0.01,  # Financial data decays slowly
            "products": 0.02,
            "industry": 0.03
        }

    def calculate_recency_score(self, item_date: str, data_type: str = "general") -> float:
        """
        Calculate recency score (0-1) based on how recent the data is.
        1.0 = brand new, 0.0 = beyond relevance window
        """
        try:
            if isinstance(item_date, str):
                # Try to parse ISO format
                if 'T' in item_date:
                    date_obj = datetime.fromisoformat(item_date.replace('Z', '+00:00'))
                else:
                    date_obj = datetime.strptime(item_date, '%Y-%m-%d')
            else:
                date_obj = item_date

            days_old = (datetime.now() - date_obj).days

            # Get relevance window for this data type
            window = self.relevance_windows.get(data_type, 180)

            if days_old < 0:
                return 1.0  # Future date, treat as current

            if days_old > window:
                # Apply exponential decay beyond window
                decay_rate = self.decay_rates.get(data_type, 0.03)
                extra_days = days_old - window
                score = max(0.0, 0.3 * (1 - decay_rate) ** extra_days)
                return score

            # Linear decay within window
            score = 1.0 - (days_old / window) * 0.7  # Decays to 0.3 at window edge
            return max(0.0, min(1.0, score))

        except Exception as e:
            print(f"Error calculating recency score: {e}")
            return 0.5  # Default to medium relevance

    def calculate_relevance_score(self, item: Dict, context: Dict = None) -> float:
        """
        Calculate overall relevance score combining recency and content relevance.
        Returns score from 0-1.
        """
        recency_score = 0.5

        # Extract date from item
        date_field = None
        for field in ['date', 'timestamp', 'period', 'scraped_at', 'discovered_at', 'extracted_at']:
            if field in item:
                date_field = item[field]
                break

        if date_field:
            data_type = item.get('type', 'general')
            recency_score = self.calculate_recency_score(date_field, data_type)

        # Content relevance factors
        content_score = 0.5

        # Boost for high-priority content
        if item.get('severity') == 'high':
            content_score += 0.3
        elif item.get('severity') == 'medium':
            content_score += 0.15

        if item.get('sentiment') == 'negative':
            content_score += 0.2  # Negative news more relevant for risk assessment

        if item.get('revenue_impact') == 'high':
            content_score += 0.2

        if item.get('filing_type') in ['10-K', '10-Q']:
            content_score += 0.3  # Official filings are highly relevant

        # Normalize content score
        content_score = min(1.0, content_score)

        # Combined score (weighted average)
        # Recency: 60%, Content: 40%
        total_score = (recency_score * 0.6) + (content_score * 0.4)

        return round(total_score, 3)

    def score_all_items(self, graph_data: Dict) -> Dict:
        """Add relevance scores to all items in the graph"""

        scored_data = graph_data.copy()

        # Score financials
        if "financials" in scored_data:
            for item in scored_data["financials"]:
                item["relevance_score"] = self.calculate_relevance_score(
                    item,
                    context={"data_type": "financial"}
                )

        # Score news
        if "news" in scored_data:
            for item in scored_data["news"]:
                item["relevance_score"] = self.calculate_relevance_score(
                    item,
                    context={"data_type": "news"}
                )

        # Score products
        if "products" in scored_data:
            for item in scored_data["products"]:
                item["relevance_score"] = self.calculate_relevance_score(
                    item,
                    context={"data_type": "products"}
                )

        return scored_data

    def prune_low_relevance(self, graph_data: Dict, threshold: float = 0.3) -> Dict:
        """Remove items below relevance threshold"""

        pruned_data = graph_data.copy()

        # Prune financials
        if "financials" in pruned_data:
            pruned_data["financials"] = [
                item for item in pruned_data["financials"]
                if item.get("relevance_score", 1.0) >= threshold
            ]

        # Prune news
        if "news" in pruned_data:
            pruned_data["news"] = [
                item for item in pruned_data["news"]
                if item.get("relevance_score", 1.0) >= threshold
            ]

        # Products have longer relevance, use lower threshold
        if "products" in pruned_data:
            product_threshold = threshold * 0.7
            pruned_data["products"] = [
                item for item in pruned_data["products"]
                if item.get("relevance_score", 1.0) >= product_threshold
            ]

        return pruned_data

    def get_temporal_summary(self, graph_data: Dict) -> Dict:
        """Get summary of temporal aspects of the data"""

        summary = {
            "total_items": 0,
            "fresh_items": 0,  # < 30 days
            "recent_items": 0,  # < 90 days
            "aged_items": 0,   # > 90 days
            "stale_items": 0,  # > 365 days
            "avg_relevance_score": 0.0,
            "oldest_item_age_days": 0,
            "newest_item_age_days": 0
        }

        all_items = []
        for key in ["financials", "news", "products"]:
            if key in graph_data:
                all_items.extend(graph_data[key])

        if not all_items:
            return summary

        summary["total_items"] = len(all_items)

        ages = []
        scores = []

        for item in all_items:
            score = item.get("relevance_score", 0.5)
            scores.append(score)

            # Calculate age
            date_field = None
            for field in ['date', 'timestamp', 'period', 'scraped_at', 'discovered_at', 'extracted_at']:
                if field in item:
                    date_field = item[field]
                    break

            if date_field:
                try:
                    if isinstance(date_field, str):
                        if 'T' in date_field:
                            date_obj = datetime.fromisoformat(date_field.replace('Z', '+00:00'))
                        else:
                            date_obj = datetime.strptime(date_field, '%Y-%m-%d')

                        age_days = (datetime.now() - date_obj).days
                        ages.append(age_days)

                        if age_days < 30:
                            summary["fresh_items"] += 1
                        elif age_days < 90:
                            summary["recent_items"] += 1
                        elif age_days < 365:
                            summary["aged_items"] += 1
                        else:
                            summary["stale_items"] += 1

                except Exception:
                    pass

        if scores:
            summary["avg_relevance_score"] = round(sum(scores) / len(scores), 3)

        if ages:
            summary["oldest_item_age_days"] = max(ages)
            summary["newest_item_age_days"] = min(ages)

        return summary

    def needs_refresh(self, item: Dict, data_type: str) -> bool:
        """Determine if an item needs to be refreshed"""

        window = self.relevance_windows.get(data_type, 180)

        date_field = None
        for field in ['date', 'timestamp', 'updated_at', 'scraped_at', 'extracted_at']:
            if field in item:
                date_field = item[field]
                break

        if not date_field:
            return True  # No date info, should refresh

        try:
            if isinstance(date_field, str):
                if 'T' in date_field:
                    date_obj = datetime.fromisoformat(date_field.replace('Z', '+00:00'))
                else:
                    date_obj = datetime.strptime(date_field, '%Y-%m-%d')

            age_days = (datetime.now() - date_obj).days
            return age_days > window

        except Exception:
            return True
