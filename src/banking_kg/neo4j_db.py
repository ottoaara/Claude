from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional
import os
from datetime import datetime


class BankingKnowledgeGraph:
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def init_schema(self):
        """Initialize graph schema with constraints and indexes"""
        with self.driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT company_name IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
                "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT news_id IF NOT EXISTS FOR (n:News) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT financial_id IF NOT EXISTS FOR (f:Financial) REQUIRE f.id IS UNIQUE",
                "CREATE CONSTRAINT industry_code IF NOT EXISTS FOR (i:Industry) REQUIRE i.naics_code IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Constraint creation skipped: {e}")

            # Create indexes for performance
            indexes = [
                "CREATE INDEX company_ticker IF NOT EXISTS FOR (c:Company) ON (c.ticker)",
                "CREATE INDEX news_date IF NOT EXISTS FOR (n:News) ON (n.date)",
                "CREATE INDEX financial_period IF NOT EXISTS FOR (f:Financial) ON (f.period)",
                "CREATE INDEX company_sector IF NOT EXISTS FOR (c:Company) ON (c.sector)",
            ]

            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    print(f"Index creation skipped: {e}")

    def create_company(self, name: str, ticker: str = None, website: str = None,
                      sector: str = None, naics: str = None, **attributes) -> Dict:
        """Create a company node"""
        with self.driver.session() as session:
            result = session.run("""
                MERGE (c:Company {name: $name})
                SET c.ticker = $ticker,
                    c.website = $website,
                    c.sector = $sector,
                    c.naics = $naics,
                    c.updated_at = datetime(),
                    c += $attributes
                RETURN c
            """, name=name, ticker=ticker, website=website, sector=sector,
               naics=naics, attributes=attributes)
            return result.single()["c"]

    def add_financial_data(self, company_name: str, filing_type: str, period: str,
                          data: Dict[str, Any], source: str = "EDGAR") -> Dict:
        """Add financial filing data (10-K, 10-Q)"""
        import json
        with self.driver.session() as session:
            financial_id = f"{company_name}_{filing_type}_{period}"
            # Flatten data for Neo4j - store complex data as JSON string
            flat_data = {
                "revenue": data.get("revenue"),
                "net_income": data.get("net_income"),
                "total_assets": data.get("total_assets"),
                "cash": data.get("cash_and_equivalents"),
                "data_json": json.dumps(data)  # Store full data as JSON string
            }
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (f:Financial {id: $financial_id})
                SET f.filing_type = $filing_type,
                    f.period = $period,
                    f.source = $source,
                    f.revenue = $revenue,
                    f.net_income = $net_income,
                    f.total_assets = $total_assets,
                    f.cash = $cash,
                    f.data_json = $data_json,
                    f.timestamp = datetime()
                MERGE (c)-[:HAS_FILING]->(f)
                RETURN f
            """, company_name=company_name, financial_id=financial_id,
               filing_type=filing_type, period=period, source=source, **flat_data)
            rec = result.single()
            return dict(rec["f"]) if rec else None

    def add_news(self, company_name: str, title: str, summary: str, url: str,
                date: str, sentiment: str = "neutral", source: str = "web",
                severity: str = "low", event_types: list = None,
                is_material: bool = False, key_facts: list = None) -> Dict:
        """Add negative/relevant news with classifier fields"""
        import json
        with self.driver.session() as session:
            news_id = f"{company_name}_{hash(url)}"
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (n:News {id: $news_id})
                SET n.title = $title,
                    n.summary = $summary,
                    n.url = $url,
                    n.date = date($date),
                    n.sentiment = $sentiment,
                    n.severity = $severity,
                    n.event_types = $event_types,
                    n.is_material = $is_material,
                    n.key_facts = $key_facts,
                    n.source = $source,
                    n.timestamp = datetime()
                MERGE (c)-[:MENTIONED_IN]->(n)
                RETURN n
            """, company_name=company_name, news_id=news_id, title=title,
               summary=summary, url=url, date=date, sentiment=sentiment, source=source,
               severity=severity,
               event_types=json.dumps(event_types or []),
               is_material=is_material,
               key_facts=json.dumps(key_facts or []))
            rec = result.single()
            return dict(rec["n"]) if rec else None

    def save_news_analysis(self, company_name: str, analysis: Dict) -> None:
        """Store the aggregate news_analysis on the Company node"""
        import json
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company {name: $company_name})
                SET c.news_analysis = $analysis_json
            """, company_name=company_name, analysis_json=json.dumps(analysis))

    def add_product(self, company_name: str, product_name: str, category: str,
                   description: str, features: List[str] = None, **attributes) -> Dict:
        """Add product information"""
        with self.driver.session() as session:
            product_id = f"{company_name}_{product_name.replace(' ', '_')}"
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (p:Product {id: $product_id})
                SET p.name = $product_name,
                    p.category = $category,
                    p.description = $description,
                    p.features = $features,
                    p.timestamp = datetime(),
                    p += $attributes
                MERGE (c)-[:OFFERS]->(p)
                RETURN p
            """, company_name=company_name, product_id=product_id,
               product_name=product_name, category=category, description=description,
               features=features or [], attributes=attributes)
            rec = result.single()
            return dict(rec["p"]) if rec else None

    def link_to_industry(self, company_name: str, naics_code: str,
                        industry_name: str, sector: str) -> None:
        """Link company to industry/sector"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company {name: $company_name})
                MERGE (i:Industry {naics_code: $naics_code})
                SET i.name = $industry_name,
                    i.sector = $sector,
                    i.updated_at = datetime()
                MERGE (c)-[:BELONGS_TO]->(i)
            """, company_name=company_name, naics_code=naics_code,
               industry_name=industry_name, sector=sector)

    def add_peer_relationship(self, company_name: str, peer_name: str,
                             similarity_score: float = None) -> None:
        """Add peer/competitor relationship"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c1:Company {name: $company_name})
                MERGE (c2:Company {name: $peer_name})
                MERGE (c1)-[r:PEER_OF]-(c2)
                SET r.similarity_score = $similarity_score,
                    r.updated_at = datetime()
            """, company_name=company_name, peer_name=peer_name,
               similarity_score=similarity_score)

    def get_company_graph(self, company_name: str, max_depth: int = 2) -> Dict:
        """Get complete company graph with all dimensions"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                OPTIONAL MATCH (c)-[r1:HAS_FILING]->(f:Financial)
                OPTIONAL MATCH (c)-[r2:MENTIONED_IN]->(n:News)
                OPTIONAL MATCH (c)-[r3:OFFERS]->(p:Product)
                OPTIONAL MATCH (c)-[r4:BELONGS_TO]->(i:Industry)
                OPTIONAL MATCH (c)-[r5:PEER_OF]-(peer:Company)
                RETURN c,
                       collect(DISTINCT f) as financials,
                       collect(DISTINCT n) as news,
                       collect(DISTINCT p) as products,
                       collect(DISTINCT i) as industries,
                       collect(DISTINCT peer) as peers
            """, company_name=company_name)

            record = result.single()
            if not record:
                return None

            import json
            # Parse news items — deserialise JSON-stored list fields
            news_items = []
            for n in record["news"]:
                if not n:
                    continue
                item = dict(n)
                for field in ("event_types", "key_facts"):
                    raw = item.get(field)
                    if isinstance(raw, str):
                        try:
                            item[field] = json.loads(raw)
                        except Exception:
                            item[field] = []
                news_items.append(item)

            # Parse news_analysis stored on Company node
            company_data = dict(record["c"])
            news_analysis = None
            raw_analysis = company_data.pop("news_analysis", None)
            if raw_analysis:
                try:
                    news_analysis = json.loads(raw_analysis)
                except Exception:
                    pass

            return {
                "company": company_data,
                "financials": [dict(f) for f in record["financials"] if f],
                "news": news_items,
                "news_analysis": news_analysis,
                "products": [dict(p) for p in record["products"] if p],
                "industries": [dict(i) for i in record["industries"] if i],
                "peers": [dict(p) for p in record["peers"] if p]
            }

    def prune_old_data(self, company_name: str, days_threshold: int = 90) -> int:
        """Temporal dimension: Remove outdated news and data"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company {name: $company_name})-[:MENTIONED_IN]->(n:News)
                WHERE n.date < date() - duration({days: $days_threshold})
                DETACH DELETE n
                RETURN count(n) as deleted
            """, company_name=company_name, days_threshold=days_threshold)
            return result.single()["deleted"]

    def get_visualization_data(self, company_name: str) -> Dict[str, List]:
        """Get graph data formatted for visualization"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Company {name: $company_name})
                OPTIONAL MATCH (c)-[r]-(other)
                RETURN c, collect(DISTINCT r) as relationships, collect(DISTINCT other) as nodes
            """, company_name=company_name)

            record = result.single()
            if not record:
                return {"nodes": [], "edges": []}

            nodes = [{"id": company_name, "label": company_name, "type": "Company",
                     "data": dict(record["c"])}]
            edges = []

            for rel in record["relationships"]:
                if rel:
                    edges.append({
                        "from": rel.start_node["name"],
                        "to": rel.end_node["name"],
                        "type": rel.type,
                        "data": dict(rel)
                    })

            for node in record["nodes"]:
                if node:
                    node_labels = list(node.labels)
                    node_type = node_labels[0] if node_labels else "Unknown"
                    node_id = node.get("name") or node.get("id")
                    nodes.append({
                        "id": node_id,
                        "label": node_id,
                        "type": node_type,
                        "data": dict(node)
                    })

            return {"nodes": nodes, "edges": edges}

    def clear_company_data(self, company_name: str) -> None:
        """Clear all data for a company"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Company {name: $company_name})
                OPTIONAL MATCH (c)-[r]->(n)
                WHERE NOT n:Industry AND NOT n:Company
                DETACH DELETE n
                DELETE r
            """, company_name=company_name)
