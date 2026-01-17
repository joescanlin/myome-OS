import axios, { AxiosInstance } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/api/v1`,
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000,
    });

    this.client.interceptors.request.use(async (config) => {
      if (!this.accessToken) {
        this.accessToken = await AsyncStorage.getItem('access_token');
      }
      if (this.accessToken) {
        config.headers.Authorization = `Bearer ${this.accessToken}`;
      }
      return config;
    });
  }

  async setTokens(accessToken: string, refreshToken: string) {
    this.accessToken = accessToken;
    await AsyncStorage.setItem('access_token', accessToken);
    await AsyncStorage.setItem('refresh_token', refreshToken);
  }

  async clearTokens() {
    this.accessToken = null;
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('refresh_token');
  }

  // Auth
  async login(email: string, password: string) {
    const response = await this.client.post('/auth/login', { email, password });
    await this.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  }

  async register(email: string, password: string, firstName?: string, lastName?: string) {
    const response = await this.client.post('/auth/register', {
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    });
    await this.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  }

  // User
  async getCurrentUser() {
    const response = await this.client.get('/users/me');
    return response.data;
  }

  // Health Data
  async getHealthScore() {
    const response = await this.client.get('/health/analytics/score');
    return response.data;
  }

  async getDailyAnalysis(date?: string) {
    const params = date ? `?date=${date}` : '';
    const response = await this.client.get(`/health/analytics/daily${params}`);
    return response.data;
  }

  async getHeartRate(start?: string, end?: string) {
    const params = new URLSearchParams();
    if (start) params.append('start', start);
    if (end) params.append('end', end);
    const response = await this.client.get(`/health/heart-rate?${params}`);
    return response.data;
  }

  async getSleep(days = 7) {
    const response = await this.client.get(`/health/sleep?limit=${days}`);
    return response.data;
  }

  // Alerts
  async getAlerts() {
    const response = await this.client.get('/alerts/?status=active');
    return response.data;
  }

  async acknowledgeAlert(alertId: string) {
    const response = await this.client.post(`/alerts/${alertId}/acknowledge`);
    return response.data;
  }
}

export const api = new ApiClient();
