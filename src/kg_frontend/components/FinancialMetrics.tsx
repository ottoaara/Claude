"use client";

interface FinancialData {
  period?: string;
  filing_type?: string;
  filing_date?: string;
  revenue?: number;
  net_income?: number;
  operating_income?: number;
  assets?: number;
  liabilities?: number;
  equity?: number;
  operating_cash_flow?: number;
  investing_cash_flow?: number;
  financing_cash_flow?: number;
}

interface Props {
  financials: FinancialData[];
}

function formatCurrency(value: number | undefined): string {
  if (value === undefined || value === null) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1
  }).format(value * 1_000_000); // Assuming values in millions
}

function formatPercent(value: number | undefined): string {
  if (value === undefined || value === null) return 'N/A';
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
}

export default function FinancialMetrics({ financials }: Props) {
  console.log('FinancialMetrics received:', financials);
  console.log('Type:', typeof financials, 'Is array:', Array.isArray(financials));

  if (!financials || !Array.isArray(financials) || financials.length === 0) {
    console.warn('No financial data - financials is:', financials);
    return (
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200">
        <p className="text-[#666666] text-center font-semibold">No financial data available</p>
        <p className="text-xs text-[#666666] text-center mt-2">
          Make sure to provide a valid stock ticker when researching the company.
        </p>
        <details className="mt-4 text-xs text-[#666666]">
          <summary className="cursor-pointer text-center">Debug Info</summary>
          <pre className="mt-2 p-2 bg-gray-100 rounded overflow-auto">
            {JSON.stringify(financials, null, 2)}
          </pre>
        </details>
      </div>
    );
  }

  const latest = financials[0];
  const previous = financials[1];

  console.log('Latest filing:', latest);
  console.log('Previous filing:', previous);

  const calculateChange = (current: number | undefined, prev: number | undefined): number | undefined => {
    if (!current || !prev) return undefined;
    return ((current - prev) / prev) * 100;
  };

  return (
    <div className="space-y-6">
      {/* Period Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-2xl font-bold text-[#D71E28] border-b-4 border-[#D71E28] pb-2 inline-block">Financial Metrics</h3>
          <p className="text-sm text-[#666666] mt-2">
            {latest.filing_type || 'Filing'} • {latest.period || 'Unknown'} • Filed: {latest.filing_date || 'N/A'}
          </p>
        </div>
      </div>

      {/* Income Statement */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <h4 className="text-lg font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
          Income Statement
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            label="Revenue"
            value={formatCurrency(latest.revenue)}
            change={calculateChange(latest.revenue, previous?.revenue)}
          />
          <MetricCard
            label="Operating Income"
            value={formatCurrency(latest.operating_income)}
            change={calculateChange(latest.operating_income, previous?.operating_income)}
          />
          <MetricCard
            label="Net Income"
            value={formatCurrency(latest.net_income)}
            change={calculateChange(latest.net_income, previous?.net_income)}
          />
        </div>
      </div>

      {/* Balance Sheet */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <h4 className="text-lg font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
          Balance Sheet
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            label="Total Assets"
            value={formatCurrency(latest.assets)}
            change={calculateChange(latest.assets, previous?.assets)}
          />
          <MetricCard
            label="Total Liabilities"
            value={formatCurrency(latest.liabilities)}
            change={calculateChange(latest.liabilities, previous?.liabilities)}
          />
          <MetricCard
            label="Shareholders Equity"
            value={formatCurrency(latest.equity)}
            change={calculateChange(latest.equity, previous?.equity)}
          />
        </div>
      </div>

      {/* Cash Flow Statement */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <h4 className="text-lg font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
          Cash Flow Statement
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            label="Operating Cash Flow"
            value={formatCurrency(latest.operating_cash_flow)}
            change={calculateChange(latest.operating_cash_flow, previous?.operating_cash_flow)}
          />
          <MetricCard
            label="Investing Cash Flow"
            value={formatCurrency(latest.investing_cash_flow)}
            change={calculateChange(latest.investing_cash_flow, previous?.investing_cash_flow)}
          />
          <MetricCard
            label="Financing Cash Flow"
            value={formatCurrency(latest.financing_cash_flow)}
            change={calculateChange(latest.financing_cash_flow, previous?.financing_cash_flow)}
          />
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  change
}: {
  label: string;
  value: string;
  change?: number;
}) {
  return (
    <div className="bg-gray-50 rounded p-4 border border-gray-300">
      <p className="text-xs text-[#666666] uppercase tracking-wide font-bold mb-2">{label}</p>
      <p className="text-2xl font-bold text-[#333333] mb-1">{value}</p>
      {change !== undefined && (
        <div className="flex items-center gap-1">
          <span className={`text-sm font-bold ${
            change >= 0 ? 'text-green-700' : 'text-red-700'
          }`}>
            {formatPercent(change)}
          </span>
          <span className="text-xs text-[#666666]">vs prev period</span>
        </div>
      )}
    </div>
  );
}
