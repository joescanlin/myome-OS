import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { useAuthStore } from '../store/auth';

export function DashboardScreen() {
  const { user } = useAuthStore();
  
  const { data: healthScore, refetch, isRefetching } = useQuery({
    queryKey: ['healthScore'],
    queryFn: () => api.getHealthScore(),
  });

  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.getAlerts(),
  });

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} />
        }
      >
        <View style={styles.header}>
          <Text style={styles.greeting}>
            Hello, {user?.first_name || 'there'}
          </Text>
          <Text style={styles.subtitle}>Here's your health summary</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Health Score</Text>
          <View style={styles.scoreContainer}>
            <Text style={styles.scoreValue}>
              {healthScore?.score?.toFixed(0) || '--'}
            </Text>
            <Text style={styles.scoreLabel}>/ 100</Text>
          </View>
          
          {healthScore?.components && (
            <View style={styles.components}>
              {Object.entries(healthScore.components).map(([key, value]) => (
                <View key={key} style={styles.componentRow}>
                  <Text style={styles.componentLabel}>
                    {key.replace('_', ' ')}
                  </Text>
                  <Text style={styles.componentValue}>
                    {(value as number).toFixed(0)}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </View>

        {alerts && alerts.length > 0 && (
          <View style={[styles.card, styles.alertCard]}>
            <Text style={styles.cardTitle}>Active Alerts</Text>
            {alerts.slice(0, 3).map((alert: any) => (
              <TouchableOpacity key={alert.id} style={styles.alertItem}>
                <Text style={styles.alertTitle}>{alert.title}</Text>
                <Text style={styles.alertMessage}>{alert.message}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
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
  greeting: {
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
  alertCard: {
    borderLeftWidth: 4,
    borderLeftColor: '#E74C3C',
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 12,
  },
  scoreContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'center',
    marginVertical: 20,
  },
  scoreValue: {
    fontSize: 64,
    fontWeight: 'bold',
    color: '#E74C3C',
  },
  scoreLabel: {
    fontSize: 24,
    color: '#9CA3AF',
    marginLeft: 8,
  },
  components: {
    marginTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    paddingTop: 16,
  },
  componentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  componentLabel: {
    fontSize: 14,
    color: '#6B7280',
    textTransform: 'capitalize',
  },
  componentValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1F2937',
  },
  alertItem: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  alertTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#E74C3C',
  },
  alertMessage: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
});
