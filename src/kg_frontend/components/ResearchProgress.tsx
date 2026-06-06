"use client";

import { useEffect, useState } from "react";
import { api, APIError } from "../lib/api";

interface Props {
  jobId: string;
  companyName: string;
  onComplete: (result: any) => void;
}

interface JobStatus {
  job_id: string;
  status: string;
  company_name: string;
  started_at: string;
  completed_at?: string;
  progress: {
    completed_steps?: string[];
    total_steps?: number;
  };
  error?: string;
}

const STEPS = [
  { key: "company_info", label: "Company Website Research" },
  { key: "financials", label: "SEC Financial Data (10-K, 10-Q)" },
  { key: "news", label: "News & Sentiment Analysis" },
  { key: "products", label: "Product Portfolio Analysis" },
  { key: "industry", label: "Industry & Peer Analysis" },
  { key: "peer_financials", label: "Peer EDGAR Financials" },
  { key: "officer_research", label: "Officer Intelligence" },
  { key: "temporal_scoring", label: "Temporal Weighting-Freshness" },
  { key: "graph_populated", label: "Knowledge Graph Population" },
];

export default function ResearchProgress({
  jobId,
  companyName,
  onComplete,
}: Props) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const data = await api.getResearchStatus(jobId);
        setStatus(data);

        if (data.status === "completed") {
          setTimeout(() => onComplete(data.result || {}), 1500);
        } else if (data.status === "failed") {
          setError(data.error || "Research failed");
        }
      } catch (err) {
        if (err instanceof APIError) {
          setError(err.message);
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 2000);

    return () => clearInterval(interval);
  }, [jobId, onComplete]);

  const completedSteps = [...new Set(status?.progress?.completed_steps || [])];
  const isStepComplete = (stepKey: string) => completedSteps.includes(stepKey);
  const isStepActive = (index: number) => {
    return (
      status?.status === "running" && completedSteps.length === index
    );
  };

  const progressPercent = Math.min(
    100,
    status ? (completedSteps.length / STEPS.length) * 100 : 0
  );

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg p-8 shadow-lg border-2 border-gray-200">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-[#D71E28] mb-2 border-b-4 border-[#D71E28] pb-3 inline-block">
            Researching {companyName}
          </h2>
          <p className="text-[#666666] mt-4 font-semibold">
            {status?.status === "completed"
              ? "Research Complete"
              : status?.status === "failed"
              ? "Research Failed"
              : "Gathering data across multiple dimensions..."}
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between text-sm text-[#666666] font-bold mb-2 uppercase tracking-wide">
            <span>Progress</span>
            <span>{Math.round(progressPercent)}%</span>
          </div>
          <div className="h-4 bg-gray-200 rounded overflow-hidden border border-gray-300">
            <div
              className="h-full bg-[#D71E28] transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {STEPS.map((step, index) => {
            const complete = isStepComplete(step.key);
            const active = isStepActive(index);

            return (
              <div
                key={step.key}
                className={`flex items-center p-4 rounded border-l-4 transition-all ${
                  complete
                    ? "bg-green-50 border-green-600"
                    : active
                    ? "bg-yellow-50 border-[#FFCD41]"
                    : "bg-gray-50 border-gray-300"
                }`}
              >
                <div className="flex-1">
                  <p
                    className={`font-bold text-sm ${
                      complete
                        ? "text-green-700"
                        : active
                        ? "text-[#D71E28]"
                        : "text-[#666666]"
                    }`}
                  >
                    {step.label}
                  </p>
                </div>
                <div className="ml-4">
                  {complete && (
                    <span className="text-xs font-bold text-green-700 bg-green-100 px-3 py-1 rounded uppercase tracking-wide">
                      Complete
                    </span>
                  )}
                  {active && (
                    <span className="text-xs font-bold text-[#D71E28] bg-yellow-100 px-3 py-1 rounded uppercase tracking-wide">
                      In Progress
                    </span>
                  )}
                  {!complete && !active && (
                    <span className="text-xs font-bold text-gray-500 bg-gray-200 px-3 py-1 rounded uppercase tracking-wide">
                      Pending
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {error && (
          <div className="mt-6 p-4 bg-red-50 border-2 border-red-600 rounded text-red-700">
            <p className="font-bold uppercase tracking-wide text-sm mb-1">Error:</p>
            <p className="text-sm">{error}</p>
          </div>
        )}

        {status?.status === "completed" && (
          <div className="mt-6 p-4 bg-green-50 border-2 border-green-600 rounded text-green-700 text-center">
            <p className="font-bold text-lg uppercase tracking-wide">
              Research Completed Successfully
            </p>
            <p className="text-sm mt-1">Loading results...</p>
          </div>
        )}
      </div>
    </div>
  );
}
