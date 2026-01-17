import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import { subDays, format } from 'date-fns';
import { api } from '../services/api';

export function HealthScreen() {
  const { data: heartRateData, refetch: refetchHR, isRefetching: isRefetchingHR } = useQuery({
    queryKey: ['heartRate', '7d'],
    queryFn: async () => {
      const end = new Date().toISOString();
      const start = subDays(new Date(), 7).toISOString();
      return api.getHeartRate(start, end);
    },
  });

  const { data: sleepData, refetch: refetchSleep, isRefetching: isRefetchingSleep } = useQuery({
    queryKey: ['sleep', '7d'],
    queryFn: () => api.getSleep(7),
  });

  const isRefetching = isRefetchingHR || isRefetchingSleep;

  const handleRefresh = () => {
    refetchHR();
    refetchSleep();
  };

  const latestHR = heartRateData?.[0];
  const latestSleep = sleepData?.[0];

  const avgHR = heartRateData?.length
    ? Math.round(
        heartRateData.reduce((sum: number, r: any) => sum + r.heart_rate_bpm, 0) /
          heartRateData.length
      )
    : null;

  const avgSleepHours = sleepData?.length
    ? (
        sleepData.reduce((sum: number, s: any) => sum + s.total_sleep_minutes, 0) /
        sleepData.length /
        60
      ).toFixed(1)
    : null;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={handleRefresh} />
        }
      >
        <View style={styles.header}>
          <Text style={styles.title}>Health Data</Text>
          <Text style={styles.subtitle}>Last 7 days</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Heart Rate</Text>
          <View style={styles.metricRow}>
            <View style={styles.metric}>
              <Text style={styles.metricValue}>{latestHR?.heart_rate_bpm || '--'}</Text>
              <Text style={styles.metricLabel}>Latest (bpm)</Text>
            </View>
            <View style={styles.metric}>
              <Text style={styles.metricValue}>{avgHR || '--'}</Text>
              <Text style={styles.metricLabel}>7-day Avg</Text>
            </View>
          </View>
          {heartRateData && (
            <Text style={styles.dataCount}>
              {heartRateData.length} readings this week
            </Text>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Sleep</Text>
          <View style={styles.metricRow}>
            <View style={styles.metric}>
              <Text style={styles.metricValue}>
                {latestSleep
                  ? `${Math.floor(latestSleep.total_sleep_minutes / 60)}h ${
                      latestSleep.total_sleep_minutes % 60
                    }m`
                  : '--'}
              </Text>
              <Text style={styles.metricLabel}>Last Night</Text>
            </View>
            <View style={styles.metric}>
              <Text style={styles.metricValue}>{avgSleepHours || '--'}h</Text>
              <Text style={styles.metricLabel}>7-day Avg</Text>
            </View>
          </View>
          {latestSleep && (
            <View style={styles.sleepBreakdown}>
              <View style={styles.sleepItem}>
                <Text style={styles.sleepLabel}>Deep</Text>
                <Text style={styles.sleepValue}>
                  {latestSleep.deep_sleep_minutes || 0}m
                </Text>
              </View>
              <View style={styles.sleepItem}>
                <Text style={styles.sleepLabel}>REM</Text>
                <Text style={styles.sleepValue}>
                  {latestSleep.rem_sleep_minutes || 0}m
                </Text>
              </View>
              <View style={styles.sleepItem}>
                <Text style={styles.sleepLabel}>Light</Text>
                <Text style={styles.sleepValue}>
                  {latestSleep.light_sleep_minutes || 0}m
                </Text>
              </View>
            </View>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Recent Activity</Text>
          <Text style={styles.placeholder}>Activity tracking coming soon</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  header: {
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1F2937',
  },
  subtitle: {
    fontSize: 16,
    color: '#6B7280',
    marginTop: 4,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    marginHorizontal: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 16,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  metric: {
    alignItems: 'center',
  },
  metricValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#E74C3C',
  },
  metricLabel: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  dataCount: {
    fontSize: 12,
    color: '#9CA3AF',
    textAlign: 'center',
    marginTop: 12,
  },
  sleepBreakdown: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  sleepItem: {
    alignItems: 'center',
  },
  sleepLabel: {
    fontSize: 12,
    color: '#6B7280',
  },
  sleepValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginTop: 4,
  },
  placeholder: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
    paddingVertical: 20,
  },
});
