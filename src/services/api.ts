import { config } from '@/config';

const API_BASE_URL = config.API_BASE_URL;

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  username: string;
  email?: string;
  full_name: string;
  role: string;
  phone?: string;
  is_active: number;
  created_at: string;
  org_unit_id?: number | null;
}

export interface MePermissionsResponse {
  user_id: number;
  role: string;
  org_unit_id: number | null;
  governorate_id: number | null;
  municipality_id: number | null;
  district_id: number | null;
  scope_unit_ids: number[] | null;
  permissions: { resource: string; action: string }[];
}

export interface PaginatedResponse<T> {
  total_count: number;
  items: T[];
}

/**
 * Structured error thrown by the API service for non-2xx HTTP responses.
 *
 * Carries the actual HTTP status, the server-provided `detail` (when the body
 * is JSON-decodable), and the request URL so callers can give the operator a
 * truthful diagnostic instead of swallowing the failure with a generic
 * "فشل تحميل ..." message.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly statusText: string;
  readonly detail: string | null;
  readonly url: string;
  readonly body: unknown;

  constructor(opts: {
    status: number;
    statusText: string;
    detail: string | null;
    url: string;
    body: unknown;
    message?: string;
  }) {
    super(opts.message ?? `HTTP ${opts.status}: ${opts.detail ?? opts.statusText}`);
    this.name = 'ApiError';
    this.status = opts.status;
    this.statusText = opts.statusText;
    this.detail = opts.detail;
    this.url = opts.url;
    this.body = opts.body;
  }
}

/** Maximum number of characters of a non-JSON error body to keep for diagnostics. */
const MAX_ERROR_TEXT_LENGTH = 500;

/**
 * Read a fetch Response, attempt to extract a JSON `detail` (FastAPI's
 * standard error shape) or fall back to the raw text, and return both.
 */
async function readErrorBody(response: Response): Promise<{ detail: string | null; body: unknown }> {
  let text = '';
  try {
    text = await response.text();
  } catch {
    return { detail: null, body: null };
  }
  if (!text) return { detail: null, body: null };
  try {
    const parsed = JSON.parse(text);
    let detail: string | null = null;
    if (parsed && typeof parsed === 'object') {
      const d = (parsed as Record<string, unknown>).detail;
      if (typeof d === 'string') detail = d;
      else if (d != null) detail = JSON.stringify(d);
    }
    return { detail, body: parsed };
  } catch {
    return { detail: text.slice(0, MAX_ERROR_TEXT_LENGTH), body: text };
  }
}

/**
 * Throw a structured ApiError from a failed Response. Callers should `await`
 * this when `response.ok` is false.
 */
async function throwApiError(response: Response, fallbackMessage: string): Promise<never> {
  const { detail, body } = await readErrorBody(response);
  throw new ApiError({
    status: response.status,
    statusText: response.statusText,
    detail,
    url: response.url,
    body,
    message: `${fallbackMessage} (HTTP ${response.status}${detail ? `: ${detail}` : ''})`,
  });
}

