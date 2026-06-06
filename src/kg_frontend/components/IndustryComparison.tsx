"use client";

interface IndustryData {
  naics_code?: string;
  sector?: string;
  description?: string;
  peer_companies?: any[];
  naics_classification?: {
    naics_code?: string;
    naics_sector?: string;
    naics_sector_name?: string;
    industry_subsector?: string;
    confidence?: string;
    reasoning?: string;
  };
  industry_trends?: {
    growth_outlook?: string;
    key_trends?: string[];
    opportunities?: string[];
    challenges?: string[];
    risk_factors?: string[];
  };
}

interface CompanyMetrics {
  revenue?: number;
  net_income?: number;
  assets?: number;
  margin?: number;
}

interface Props {
  industry: IndustryData;
  companyMetrics?: CompanyMetrics;
  industryAverages?: CompanyMetrics;
}

function formatCurrency(value: number | undefined): string {
  if (value === undefined || value === null) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1
  }).format(value);
}

function formatPercent(value: number | undefined): string {
  if (value === undefined || value === null) return 'N/A';
  return `${value.toFixed(1)}%`;
}

function getPerformanceLevel(companyValue: number | undefined, industryAvg: number | undefined): {
  label: string;
  color: string;
} {
  if (!companyValue || !industryAvg) return { label: 'N/A', color: 'text-gray-600' };

  const ratio = companyValue / industryAvg;

  if (ratio >= 1.2) return { label: 'Above Average', color: 'text-green-700' };
  if (ratio >= 0.8) return { label: 'Average', color: 'text-blue-700' };
  return { label: 'Below Average', color: 'text-red-700' };
}

