const API_BASE_URL = 'http://localhost:8000';

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
}

export interface PaginatedResponse<T> {
  total_count: number;
  items: T[];
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

  // ── Complaints ──
  async getComplaints(params?: { status?: string; area_id?: number; skip?: number; limit?: number }): Promise<any[]> {
    const qp = new URLSearchParams();
    if (params?.status) qp.append('status_filter', params.status);
    if (params?.area_id) qp.append('area_id', params.area_id.toString());
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    const response = await fetch(`${API_BASE_URL}/complaints?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch complaints');
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
  async getTasks(params?: { status?: string; area_id?: number; skip?: number; limit?: number }): Promise<any[]> {
    const qp = new URLSearchParams();
    if (params?.status) qp.append('status_filter', params.status);
    if (params?.area_id) qp.append('area_id', params.area_id.toString());
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    const response = await fetch(`${API_BASE_URL}/tasks?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch tasks');
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
  async getContracts(params?: { status?: string; skip?: number; limit?: number }): Promise<any[]> {
    const qp = new URLSearchParams();
    if (params?.status) qp.append('status_filter', params.status);
    if (params?.skip !== undefined) qp.append('skip', params.skip.toString());
    if (params?.limit !== undefined) qp.append('limit', params.limit.toString());
    const response = await fetch(`${API_BASE_URL}/contracts?${qp}`, { headers: this.getAuthHeaders() });
    if (!response.ok) throw new Error('Failed to fetch contracts');
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
  async getReportSummary(params?: { date_from?: string; date_to?: string; area_id?: number; status?: string }): Promise<any> {
    const qp = new URLSearchParams();
    if (params?.date_from) qp.append('date_from', params.date_from);
    if (params?.date_to) qp.append('date_to', params.date_to);
    if (params?.area_id) qp.append('area_id', params.area_id.toString());
    if (params?.status) qp.append('status', params.status);
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

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('cached_user');
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }
}

export const apiService = new ApiService();
