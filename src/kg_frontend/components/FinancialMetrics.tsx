"use client";

import { useEffect, useState } from "react";

interface FinancialData {
  period?: string;
  filing_type?: string;
  filing_date?: string;
  revenue?: number;
  net_income?: number;
  operating_income?: number;
  assets?: number;
  total_assets?: number;
  liabilities?: number;
  total_liabilities?: number;
  equity?: number;
  stockholders_equity?: number;
  operating_cash_flow?: number;
  investing_cash_flow?: number;
  financing_cash_flow?: number;
}

interface Props {
  companyName: string;
}

const API = "http://localhost:8000";

function formatCurrency(value: number | undefined): string {
  if (value === undefined || value === null) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1
  }).format(value * 1_000_000);
}

function formatPercent(value: number | undefined): string {
  if (value === undefined || value === null) return 'N/A';
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
}

function normalise(f: any): FinancialData {
  return {
    period: f.filing_period || f.period || "Unknown",
    filing_type: f.filing_type || "10-K",
    filing_date: f.filing_date || "",
    revenue: f.revenue,
    net_income: f.net_income,
    operating_income: f.operating_income,
    assets: f.total_assets ?? f.assets,
    liabilities: f.total_liabilities ?? f.liabilities,
    equity: f.stockholders_equity ?? f.equity,
    operating_cash_flow: f.operating_cash_flow,
    investing_cash_flow: f.investing_cash_flow,
    financing_cash_flow: f.financing_cash_flow,
  };
}

export default function FinancialMetrics({ companyName }: Props) {
  const [financials, setFinancials] = useState<FinancialData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!companyName) return;
    setLoading(true);
    fetch(`${API}/company/${encodeURIComponent(companyName)}/graph`)
      .then(r => r.json())
      .then(d => {
        const raw = d.financials || [];
        setFinancials(raw.map(normalise));
      })
      .catch(() => setFinancials([]))
      .finally(() => setLoading(false));
  }, [companyName]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg p-12 text-center border-2 border-gray-200">
        <div className="inline-block w-10 h-10 border-4 border-[#D71E28] border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-[#666666] font-semibold">Loading financial data…</p>
      </div>
    );
  }

  if (!financials.length) {
    return (
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200">
        <p className="text-[#666666] text-center font-semibold">No financial data available</p>
        <p className="text-xs text-[#666666] text-center mt-2">
          Make sure to provide a valid stock ticker when researching the company.
        </p>
      </div>
    );
  }

  const latest = financials[0];
  const previous = financials[1];

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
