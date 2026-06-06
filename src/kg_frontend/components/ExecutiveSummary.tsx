"use client";

interface Props {
  summary: string;
  companyName: string;
  temporalSummary?: {
    total_items: number;
    fresh_items: number;
    recent_items: number;
    aged_items: number;
    stale_items: number;
    avg_relevance_score: number;
  };
}

export default function ExecutiveSummary({ summary, companyName, temporalSummary }: Props) {
  const freshness = temporalSummary
    ? ((temporalSummary.fresh_items + temporalSummary.recent_items) / temporalSummary.total_items) * 100
    : null;

  // Ensure summary is a string
  const summaryText = typeof summary === 'string'
    ? summary
    : 'Research completed successfully. Comprehensive data has been gathered across all dimensions. Review the Financial Metrics, Industry Analysis, and Knowledge Graph tabs for detailed insights.';

  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      <div className="bg-white rounded-lg p-8 border-2 border-gray-200 shadow-md">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-[#D71E28] border-b-4 border-[#D71E28] pb-3 mb-2">{companyName}</h2>
          <p className="text-sm text-[#666666] uppercase tracking-wide font-bold">Executive Summary</p>
        </div>

        <div className="prose max-w-none">
          <p className="text-base text-[#333333] leading-relaxed whitespace-pre-line">
            {summaryText}
          </p>
        </div>

        {/* Data Freshness Indicator */}
        {temporalSummary && (
          <div className="mt-6 pt-6 border-t-2 border-gray-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-bold text-[#333333] uppercase tracking-wide">Data Freshness</span>
              <span className={`text-sm font-bold px-3 py-1 rounded ${
                freshness && freshness >= 70 ? 'bg-green-100 text-green-700' :
                freshness && freshness >= 40 ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              }`}>
                {freshness?.toFixed(0)}% Current
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
              <DataAge
                count={temporalSummary.fresh_items}
                label="Fresh"
                sublabel="< 30 days"
                color="bg-green-500"
              />
              <DataAge
                count={temporalSummary.recent_items}
                label="Recent"
                sublabel="30-90 days"
                color="bg-blue-500"
              />
              <DataAge
                count={temporalSummary.aged_items}
                label="Aged"
                sublabel="90-365 days"
                color="bg-yellow-500"
              />
              <DataAge
                count={temporalSummary.stale_items}
                label="Stale"
                sublabel="> 365 days"
                color="bg-red-500"
              />
            </div>

            <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
              <span>Average Relevance Score:</span>
              <span className="font-semibold text-white">
                {(temporalSummary.avg_relevance_score * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Meeting Prep Checklist */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <h3 className="text-lg font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
          Meeting Preparation Checklist
        </h3>
        <ul className="space-y-3">
          <ChecklistItem completed text="Financial health assessment reviewed" />
          <ChecklistItem completed text="Recent news and sentiment analyzed" />
          <ChecklistItem completed text="Industry position and peer comparison completed" />
          <ChecklistItem completed text="Product opportunities identified" />
          <ChecklistItem text="Prepare talking points based on insights" />
          <ChecklistItem text="Schedule follow-up on identified opportunities" />
        </ul>
      </div>
    </div>
  );
}

function DataAge({
  count,
  label,
  sublabel,
  color
}: {
  count: number;
  label: string;
  sublabel: string;
  color: string;
}) {
  const bgColor = color === 'bg-green-500' ? 'bg-green-50 border-green-500' :
                  color === 'bg-blue-500' ? 'bg-blue-50 border-blue-500' :
                  color === 'bg-yellow-500' ? 'bg-yellow-50 border-yellow-500' :
                  'bg-red-50 border-red-500';

  const textColor = color === 'bg-green-500' ? 'text-green-700' :
                    color === 'bg-blue-500' ? 'text-blue-700' :
                    color === 'bg-yellow-500' ? 'text-yellow-700' :
                    'text-red-700';

  return (
    <div className={`${bgColor} rounded p-3 border-l-4`}>
      <p className={`text-2xl font-bold ${textColor}`}>{count}</p>
      <p className={`text-xs font-bold ${textColor} uppercase tracking-wide`}>{label}</p>
      <p className="text-xs text-[#666666]">{sublabel}</p>
    </div>
  );
}

function ChecklistItem({ text, completed }: { text: string; completed?: boolean }) {
  return (
    <li className="flex items-center gap-3 p-2">
      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
        completed
          ? 'bg-green-600 border-green-600'
          : 'border-gray-400'
      }`}>
        {completed && (
          <div className="w-2 h-2 bg-white rounded-sm" />
        )}
      </div>
      <span className={`text-sm ${completed ? 'text-[#666666] line-through' : 'text-[#333333] font-semibold'}`}>
        {text}
      </span>
    </li>
  );
}
