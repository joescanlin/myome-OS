import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { api } from '../services/api';

export function AlertsScreen() {
  const queryClient = useQueryClient();

  const { data: alerts, refetch, isRefetching } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.getAlerts(),
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (alertId: string) => api.acknowledgeAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
    onError: (error: any) => {
      Alert.alert('Error', error.message || 'Failed to acknowledge alert');
    },
  });

  const handleAcknowledge = (alertId: string, title: string) => {
    Alert.alert(
      'Acknowledge Alert',
      `Dismiss "${title}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Dismiss',
          onPress: () => acknowledgeMutation.mutate(alertId),
        },
      ]
    );
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return '#DC2626';
      case 'high':
        return '#EA580C';
      case 'medium':
        return '#D97706';
      default:
        return '#6B7280';
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} />
        }
      >
        <View style={styles.header}>
          <Text style={styles.title}>Alerts</Text>
          <Text style={styles.subtitle}>
            {alerts?.length || 0} active alert{alerts?.length !== 1 ? 's' : ''}
          </Text>
        </View>

        {alerts && alerts.length > 0 ? (
          alerts.map((alert: any) => (
            <TouchableOpacity
              key={alert.id}
              style={[
                styles.alertCard,
                { borderLeftColor: getPriorityColor(alert.priority) },
              ]}
              onPress={() => handleAcknowledge(alert.id, alert.title)}
            >
              <View style={styles.alertHeader}>
                <View
                  style={[
                    styles.priorityBadge,
                    { backgroundColor: getPriorityColor(alert.priority) },
                  ]}
                >
                  <Text style={styles.priorityText}>
                    {alert.priority?.toUpperCase()}
                  </Text>
                </View>
                <Text style={styles.alertTime}>
                  {alert.created_at
                    ? format(new Date(alert.created_at), 'MMM d, h:mm a')
                    : ''}
                </Text>
              </View>
              <Text style={styles.alertTitle}>{alert.title}</Text>
              <Text style={styles.alertMessage}>{alert.message}</Text>
              <Text style={styles.tapToDismiss}>Tap to dismiss</Text>
            </TouchableOpacity>
          ))
        ) : (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>✓</Text>
            <Text style={styles.emptyTitle}>All Clear</Text>
            <Text style={styles.emptyMessage}>
              No active alerts. Keep up the good work!
            </Text>
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
  alertCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 20,
    marginBottom: 12,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  alertHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  priorityText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '700',
  },
  alertTime: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  alertTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  alertMessage: {
    fontSize: 14,
    color: '#6B7280',
    lineHeight: 20,
  },
  tapToDismiss: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 12,
    textAlign: 'right',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    paddingHorizontal: 40,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 8,
  },
  emptyMessage: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
  },
});
