// API client configuration and utilities

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }
}

// Types
export interface CompanyResearchRequest {
  company_name: string;
  ticker?: string | null;
  website?: string | null;
}

export interface ResearchStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  company_name: string;
  started_at: string;
  completed_at?: string;
  progress?: {
    completed_steps?: string[];
    total_steps?: number;
  };
  result?: ResearchResult;
  error?: string;
}

export interface ResearchResult {
  summary: string;
  dimensions: {
    company_info?: any;
    financials?: any;
    news?: any;
    products?: any;
    industry?: any;
  };
  temporal_summary?: {
    total_items: number;
    fresh_items: number;
    recent_items: number;
    aged_items: number;
    stale_items: number;
    avg_relevance_score: number;
  };
  completed_steps: string[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  data: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  data?: Record<string, any>;
}

export interface GraphVisualization {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Company {
  name: string;
  ticker?: string;
}

export interface PeerCompanyMetrics {
  name: string;
  ticker?: string | null;
  revenue?: number | null;
  net_income?: number | null;
  operating_income?: number | null;
  total_assets?: number | null;
  stockholders_equity?: number | null;
  net_margin?: number | null;
  filing_period?: string;
  filing_type?: string;
  relationship?: string;
  estimated_size?: string;
}

// API functions
export const api = {
  // Research endpoints
  async startResearch(request: CompanyResearchRequest): Promise<ResearchStatus> {
    return fetchAPI<ResearchStatus>('/research/start', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async getResearchStatus(jobId: string): Promise<ResearchStatus> {
    return fetchAPI<ResearchStatus>(`/research/status/${jobId}`);
  },

  async listResearchJobs(): Promise<{ jobs: ResearchStatus[]; total: number }> {
    return fetchAPI('/research/jobs');
  },

  // Company endpoints
  async getCompanyGraph(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/graph`);
  },

  async getVisualizationData(companyName: string): Promise<GraphVisualization> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/visualization`);
  },

  async deleteCompany(companyName: string): Promise<{ message: string }> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}`, {
      method: 'DELETE',
    });
  },

  async listCompanies(): Promise<{ companies: Company[]; total: number }> {
    return fetchAPI('/companies');
  },

  async getFreshness(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/freshness`);
  },

  async getPeerComparison(companyName: string): Promise<{
    target: PeerCompanyMetrics;
    peers: PeerCompanyMetrics[];
  }> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/peer-comparison`);
  },

  async getStockAroundDates(ticker: string, dates: string[]): Promise<Record<string, {
    before: { date: string | null; close: number | null };
    on:     { date: string | null; close: number | null };
    after:  { date: string | null; close: number | null };
    change_pct: number | null;
    color: 'red' | 'green' | 'black' | 'gray';
  }>> {
    if (!ticker || dates.length === 0) return {};
    const dateParam = dates.join(',');
    return fetchAPI(`/stock/${encodeURIComponent(ticker)}/around-dates?dates=${encodeURIComponent(dateParam)}`);
  },

  // System endpoints
  async healthCheck(): Promise<{ status: string; neo4j_connected: boolean; orchestrator_ready: boolean }> {
    return fetchAPI('/health');
  },
};