class ApiService {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  async login(credentials: LoginCredentials): Promise<AuthToken> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    if (!response.ok) throw new Error('Login failed');
    const data: AuthToken = await response.json();
    localStorage.setItem('access_token', data.access_token);
    // Pre-fetch and cache user info for RBAC
    try {
      const userResp = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${data.access_token}`,
        },
      });
      if (userResp.ok) {
        const user = await userResp.json();
        localStorage.setItem('cached_user', JSON.stringify(user));
      }
    } catch {
      // Non-critical – useAuth will fetch it anyway
    }
    return data;
  }

  async getCurrentUser(): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch user');
    return response.json();
  }

  async getCurrentUserPermissions(): Promise<MePermissionsResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/me/permissions`, {
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch permissions');
    return response.json();
  }

  // ── Complaints ──
  async getComplaints(params?: { status?: string; area_id?: number; location_id?: number; project_id?: number; search?: string; skip?: number; limit?: number }): Promise<PaginatedResponse<any>> {
    const qp = new URLSearchParams();
    if (params?.status) qp.append('status_filter', params.status);
    if (params?.area_id) qp.append('area_id', params.area_id.toString());
    if (params?.location_id) qp.append('location_id', params.location_id.toString());
    if (params?.project_id) qp.append('project_id', params.project_id.toString());
    if (params?.search) qp.append('search', params.search);
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    // NOTE: trailing slash is required. The backend route is `@router.get("/")`
    // so `/complaints` triggers a 307 redirect to `/complaints/`. Behind nginx
    // (HTTPS) the redirect Location is built with `http://` because Starlette
    // doesn't trust X-Forwarded-Proto, which the browser then blocks as mixed
    // content and the fetch fails. Calling the canonical URL avoids the redirect.
    const response = await fetch(`${API_BASE_URL}/complaints/?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) await throwApiError(response, 'Failed to fetch complaints');
    return response.json();
  }

  async getComplaint(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/complaints/${id}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch complaint');
    return response.json();
  }

  async createComplaint(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/complaints/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create complaint');
    return response.json();
  }

  async trackComplaint(tracking_number: string, phone: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/complaints/track`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tracking_number, phone }),
    });
    if (!response.ok) throw new Error('Complaint not found');
    return response.json();
  }

  async updateComplaint(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/complaints/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update complaint');
    return response.json();
  }

  async getComplaintActivities(id: number): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/complaints/${id}/activities`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch activities');
    return response.json();
  }

  // ── Tasks ──
  async getTasks(params?: { status?: string; area_id?: number; location_id?: number; project_id?: number; team_id?: number; complaint_id?: number; assigned_to_id?: number; search?: string; priority?: string; skip?: number; limit?: number }): Promise<PaginatedResponse<any>> {
    const qp = new URLSearchParams();
    if (params?.status) qp.append('status_filter', params.status);
    if (params?.area_id) qp.append('area_id', params.area_id.toString());
    if (params?.location_id) qp.append('location_id', params.location_id.toString());
    if (params?.project_id) qp.append('project_id', params.project_id.toString());
    if (params?.team_id) qp.append('team_id', params.team_id.toString());
    if (params?.complaint_id) qp.append('complaint_id', params.complaint_id.toString());
    if (params?.assigned_to_id) qp.append('assigned_to_id', params.assigned_to_id.toString());
    if (params?.search) qp.append('search', params.search);
    if (params?.priority) qp.append('priority_filter', params.priority);
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    // Trailing slash required — see note on getComplaints().
    const response = await fetch(`${API_BASE_URL}/tasks/?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) await throwApiError(response, 'Failed to fetch tasks');
    return response.json();
  }

  async getTask(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch task');
    return response.json();
  }

  async createTask(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/tasks/`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create task');
    return response.json();
  }

  async updateTask(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update task');
    return response.json();
  }

  async getTaskActivities(id: number): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}/activities`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch activities');
    return response.json();
  }

  // ── Contracts ──
  async getContracts(params?: { status?: string; contract_type?: string; project_id?: number; search?: string; skip?: number; limit?: number }): Promise<PaginatedResponse<any>> {
    const qp = new URLSearchParams();
    if (params?.status) qp.append('status_filter', params.status);
    if (params?.contract_type) qp.append('contract_type', params.contract_type);
    if (params?.project_id) qp.append('project_id', params.project_id.toString());
    if (params?.search) qp.append('search', params.search);
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    // Trailing slash required — see note on getComplaints().
    const response = await fetch(`${API_BASE_URL}/contracts/?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) await throwApiError(response, 'Failed to fetch contracts');
    return response.json();
  }

  async getContract(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contracts/${id}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch contract');
    return response.json();
  }

  async createContract(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contracts/`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create contract');
    return response.json();
  }

  async updateContract(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contracts/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update contract');
    return response.json();
  }

  async approveContract(id: number, action: string, comments?: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contracts/${id}/approve`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ action, comments }),
    });
    if (!response.ok) throw new Error('Failed to approve contract');
    return response.json();
  }

  async deleteContract(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contracts/${id}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to delete contract');
    return response.json();
  }

  async generateContractPdf(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contracts/${id}/generate-pdf`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to generate PDF');
    return response.json();
  }

  async getContractApprovals(id: number): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/contracts/${id}/approvals`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch approvals');
    return response.json();
  }

  // ── Projects ──
  async getProjects(params?: { status?: string; location_id?: number; contract_id?: number; search?: string; skip?: number; limit?: number }): Promise<PaginatedResponse<any>> {
    const qp = new URLSearchParams();
    if (params?.status) qp.append('status', params.status);
    if (params?.location_id) qp.append('location_id', params.location_id.toString());
    if (params?.contract_id) qp.append('contract_id', params.contract_id.toString());
    if (params?.search) qp.append('search', params.search);
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    // Trailing slash required — see note on getComplaints().
    const response = await fetch(`${API_BASE_URL}/projects/?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) await throwApiError(response, 'Failed to fetch projects');
    return response.json();
  }

  async getProject(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/projects/${id}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch project');
    return response.json();
  }

  async createProject(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/projects/`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create project');
    return response.json();
  }

  async updateProject(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/projects/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update project');
    return response.json();
  }

  async deleteProject(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/projects/${id}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to delete project');
    return response.json();
  }

  // ── Teams ──
  async getTeams(params?: { team_type?: string; is_active?: boolean; project_id?: number; location_id?: number; search?: string; skip?: number; limit?: number }): Promise<PaginatedResponse<any>> {
    const qp = new URLSearchParams();
    if (params?.team_type) qp.append('team_type', params.team_type);
    if (params?.is_active !== undefined) qp.append('is_active', params.is_active.toString());
    if (params?.project_id) qp.append('project_id', params.project_id.toString());
    if (params?.location_id) qp.append('location_id', params.location_id.toString());
    if (params?.search) qp.append('search', params.search);
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    // Trailing slash required — see note on getComplaints().
    const response = await fetch(`${API_BASE_URL}/teams/?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) await throwApiError(response, 'Failed to fetch teams');
    return response.json();
  }

  async getActiveTeams(): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/teams/active`, { headers: this.getAuthHeaders() });
    if (!response.ok) await throwApiError(response, 'Failed to fetch active teams');
    return response.json();
  }

  async getTeam(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/teams/${id}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch team');
    return response.json();
  }

  async createTeam(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/teams/`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create team');
    return response.json();
  }

  async updateTeam(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/teams/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update team');
    return response.json();
  }

  async deactivateTeam(id: number): Promise<any> {
    return this.updateTeam(id, { is_active: false });
  }

  // ── Settings ──
  async getSettings(): Promise<Record<string, any[]>> {
    const response = await fetch(`${API_BASE_URL}/settings/`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch settings');
    return response.json();
  }

  async updateSettings(items: any[]): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/settings/`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ items }),
    });
    if (!response.ok) throw new Error('Failed to update settings');
    return response.json();
  }

  async createTaskFromComplaint(complaintId: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/complaints/${complaintId}/create-task`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create task from complaint');
    return response.json();
  }

  // ── Dashboard ──
  async getDashboardStats(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/dashboard/stats`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch dashboard stats');
    return response.json();
  }

  async getRecentActivity(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/dashboard/recent-activity`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch recent activity');
    return response.json();
  }

  // ── Locations ──
  async getAreas(): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/locations/areas`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch areas');
    return response.json();
  }

  async getBuildings(areaId?: number): Promise<any[]> {
    const qp = new URLSearchParams();
    if (areaId) qp.append('area_id', areaId.toString());
    const response = await fetch(`${API_BASE_URL}/locations/buildings?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch buildings');
    return response.json();
  }

  // ── Unified Locations ──
  async getLocations(params?: {
    location_type?: string; status?: string; parent_id?: number;
    is_active?: number; search?: string;
    has_open_complaints?: boolean; has_active_tasks?: boolean; has_contract_coverage?: boolean;
    skip?: number; limit?: number;
  }): Promise<any[]> {
    const qp = new URLSearchParams();
    if (params?.location_type) qp.append('location_type', params.location_type);
    if (params?.status) qp.append('status', params.status);
    if (params?.parent_id !== undefined) qp.append('parent_id', params.parent_id.toString());
    if (params?.is_active !== undefined) qp.append('is_active', params.is_active.toString());
    if (params?.search) qp.append('search', params.search);
    if (params?.has_open_complaints) qp.append('has_open_complaints', 'true');
    if (params?.has_active_tasks) qp.append('has_active_tasks', 'true');
    if (params?.has_contract_coverage) qp.append('has_contract_coverage', 'true');
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    const response = await fetch(`${API_BASE_URL}/locations/list?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch locations');
    return response.json();
  }

  async getLocationTree(): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/locations/tree`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch location tree');
    return response.json();
  }

  async getLocationDetail(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/detail/${id}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch location detail');
    return response.json();
  }

  async getLocationComplaints(id: number, statusFilter?: string): Promise<any> {
    const qp = new URLSearchParams();
    if (statusFilter) qp.append('status_filter', statusFilter);
    const response = await fetch(`${API_BASE_URL}/locations/detail/${id}/complaints?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch location complaints');
    return response.json();
  }

  async getLocationTasks(id: number, statusFilter?: string): Promise<any> {
    const qp = new URLSearchParams();
    if (statusFilter) qp.append('status_filter', statusFilter);
    const response = await fetch(`${API_BASE_URL}/locations/detail/${id}/tasks?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch location tasks');
    return response.json();
  }

  async getLocationContracts(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/detail/${id}/contracts`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch location contracts');
    return response.json();
  }

  async getLocationActivity(id: number): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/locations/detail/${id}/activity`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch location activity');
    return response.json();
  }

  async getLocationStats(locationType?: string): Promise<any[]> {
    const qp = new URLSearchParams();
    if (locationType) qp.append('location_type', locationType);
    const response = await fetch(`${API_BASE_URL}/locations/stats/all?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch location stats');
    return response.json();
  }

  async getLocationReportSummary(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/reports/summary`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch location report');
    return response.json();
  }

  async createLocation(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create location');
    }
    return response.json();
  }

  async updateLocation(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update location');
    }
    return response.json();
  }

  async deleteLocation(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/${id}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to delete location');
    }
    return response.json();
  }

  async getLocationMapData(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/detail/${id}/map-data`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch location map data');
    return response.json();
  }

  async exportLocationReportCSV(params?: { location_type?: string; status?: string }): Promise<Blob> {
    const qp = new URLSearchParams();
    if (params?.location_type) qp.append('location_type', params.location_type);
    if (params?.status) qp.append('status', params.status);
    const response = await fetch(`${API_BASE_URL}/locations/reports/export/csv?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to export location report');
    }
    return response.blob();
  }

  async getContractLocations(contractId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/contracts/${contractId}/locations`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch contract locations');
    return response.json();
  }

  async linkContractToLocation(contractId: number, locationId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/contracts/link?contract_id=${contractId}&location_id=${locationId}`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to link contract to location');
    }
    return response.json();
  }

  async unlinkContractFromLocation(contractId: number, locationId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/contracts/link?contract_id=${contractId}&location_id=${locationId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to unlink contract from location');
    }
    return response.json();
  }

  async getGeoDashboard(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/locations/geo-dashboard`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch geo dashboard');
    return response.json();
  }

  // ── Users ──
  async getUsers(params?: { search?: string; role_filter?: string; is_active?: boolean; skip?: number; limit?: number }): Promise<PaginatedResponse<User>> {
    const qp = new URLSearchParams();
    if (params?.search) qp.append('search', params.search);
    if (params?.role_filter) qp.append('role_filter', params.role_filter);
    if (params?.is_active !== undefined) qp.append('is_active', params.is_active.toString());
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    const response = await fetch(`${API_BASE_URL}/users?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch users');
    return response.json();
  }

  async getUser(id: number): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/users/${id}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch user');
    return response.json();
  }

  async createUser(data: any): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/users/`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create user');
    }
    return response.json();
  }

  async updateUser(id: number, data: any): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/users/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update user');
    }
    return response.json();
  }

  async deactivateUser(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/users/${id}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to deactivate user');
    return response.json();
  }

  // ── File Upload ──
  async uploadFile(file: File, category: string): Promise<any> {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/uploads/?category=${encodeURIComponent(category)}`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to upload file');
    return response.json();
  }

  async uploadFilePublic(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/uploads/public`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to upload file');
    return response.json();
  }

  // ── Reports ──
  async getReportSummary(params?: { date_from?: string; date_to?: string; area_id?: number; status?: string; complaint_type?: string; contract_type?: string; priority?: string; assigned_to_id?: number }): Promise<any> {
    const qp = new URLSearchParams();
    if (params?.date_from) qp.append('date_from', params.date_from);
    if (params?.date_to) qp.append('date_to', params.date_to);
    if (params?.area_id) qp.append('area_id', params.area_id.toString());
    if (params?.status) qp.append('status', params.status);
    if (params?.complaint_type) qp.append('complaint_type', params.complaint_type);
    if (params?.contract_type) qp.append('contract_type', params.contract_type);
    if (params?.priority) qp.append('priority', params.priority);
    if (params?.assigned_to_id) qp.append('assigned_to_id', params.assigned_to_id.toString());
    const response = await fetch(`${API_BASE_URL}/reports/summary?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch report summary');
    return response.json();
  }

  async getReportComplaints(params?: Record<string, any>): Promise<any> {
    const qp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qp.append(k, String(v));
      });
    }
    const response = await fetch(`${API_BASE_URL}/reports/complaints?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch complaints report');
    return response.json();
  }

  async getReportTasks(params?: Record<string, any>): Promise<any> {
    const qp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qp.append(k, String(v));
      });
    }
    const response = await fetch(`${API_BASE_URL}/reports/tasks?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch tasks report');
    return response.json();
  }

  async getReportContracts(params?: Record<string, any>): Promise<any> {
    const qp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qp.append(k, String(v));
      });
    }
    const response = await fetch(`${API_BASE_URL}/reports/contracts?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch contracts report');
    return response.json();
  }

  async downloadReportCsv(entity: 'complaints' | 'tasks' | 'contracts', params?: Record<string, any>): Promise<void> {
    const qp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '' && v !== 'all') qp.append(k, String(v));
      });
    }
    const response = await fetch(`${API_BASE_URL}/reports/${entity}/csv?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to download CSV');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${entity}_report.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // ── Citizen Dashboard ──
  async getCitizenComplaints(params?: { status_filter?: string; skip?: number; limit?: number }): Promise<PaginatedResponse<any>> {
    const qp = new URLSearchParams();
    if (params?.status_filter) qp.append('status_filter', params.status_filter);
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    const response = await fetch(`${API_BASE_URL}/complaints/citizen/my-complaints?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch citizen complaints');
    return response.json();
  }

  // ── Complaints Map ──
  async getComplaintsMapMarkers(params?: { status_filter?: string; area_id?: number }): Promise<any[]> {
    const qp = new URLSearchParams();
    if (params?.status_filter) qp.append('status_filter', params.status_filter);
    if (params?.area_id) qp.append('area_id', params.area_id.toString());
    const response = await fetch(`${API_BASE_URL}/complaints/map/markers?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch map markers');
    return response.json();
  }

  // ── GIS / Operations Map ──
  async getOperationsMapMarkers(params?: { entity_type?: string; status_filter?: string; area_id?: number }): Promise<any[]> {
    const qp = new URLSearchParams();
    if (params?.entity_type) qp.append('entity_type', params.entity_type);
    if (params?.status_filter) qp.append('status_filter', params.status_filter);
    if (params?.area_id) qp.append('area_id', params.area_id.toString());
    const response = await fetch(`${API_BASE_URL}/gis/operations-map?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch operations map markers');
    return response.json();
  }

  async getAreaBoundaries(): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/gis/area-boundaries`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch area boundaries');
    return response.json();
  }

  // ── Notifications ──
  async getNotifications(params?: { skip?: number; limit?: number; unread_only?: boolean }): Promise<{ total_count: number; unread_count: number; items: any[] }> {
    const qp = new URLSearchParams();
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    if (params?.unread_only) qp.append('unread_only', 'true');
    const response = await fetch(`${API_BASE_URL}/notifications?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch notifications');
    return response.json();
  }

  async markNotificationsRead(ids: number[]): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/notifications/mark-read`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ notification_ids: ids }),
    });
    if (!response.ok) throw new Error('Failed to mark notifications read');
    return response.json();
  }

  async markAllNotificationsRead(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/notifications/mark-all-read`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to mark all notifications read');
    return response.json();
  }

  // ── Contract Intelligence ──
  async getIntelligenceDashboard(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/dashboard`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch intelligence dashboard');
    return response.json();
  }

  async getProcessingQueue(params?: { status_filter?: string; skip?: number; limit?: number }): Promise<any> {
    const qp = new URLSearchParams();
    if (params?.status_filter) qp.append('status_filter', params.status_filter);
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/queue?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch processing queue');
    return response.json();
  }

  async uploadContractDocument(file: File): Promise<any> {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/upload`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to upload contract document');
    return response.json();
  }

  async getContractDocument(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/documents/${id}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch document');
    return response.json();
  }

  async updateContractDocument(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/documents/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update document');
    return response.json();
  }

  async approveContractDocument(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/documents/${id}/approve`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to approve document');
    return response.json();
  }

  async rejectContractDocument(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/documents/${id}/reject`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to reject document');
    return response.json();
  }

  async reprocessDocument(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/documents/${id}/reprocess`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to reprocess document');
    return response.json();
  }

  async convertDocumentToContract(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/documents/${id}/convert-to-contract`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to convert to contract');
    return response.json();
  }

  async getIntelligenceRisks(params?: { document_id?: number; contract_id?: number; unresolved_only?: boolean }): Promise<any[]> {
    const qp = new URLSearchParams();
    if (params?.document_id) qp.append('document_id', params.document_id.toString());
    if (params?.contract_id) qp.append('contract_id', params.contract_id.toString());
    if (params?.unresolved_only) qp.append('unresolved_only', 'true');
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/risks?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch risks');
    return response.json();
  }

  async resolveRiskFlag(id: number, notes?: string): Promise<any> {
    const qp = new URLSearchParams();
    if (notes) qp.append('resolution_notes', notes);
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/risks/${id}/resolve?${qp}`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to resolve risk');
    return response.json();
  }

  async getIntelligenceDuplicates(params?: { status_filter?: string; document_id?: number }): Promise<any[]> {
    const qp = new URLSearchParams();
    if (params?.status_filter) qp.append('status_filter', params.status_filter);
    if (params?.document_id) qp.append('document_id', params.document_id.toString());
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/duplicates?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch duplicates');
    return response.json();
  }

  async reviewDuplicate(id: number, data: { status: string; review_notes?: string }): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/duplicates/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to review duplicate');
    return response.json();
  }

  async previewCsvImport(file: File): Promise<any> {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/bulk-import/preview-csv`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to preview CSV');
    return response.json();
  }

  async executeCsvImport(file: File): Promise<any> {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/bulk-import/execute-csv`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to execute CSV import');
    return response.json();
  }

  async bulkScanImport(files: File[]): Promise<any> {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/bulk-import/scan-batch`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to bulk scan import');
    return response.json();
  }

  async getContractIntelligence(contractId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/contracts/${contractId}/intelligence`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch contract intelligence');
    return response.json();
  }

  async analyzeContractRisks(contractId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/contracts/${contractId}/analyze-risks`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to analyze risks');
    return response.json();
  }

  async detectContractDuplicates(contractId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/contracts/${contractId}/detect-duplicates`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to detect duplicates');
    return response.json();
  }

  // Excel import
  async previewExcelImport(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/bulk-import/preview-excel`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to preview Excel');
    return response.json();
  }

  async executeExcelImport(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/bulk-import/execute-excel`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to execute Excel import');
    return response.json();
  }

  // OCR status
  async getOcrStatus(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/ocr-status`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch OCR status');
    return response.json();
  }

  // --- Intelligence report helpers ---
  private _buildQueryParams(params?: Record<string, any>): URLSearchParams {
    const qp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qp.append(k, String(v));
      });
    }
    return qp;
  }

  // Intelligence reports (with filters)
  async getIntelligenceReports(params?: Record<string, any>): Promise<any> {
    const qp = this._buildQueryParams(params);
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/reports?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch intelligence reports');
    return response.json();
  }

  // Intelligence report exports
  async downloadIntelligenceCsv(params?: Record<string, any>): Promise<void> {
    const qp = this._buildQueryParams(params);
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/reports/export/csv?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to download CSV');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'intelligence_report.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async downloadIntelligencePdf(params?: Record<string, any>): Promise<void> {
    const qp = this._buildQueryParams(params);
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/reports/export/pdf?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to download PDF');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'intelligence_report.pdf';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async downloadDocumentPdf(documentId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/contract-intelligence/documents/${documentId}/export/pdf`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to download document PDF');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `document_${documentId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('cached_user');
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }
}

export const apiService = new ApiService();
