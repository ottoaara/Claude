"use client";

import { useEffect, useState } from "react";
import { api, APIError } from "../lib/api";
import WFCommonality from "./WFCommonality";
import { ScoreTooltip } from "./ScoreTooltip";

interface Props {
  companyName: string;
}

export default function InsightsOverview({ companyName }: Props) {
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        setLoading(true);
        const data = await api.getCompanyGraph(companyName);
        setGraphData(data);
      } catch (err) {
        if (err instanceof APIError) {
          setError(err.message);
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchGraphData();
  }, [companyName]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg p-12 text-center border-2 border-gray-200">
        <div className="inline-block w-12 h-12 border-4 border-[#D71E28] border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-[#666666] font-semibold">Loading insights...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-2 border-red-300 rounded p-8 text-red-700">
        <p className="font-bold mb-2 uppercase tracking-wide text-sm">Error Loading Data:</p>
        <p>{error}</p>
      </div>
    );
  }

  if (!graphData) {
    return (
      <div className="bg-white rounded-lg p-8 text-center border-2 border-gray-200">
        <p className="text-[#666666]">No data available</p>
      </div>
    );
  }

  // Helper to convert Neo4j dates to strings
  const formatDate = (dateObj: any): string => {
    if (!dateObj) return 'N/A';
    if (typeof dateObj === 'string') return dateObj;

    // Handle Neo4j date objects
    if (dateObj._Date__year && dateObj._Date__month && dateObj._Date__day) {
      return `${dateObj._Date__year}-${String(dateObj._Date__month).padStart(2, '0')}-${String(dateObj._Date__day).padStart(2, '0')}`;
    }

    // Handle standard Date objects
    if (dateObj instanceof Date) {
      return dateObj.toISOString().split('T')[0];
    }

    return String(dateObj);
  };

  // Extract insights from graph data
  const company = graphData.company || {};
  const financials = (graphData.financials || []).map((f: any) => ({
    ...f,
    filing_date: formatDate(f.filing_date),
    date: formatDate(f.date)
  }));
  const news = (graphData.news || []).map((n: any) => ({
    ...n,
    date: formatDate(n.date)
  }));
  const products = graphData.products || [];
  const industry = graphData.industry || {};
  const peers = graphData.peers || [];

  return (
    <div className="space-y-6">
      {/* Company Overview */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <h3 className="text-xl font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
          Company Overview
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {company.ticker && (
            <InfoCard label="Stock Ticker" value={company.ticker} />
          )}
          {company.sector && (
            <InfoCard label="Sector" value={company.sector} />
          )}
          {company.website && (
            <InfoCard label="Website" value={company.website} link />
          )}
        </div>
        {company.description && (
          <div className="mt-4 p-4 bg-gray-50 rounded border border-gray-200">
            <p className="text-sm text-[#333333]">{company.description}</p>
          </div>
        )}
      </div>

      {/* WF × Company Commonality */}
      <WFCommonality companyName={companyName} graphData={graphData} />

      {/* Financial Health Snapshot */}
      {financials.length > 0 && (
        <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
          <h3 className="text-xl font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
            Financial Health Snapshot
          </h3>
          <div className="space-y-3">
            {financials.slice(0, 3).map((filing: any, idx: number) => (
              <div key={idx} className="p-4 bg-gray-50 rounded border-l-4 border-[#D71E28]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold text-[#333333] uppercase tracking-wide">
                    {filing.filing_type || 'Filing'} - {filing.period || 'Unknown'}
                  </span>
                  <span className="text-xs text-[#666666]">
                    Filed: {String(filing.filing_date || 'N/A')}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  {filing.revenue && (
                    <div>
                      <p className="text-xs text-[#666666] font-bold uppercase">Revenue</p>
                      <p className="text-base font-bold text-[#D71E28]">
                        ${Number(filing.revenue).toFixed(1)}M
                      </p>
                    </div>
                  )}
                  {filing.net_income && (
                    <div>
                      <p className="text-xs text-[#666666] font-bold uppercase">Net Income</p>
                      <p className="text-base font-bold text-[#333333]">
                        ${Number(filing.net_income).toFixed(1)}M
                      </p>
                    </div>
                  )}
                  {filing.total_assets && (
                    <div>
                      <p className="text-xs text-[#666666] font-bold uppercase">Total Assets</p>
                      <p className="text-base font-bold text-[#333333]">
                        ${Number(filing.total_assets).toFixed(1)}M
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent News & Sentiment */}
      {news.length > 0 && (
        <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
          <h3 className="text-xl font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
            Recent News & Sentiment
          </h3>
          <div className="space-y-3">
            {news.slice(0, 5).map((item: any, idx: number) => (
              <div key={idx} className="p-4 bg-gray-50 rounded border-l-4 border-gray-300">
                <div className="flex items-start justify-between mb-2">
                  <h4 className="text-sm font-bold text-[#333333] flex-1">{item.title}</h4>
                  <SentimentBadge sentiment={item.sentiment} />
                </div>
                {item.summary && (
                  <p className="text-xs text-[#666666] mb-2">{item.summary}</p>
                )}
                <div className="flex items-center justify-between text-xs text-[#666666]">
                  <span>{String(item.date || 'N/A')}</span>
                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#D71E28] hover:underline font-semibold"
                    >
                      Read More
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Industry Position */}
      {(industry.sector || peers.length > 0) && (
        <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
          <h3 className="text-xl font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
            Industry Position
          </h3>

          {industry.sector && (
            <div className="mb-4 p-4 bg-gray-50 rounded">
              <p className="text-xs text-[#666666] font-bold uppercase tracking-wide mb-1">
                Industry Classification
              </p>
              <p className="text-lg font-bold text-[#333333]">
                {industry.naics_code} - {industry.sector}
              </p>
              {industry.description && (
                <p className="text-sm text-[#666666] mt-2">{industry.description}</p>
              )}
            </div>
          )}

          {peers.length > 0 && (
            <div>
              <p className="text-xs text-[#666666] font-bold uppercase tracking-wide mb-3">
                Key Competitors ({peers.length})
              </p>
              <div className="flex flex-wrap gap-2">
                {peers.slice(0, 8).map((peer: any, idx: number) => (
                  <span
                    key={idx}
                    className="px-3 py-2 bg-gray-100 border border-gray-300 rounded text-sm font-semibold text-[#333333]"
                  >
                    {peer.name || peer}
                  </span>
                ))}
                {peers.length > 8 && (
                  <span className="px-3 py-2 text-sm text-[#666666] font-semibold">
                    +{peers.length - 8} more
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Products & Services */}
      {products.length > 0 && (
        <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
          <h3 className="text-xl font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
            Products & Services
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {products.slice(0, 6).map((product: any, idx: number) => (
              <div key={idx} className="p-4 bg-gray-50 rounded border border-gray-200">
                <h4 className="text-sm font-bold text-[#333333] mb-2">{product.name}</h4>
                {product.category && (
                  <p className="text-xs text-[#666666] mb-2 uppercase tracking-wide font-bold">
                    {product.category}
                  </p>
                )}
                {product.description && (
                  <p className="text-xs text-[#666666]">{product.description}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Relationships Summary */}
      <div className="bg-gradient-to-r from-[#D71E28] to-[#A91B23] rounded-lg p-6 text-white shadow-md">
        <h3 className="text-xl font-bold mb-4 uppercase tracking-wide">
          Data Summary
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard label="Financial Filings" count={financials.length} />
          <SummaryCard label="News Articles" count={news.length} />
          <SummaryCard label="Products" count={products.length} />
          <SummaryCard label="Competitors" count={peers.length} />
        </div>
      </div>
    </div>
  );
}

function InfoCard({ label, value, link }: { label: string; value: string; link?: boolean }) {
  return (
    <div className="p-3 bg-gray-50 rounded border border-gray-200">
      <p className="text-xs text-[#666666] font-bold uppercase tracking-wide mb-1">{label}</p>
      {link ? (
        <a
          href={value}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-semibold text-[#D71E28] hover:underline"
        >
          {value}
        </a>
      ) : (
        <p className="text-sm font-bold text-[#333333]">{value}</p>
      )}
    </div>
  );
}

const SENTIMENT_EXPLAIN: Record<string, string> = {
  positive: "The news pipeline scored this article as favorable — revenue beats, product launches, partnership announcements, or positive analyst coverage. Less likely to signal an immediate banking need.",
  negative: "The news pipeline flagged adverse language: earnings misses, regulatory actions, litigation, leadership departures, layoffs, or debt concerns. Negative sentiment raises deal-trigger scores and urgency ratings.",
  neutral:  "The article is informational or mixed — no strong positive or negative signal detected. Still worth reviewing for context.",
};

function SentimentBadge({ sentiment }: { sentiment: string }) {
  const colors = {
    positive: 'bg-green-100 text-green-700',
    negative: 'bg-red-100 text-red-700',
    neutral: 'bg-gray-100 text-gray-700'
  };

  const color = colors[sentiment as keyof typeof colors] || colors.neutral;
  const explain = SENTIMENT_EXPLAIN[sentiment] ?? `Sentiment classification: ${sentiment}.`;

  return (
    <ScoreTooltip
      title={`${sentiment.charAt(0).toUpperCase() + sentiment.slice(1)} Sentiment`}
      body={explain}
      width="w-80"
      position="bottom"
    >
      <span className={`px-2 py-1 rounded text-xs font-bold uppercase tracking-wide cursor-help ${color}`}>
        {sentiment}
      </span>
    </ScoreTooltip>
  );
}

function SummaryCard({ label, count }: { label: string; count: number }) {
  return (
    <div className="text-center">
      <p className="text-3xl font-bold mb-1">{count}</p>
      <p className="text-xs uppercase tracking-wide opacity-90">{label}</p>
    </div>
  );
}
