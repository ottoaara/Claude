"use client";

import { useState } from "react";
import { api, APIError } from "../lib/api";

interface Props {
  onResearchStart: (jobId: string, companyName: string) => void;
}

export default function CompanyResearchForm({ onResearchStart }: Props) {
  const [companyName, setCompanyName] = useState("");
  const [ticker, setTicker] = useState("");
  const [website, setWebsite] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await api.startResearch({
        company_name: companyName,
        ticker: ticker || null,
        website: website || null,
      });

      onResearchStart(data.job_id, companyName);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : "Unknown error occurred");
      }
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg p-8 shadow-lg border-2 border-gray-200">
      <h2 className="text-2xl font-bold text-[#333333] mb-6 border-b-4 border-[#D71E28] pb-3">
        Start Company Research
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-bold text-[#333333] mb-2 uppercase tracking-wide">
            Company Name *
          </label>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            required
            placeholder="e.g., Apple Inc."
            className="w-full px-4 py-3 bg-white border-2 border-gray-300 rounded text-[#333333] placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#D71E28] focus:border-[#D71E28]"
          />
        </div>

        <div>
          <label className="block text-sm font-bold text-[#333333] mb-2 uppercase tracking-wide">
            Stock Ticker (Optional)
          </label>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="e.g., AAPL"
            maxLength={5}
            className="w-full px-4 py-3 bg-white border-2 border-gray-300 rounded text-[#333333] placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#D71E28] focus:border-[#D71E28]"
          />
          <p className="text-xs text-[#666666] mt-1">
            Required for SEC financial data (10-K, 10-Q)
          </p>
        </div>

        <div>
          <label className="block text-sm font-bold text-[#333333] mb-2 uppercase tracking-wide">
            Website (Optional)
          </label>
          <input
            type="url"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            placeholder="e.g., https://www.apple.com"
            className="w-full px-4 py-3 bg-white border-2 border-gray-300 rounded text-[#333333] placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#D71E28] focus:border-[#D71E28]"
          />
        </div>

        {error && (
          <div className="p-4 bg-red-50 border-2 border-red-300 rounded text-red-700 font-semibold">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !companyName}
          className="w-full px-6 py-4 bg-[#D71E28] hover:bg-[#A91B23] text-white font-bold rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md uppercase tracking-wide"
        >
          {loading ? "Starting Research..." : "Start Research"}
        </button>
      </form>

      <div className="mt-6 p-4 bg-gray-50 border-2 border-gray-200 rounded">
        <h3 className="text-sm font-bold text-[#333333] mb-2 uppercase tracking-wide">
          Research Dimensions:
        </h3>
        <ul className="text-sm text-[#666666] space-y-1">
          <li>Company info from public website</li>
          <li>Financial data from SEC Edgar (10-K, 10-Q)</li>
          <li>Recent news and sentiment analysis</li>
          <li>Product portfolio analysis</li>
          <li>Industry analysis with NAICS classification & peer comparison</li>
        </ul>
      </div>
    </div>
  );
}
