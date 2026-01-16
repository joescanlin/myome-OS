import { create } from 'zustand';
import { api } from '../services/api';

interface HealthScore {
  score: number | null;
  components: Record<string, number>;
}

interface Alert {
  id: string;
  title: string;
  message: string;
  priority: string;
  status: string;
  biomarker: string;
  value: number;
  created_at: string;
}

interface Trend {
  biomarker: string;
  direction: string;
  percent_change: number;
  is_significant: boolean;
}

interface Correlation {
  biomarker_1: string;
  biomarker_2: string;
  correlation: number;
  lag_days: number;
  is_significant: boolean;
}

interface HealthState {
  healthScore: HealthScore | null;
  alerts: Alert[];
  trends: Trend[];
  correlations: Correlation[];
  isLoading: boolean;
  
  fetchHealthScore: () => Promise<void>;
  fetchAlerts: () => Promise<void>;
  fetchTrends: (days?: number) => Promise<void>;
  fetchCorrelations: (days?: number) => Promise<void>;
  acknowledgeAlert: (alertId: string) => Promise<void>;
}

export const useHealthStore = create<HealthState>((set, get) => ({
  healthScore: null,
  alerts: [],
  trends: [],
  correlations: [],
  isLoading: false,

  fetchHealthScore: async () => {
    set({ isLoading: true });
    try {
      const score = await api.getHealthScore();
      set({ healthScore: score, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
    }
  },

  fetchAlerts: async () => {
    try {
      const alerts = await api.getAlerts('active');
      set({ alerts });
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    }
  },

  fetchTrends: async (days = 30) => {
    try {
      const trends = await api.getTrends(days);
      set({ trends });
    } catch (error) {
      console.error('Failed to fetch trends:', error);
    }
  },

  fetchCorrelations: async (days = 30) => {
    try {
      const correlations = await api.getCorrelations(days);
      set({ correlations });
    } catch (error) {
      console.error('Failed to fetch correlations:', error);
    }
  },

  acknowledgeAlert: async (alertId: string) => {
    try {
      await api.acknowledgeAlert(alertId);
      const alerts = get().alerts.filter((a) => a.id !== alertId);
      set({ alerts });
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  },
}));
