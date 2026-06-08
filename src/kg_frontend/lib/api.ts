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

  async getFreshness(
    companyName: string,
    windows?: { fin_window?: number; news_window?: number; prod_window?: number }
  ): Promise<any> {
    const params = new URLSearchParams();
    if (windows?.fin_window  != null) params.set("fin_window",  String(windows.fin_window));
    if (windows?.news_window != null) params.set("news_window", String(windows.news_window));
    if (windows?.prod_window != null) params.set("prod_window", String(windows.prod_window));
    const qs = params.toString();
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/freshness${qs ? "?" + qs : ""}`);
  },

  async getPeerComparison(companyName: string): Promise<{
    target: PeerCompanyMetrics;
    peers: PeerCompanyMetrics[];
  }> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/peer-comparison`);
  },

  async getOfficers(companyName: string): Promise<{
    company_name: string;
    officers: Record<string, unknown>[];
    total: number;
  }> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/officers`);
  },

  async searchOfficer(name: string, company: string, role?: string): Promise<Record<string, unknown>> {
    return fetchAPI('/officer/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, company, role: role ?? null }),
    });
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

  async getRecommendations(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/recommendations`);
  },

  async getBoardInterlocks(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/board-interlocks`);
  },

  async getRelationshipMap(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/relationship-map`);
  },

  async getTriggers(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/triggers`);
  },

  async getCovenantWatch(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/covenant-watch`);
  },

  async getIncumbentBank(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/incumbent-bank`);
  },

  async getMeetingBrief(companyName: string, contactName?: string, contactRole?: string): Promise<any> {
    const params = new URLSearchParams();
    if (contactName) params.set("contact_name", contactName);
    if (contactRole) params.set("contact_role", contactRole);
    const qs = params.toString();
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/meeting-brief${qs ? "?" + qs : ""}`);
  },

  async getActivities(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/activity`);
  },

  async addActivity(companyName: string, activity: {
    type: string; date: string; contact_name?: string;
    contact_role?: string; notes?: string; next_action?: string;
  }): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/activity`, {
      method: "POST", body: JSON.stringify(activity),
    });
  },

  async deleteActivity(activityId: string): Promise<any> {
    return fetchAPI(`/activity/${encodeURIComponent(activityId)}`, { method: "DELETE" });
  },

  async getDeals(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/deals`);
  },

  async addDeal(companyName: string, deal: {
    product: string; category: string; status?: string;
    amount?: string; start_date?: string; notes?: string;
  }): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/deals`, {
      method: "POST", body: JSON.stringify(deal),
    });
  },

  async deleteDeal(dealId: string): Promise<any> {
    return fetchAPI(`/deal/${encodeURIComponent(dealId)}`, { method: "DELETE" });
  },

  async getPortfolio(): Promise<any> {
    return fetchAPI("/rm/portfolio");
  },

  async getPitchScore(companyName: string): Promise<any> {
    return fetchAPI(`/company/${encodeURIComponent(companyName)}/pitch-score`);
  },

  async getIndustryHeatmap(): Promise<any> {
    return fetchAPI("/rm/industry-heatmap");
  },

  async getCompanies(): Promise<{ name: string; ticker: string; industry: string; headquarters: string }[]> {
    const data = await fetchAPI('/companies');
    return data.companies ?? [];
  },

  // System endpoints
  async healthCheck(): Promise<{ status: string; neo4j_connected: boolean; orchestrator_ready: boolean; llm_provider?: string; llm_model?: string; llm_label?: string }> {
    return fetchAPI('/health');
  },
};
