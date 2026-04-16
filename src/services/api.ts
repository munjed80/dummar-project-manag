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

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data: AuthToken = await response.json();
    localStorage.setItem('access_token', data.access_token);
    return data;
  }

  async getCurrentUser(): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch user');
    }

    return response.json();
  }

  async getComplaints(params?: { status?: string; area_id?: number }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status_filter', params.status);
    if (params?.area_id) queryParams.append('area_id', params.area_id.toString());

    const response = await fetch(`${API_BASE_URL}/complaints?${queryParams}`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch complaints');
    }

    return response.json();
  }

  async getComplaint(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/complaints/${id}`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch complaint');
    }

    return response.json();
  }

  async createComplaint(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/complaints/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Failed to create complaint');
    }

    return response.json();
  }

  async trackComplaint(tracking_number: string, phone: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/complaints/track`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tracking_number, phone }),
    });

    if (!response.ok) {
      throw new Error('Complaint not found');
    }

    return response.json();
  }

  async updateComplaint(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/complaints/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Failed to update complaint');
    }

    return response.json();
  }

  async getTasks(params?: { status?: string; area_id?: number }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status_filter', params.status);
    if (params?.area_id) queryParams.append('area_id', params.area_id.toString());

    const response = await fetch(`${API_BASE_URL}/tasks?${queryParams}`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch tasks');
    }

    return response.json();
  }

  async getTask(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch task');
    }

    return response.json();
  }

  async createTask(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/tasks/`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Failed to create task');
    }

    return response.json();
  }

  async updateTask(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Failed to update task');
    }

    return response.json();
  }

  async getContracts(params?: { status?: string }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status_filter', params.status);

    const response = await fetch(`${API_BASE_URL}/contracts?${queryParams}`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch contracts');
    }

    return response.json();
  }

  async getContract(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contracts/${id}`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch contract');
    }

    return response.json();
  }

  async createContract(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contracts/`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Failed to create contract');
    }

    return response.json();
  }

  async updateContract(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contracts/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Failed to update contract');
    }

    return response.json();
  }

  async approveContract(id: number, action: string, comments?: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/contracts/${id}/approve`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ action, comments }),
    });

    if (!response.ok) {
      throw new Error('Failed to approve contract');
    }

    return response.json();
  }

  async getDashboardStats(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/dashboard/stats`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch dashboard stats');
    }

    return response.json();
  }

  async getRecentActivity(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/dashboard/recent-activity`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch recent activity');
    }

    return response.json();
  }

  async getAreas(): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/locations/areas`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch areas');
    }

    return response.json();
  }

  async getUsers(): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/users`, {
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch users');
    return response.json();
  }

  async getUser(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/users/${id}`, {
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch user');
    return response.json();
  }

  async createUser(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/users/`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create user');
    return response.json();
  }

  async updateUser(id: number, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/users/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update user');
    return response.json();
  }

  async deleteUser(id: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/users/${id}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to delete user');
    return response.json();
  }

  async getReportsSummary(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/reports/summary`, {
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch reports');
    return response.json();
  }

  async getComplaintActivities(id: number): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/complaints/${id}/activities`, {
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch activities');
    return response.json();
  }

  async getTaskActivities(id: number): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}/activities`, {
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch activities');
    return response.json();
  }

  async getContractApprovals(id: number): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/contracts/${id}/approvals`, {
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch approvals');
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

  async getBuildings(areaId?: number): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (areaId) queryParams.append('area_id', areaId.toString());
    const response = await fetch(`${API_BASE_URL}/locations/buildings?${queryParams}`, {
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch buildings');
    return response.json();
  }

  async uploadFile(file: File, category: string): Promise<any> {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);
    const response = await fetch(`${API_BASE_URL}/uploads/?category=${category}`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to upload file');
    return response.json();
  }

  logout() {
    localStorage.removeItem('access_token');
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }
}

export const apiService = new ApiService();
