// Use VITE_API_URL when set (e.g. Docker: http://localhost:8000). Else relative URLs ('' = Vite proxy) in dev.
const API_URL =
  import.meta.env.VITE_API_URL && String(import.meta.env.VITE_API_URL).trim() !== ''
    ? String(import.meta.env.VITE_API_URL).replace(/\/$/, '')
    : import.meta.env.DEV
      ? ''
      : (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000');

export interface Organization {
  id: string;
  name: string;
  created_at: string;
}

export interface Cycle {
  id: string;
  org_id: string;
  vertical_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Questionnaire {
  schema_version: string;
  vertical_id: string;
  title: string;
  description: string;
  sections: QuestionnaireSection[];
}

export interface QuestionnaireSection {
  id: string;
  title: string;
  questions: Question[];
}

export interface Question {
  id: string;
  label: string;
  type: 'single_select' | 'multi_select' | 'likert_1_5' | 'short_text' | 'long_text' | 'ranking';
  required: boolean;
  options?: string[];
  max_selected?: number;
  max_chars?: number;
  min_label?: string;
  max_label?: string;
  helper_text?: string;
  ranking_min?: number;
  ranking_max?: number;
}

export interface Results {
  cycle_id: string;
  status: string;
  category_scores: any[];
  core_initiatives: Initiative[];
  sandbox_initiatives: Initiative[];
}

export interface Initiative {
  id: string;
  title: string;
  body: any;
  rank: number;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const base = API_URL || '';
  const url = base ? `${base}${endpoint}` : endpoint;
  let response: Response;

  try {
    response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
  } catch (err) {
    if (err instanceof TypeError && err.message === 'Failed to fetch') {
      const hint = base ? ` at ${base}` : ' (same origin)';
      throw new Error(`Could not connect to API${hint} Is the backend running? Try "make up" or "docker-compose up".`);
    }
    throw err;
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    const msg = typeof error?.detail === 'string'
      ? error.detail
      : Array.isArray(error?.detail)
        ? error.detail.map((e: { msg?: string }) => e?.msg).filter(Boolean).join('; ') || response.statusText
        : error?.detail ?? response.statusText;
    throw new Error(String(msg || `HTTP error! status: ${response.status}`));
  }

  return response.json();
}

export const api = {
  createOrg: (name: string) =>
    request<Organization>('/api/orgs', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  getOrg: (orgId: string) =>
    request<Organization>(`/api/orgs/${orgId}`),

  createCycle: (orgId: string) =>
    request<Cycle>('/api/cycles', {
      method: 'POST',
      body: JSON.stringify({ org_id: orgId }),
    }),

  getCycle: (cycleId: string) =>
    request<Cycle>(`/api/cycles/${cycleId}`),

  getQuestionnaire: (cycleId: string) =>
    request<Questionnaire>(`/api/cycles/${cycleId}/questionnaire`),

  saveQuestionnaire: (cycleId: string, responses: Record<string, any>) =>
    request(`/api/cycles/${cycleId}/questionnaire`, {
      method: 'POST',
      body: JSON.stringify({ responses }),
    }),

  generate: (cycleId: string) =>
    request(`/api/cycles/${cycleId}/generate`, {
      method: 'POST',
    }),

  getResults: (cycleId: string) =>
    request<Results>(`/api/cycles/${cycleId}/results`),
};
