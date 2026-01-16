import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth
    this.client.interceptors.request.use((config) => {
      if (this.accessToken) {
        config.headers.Authorization = `Bearer ${this.accessToken}`;
      }
      return config;
    });

    // Response interceptor for errors
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Try to refresh token
          const refreshed = await this.refreshToken();
          if (refreshed && error.config) {
            return this.client.request(error.config);
          }
          // Redirect to login
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );

    // Load token from storage
    this.accessToken = localStorage.getItem('access_token');
  }

  setTokens(accessToken: string, refreshToken: string) {
    this.accessToken = accessToken;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  clearTokens() {
    this.accessToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  private async refreshToken(): Promise<boolean> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;

    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
        refresh_token: refreshToken,
      });
      this.setTokens(response.data.access_token, response.data.refresh_token);
      return true;
    } catch {
      this.clearTokens();
      return false;
    }
  }

  // Auth
  async register(email: string, password: string, firstName?: string, lastName?: string) {
    const response = await this.client.post('/auth/register', {
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    });
    this.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  }

  async login(email: string, password: string) {
    const response = await this.client.post('/auth/login', { email, password });
    this.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  }

  logout() {
    this.clearTokens();
  }

  // User
  async getCurrentUser() {
    const response = await this.client.get('/users/me');
    return response.data;
  }

  async updateUser(data: Record<string, unknown>) {
    const response = await this.client.patch('/users/me', data);
    return response.data;
  }

  // Health Data
  async getHeartRate(start?: string, end?: string, limit = 1000) {
    const params = new URLSearchParams();
    if (start) params.append('start', start);
    if (end) params.append('end', end);
    params.append('limit', limit.toString());
    
    const response = await this.client.get(`/health/heart-rate?${params}`);
    return response.data;
  }

  async getGlucose(start?: string, end?: string, limit = 1000) {
    const params = new URLSearchParams();
    if (start) params.append('start', start);
    if (end) params.append('end', end);
    params.append('limit', limit.toString());
    
    const response = await this.client.get(`/health/glucose?${params}`);
    return response.data;
  }

  async getSleep(start?: string, end?: string, limit = 30) {
    const params = new URLSearchParams();
    if (start) params.append('start', start);
    if (end) params.append('end', end);
    params.append('limit', limit.toString());
    
    const response = await this.client.get(`/health/sleep?${params}`);
    return response.data;
  }

  // Analytics
  async getDailyAnalysis(date?: string) {
    const params = date ? `?date=${date}` : '';
    const response = await this.client.get(`/health/analytics/daily${params}`);
    return response.data;
  }

  async getHealthScore(date?: string) {
    const params = date ? `?date=${date}` : '';
    const response = await this.client.get(`/health/analytics/score${params}`);
    return response.data;
  }

  async getCorrelations(days = 30) {
    const response = await this.client.get(`/health/analytics/correlations?days=${days}`);
    return response.data;
  }

  async getTrends(days = 30) {
    const response = await this.client.get(`/health/analytics/trends?days=${days}`);
    return response.data;
  }

  // Devices
  async getDevices() {
    const response = await this.client.get('/devices/');
    return response.data;
  }

  async addDevice(data: { name: string; device_type: string; vendor: string }) {
    const response = await this.client.post('/devices/', data);
    return response.data;
  }

  async syncDevice(deviceId: string, hoursBack = 24) {
    const response = await this.client.post(`/devices/${deviceId}/sync`, {
      hours_back: hoursBack,
    });
    return response.data;
  }

  // Alerts
  async getAlerts(status?: string) {
    const params = status ? `?status=${status}` : '';
    const response = await this.client.get(`/alerts/${params}`);
    return response.data;
  }

  async acknowledgeAlert(alertId: string) {
    const response = await this.client.post(`/alerts/${alertId}/acknowledge`);
    return response.data;
  }

  async resolveAlert(alertId: string) {
    const response = await this.client.post(`/alerts/${alertId}/resolve`);
    return response.data;
  }
}

export const api = new ApiClient();