export default function IndustryComparison({ industry, companyMetrics, industryAverages }: Props) {
  console.log('IndustryComparison received:', { industry, companyMetrics, industryAverages });

  if (!industry || Object.keys(industry).length === 0) {
    return (
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200">
        <p className="text-[#666666] text-center font-semibold">No industry data available</p>
        <p className="text-xs text-[#666666] text-center mt-2">
          Industry analysis will appear after research completes.
        </p>
      </div>
    );
  }

  // Extract data from nested structure
  const naicsCode = industry.naics_classification?.naics_code || industry.naics_code || 'N/A';
  const sector = industry.naics_classification?.naics_sector_name || industry.sector || 'N/A';
  const subsector = industry.naics_classification?.industry_subsector;
  const reasoning = industry.naics_classification?.reasoning;

  return (
    <div className="space-y-6">
      {/* Industry Overview */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <h3 className="text-2xl font-bold text-[#D71E28] mb-4 border-b-4 border-[#D71E28] pb-3 uppercase tracking-wide">
          Industry Analysis
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <p className="text-xs text-[#666666] font-bold uppercase tracking-wide mb-2">NAICS Classification</p>
            <p className="text-lg font-bold text-[#333333]">
              {naicsCode} - {sector}
            </p>
            {subsector && (
              <p className="text-sm font-semibold text-[#D71E28] mt-1">{subsector}</p>
            )}
            {reasoning && (
              <p className="text-sm text-[#666666] mt-2">{reasoning}</p>
            )}
          </div>

          {industry.peer_companies && industry.peer_companies.length > 0 && (
            <div>
              <p className="text-xs text-[#666666] font-bold uppercase tracking-wide mb-2">Peer Companies</p>
              <div className="flex flex-wrap gap-2">
                {industry.peer_companies.slice(0, 5).map((peer: any, idx: number) => {
                  const peerName = typeof peer === 'string' ? peer : peer.company_name || peer.name || String(peer);
                  return (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-gray-100 border border-gray-300 rounded text-sm text-[#333333] font-semibold"
                    >
                      {peerName}
                    </span>
                  );
                })}
                {industry.peer_companies.length > 5 && (
                  <span className="px-3 py-1 text-sm text-[#666666] font-semibold">
                    +{industry.peer_companies.length - 5} more
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Comparison Metrics */}
        {companyMetrics && industryAverages && (
          <div className="space-y-4 mt-6 pt-6 border-t-2 border-gray-200">
            <h4 className="text-lg font-bold text-[#333333] mb-3 uppercase tracking-wide">
              Performance vs. Industry Average
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ComparisonCard
                label="Revenue"
                companyValue={companyMetrics.revenue}
                industryValue={industryAverages.revenue}
                formatter={formatCurrency}
              />
              <ComparisonCard
                label="Net Income"
                companyValue={companyMetrics.net_income}
                industryValue={industryAverages.net_income}
                formatter={formatCurrency}
              />
              <ComparisonCard
                label="Total Assets"
                companyValue={companyMetrics.assets}
                industryValue={industryAverages.assets}
                formatter={formatCurrency}
              />
              <ComparisonCard
                label="Profit Margin"
                companyValue={companyMetrics.margin}
                industryValue={industryAverages.margin}
                formatter={formatPercent}
              />
            </div>
          </div>
        )}
      </div>

      {/* Industry Trends */}
      {industry.industry_trends && (
        <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
          <h4 className="text-lg font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
            Industry Trends & Outlook
          </h4>

          {industry.industry_trends.growth_outlook && (
            <div className="mb-4">
              <p className="text-xs text-[#666666] font-bold uppercase tracking-wide mb-1">Growth Outlook</p>
              <p className="text-base text-[#333333] font-semibold capitalize">{industry.industry_trends.growth_outlook}</p>
            </div>
          )}

          {industry.industry_trends.key_trends && industry.industry_trends.key_trends.length > 0 && (
            <div className="mb-4">
              <p className="text-xs text-[#666666] font-bold uppercase tracking-wide mb-2">Key Trends</p>
              <ul className="space-y-2">
                {industry.industry_trends.key_trends.map((trend, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-[#333333]">
                    <span className="text-[#D71E28] font-bold">•</span>
                    <span>{trend}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {industry.industry_trends.opportunities && industry.industry_trends.opportunities.length > 0 && (
              <div className="p-3 bg-green-50 border border-green-200 rounded">
                <p className="text-xs text-green-800 font-bold uppercase tracking-wide mb-2">Opportunities</p>
                <ul className="space-y-1">
                  {industry.industry_trends.opportunities.map((opp, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-green-900">
                      <span className="text-green-600 font-bold">+</span>
                      <span>{opp}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {industry.industry_trends.challenges && industry.industry_trends.challenges.length > 0 && (
              <div className="p-3 bg-red-50 border border-red-200 rounded">
                <p className="text-xs text-red-800 font-bold uppercase tracking-wide mb-2">Challenges</p>
                <ul className="space-y-1">
                  {industry.industry_trends.challenges.map((challenge, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-red-900">
                      <span className="text-red-600 font-bold">−</span>
                      <span>{challenge}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Key Insights */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <h4 className="text-lg font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
          Key Insights
        </h4>
        <ul className="space-y-3 text-sm text-[#333333]">
          <li className="flex items-start gap-3 p-2 bg-gray-50 rounded">
            <span className="font-bold text-[#D71E28]">•</span>
            <span>
              Company operates in <strong className="text-[#D71E28]">{sector}</strong> sector
              {industry.peer_companies && industry.peer_companies.length > 0 && (
                <> with <strong className="text-[#D71E28]">{industry.peer_companies.length}</strong> identified peers</>
              )}
            </span>
          </li>
          {companyMetrics && industryAverages && (
            <>
              <li className="flex items-start gap-3 p-2 bg-gray-50 rounded">
                <span className="font-bold text-[#D71E28]">•</span>
                <span>
                  Revenue performance: {' '}
                  <strong className={getPerformanceLevel(companyMetrics.revenue, industryAverages.revenue).color}>
                    {getPerformanceLevel(companyMetrics.revenue, industryAverages.revenue).label}
                  </strong>
                  {' '}compared to sector average
                </span>
              </li>
              <li className="flex items-start gap-3 p-2 bg-gray-50 rounded">
                <span className="font-bold text-[#D71E28]">•</span>
                <span>
                  Profitability: {' '}
                  <strong className={getPerformanceLevel(companyMetrics.margin, industryAverages.margin).color}>
                    {getPerformanceLevel(companyMetrics.margin, industryAverages.margin).label}
                  </strong>
                  {' '}profit margins relative to peers
                </span>
              </li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
}

function ComparisonCard({
  label,
  companyValue,
  industryValue,
  formatter
}: {
  label: string;
  companyValue: number | undefined;
  industryValue: number | undefined;
  formatter: (val: number | undefined) => string;
}) {
  const performance = getPerformanceLevel(companyValue, industryValue);
  const percentDiff = companyValue && industryValue
    ? ((companyValue - industryValue) / industryValue) * 100
    : undefined;

  return (
    <div className="bg-gray-50 rounded p-4 border border-gray-300">
      <p className="text-xs text-[#666666] font-bold uppercase tracking-wide mb-3">{label}</p>

      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <p className="text-xs text-[#666666] font-bold mb-1 uppercase tracking-wide">Company</p>
          <p className="text-lg font-bold text-[#D71E28]">{formatter(companyValue)}</p>
        </div>
        <div>
          <p className="text-xs text-[#666666] font-bold mb-1 uppercase tracking-wide">Industry Avg</p>
          <p className="text-lg font-bold text-[#333333]">{formatter(industryValue)}</p>
        </div>
      </div>

      <div className="flex items-center justify-between pt-3 border-t border-gray-300">
        <span className={`text-sm font-bold ${performance.color}`}>
          {performance.label}
        </span>
        {percentDiff !== undefined && (
          <span className={`text-xs font-bold ${percentDiff >= 0 ? 'text-green-700' : 'text-red-700'}`}>
            {percentDiff >= 0 ? '+' : ''}{percentDiff.toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}
