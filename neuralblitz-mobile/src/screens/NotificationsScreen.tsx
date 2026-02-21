import React, { useEffect, useCallback, useState } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, Alert } from 'react-native';
import { 
  Card, 
  Title, 
  Paragraph, 
  Button, 
  Chip,
  IconButton,
  Badge,
  Divider,
  Menu,
  List,
  Switch,
  Text
} from 'react-native-paper';
import { StatusBar } from 'expo-status-bar';
import { useNotificationStore, Notification, NotificationType } from '../store/notificationStore';
import NotificationService from '../services/NotificationService';
import { colors, spacing, typography } from '../theme';

const NotificationItem: React.FC<{
  notification: Notification;
  onPress: () => void;
  onDismiss: () => void;
  onMarkRead: () => void;
}> = ({ notification, onPress, onDismiss, onMarkRead }) => {
  const [menuVisible, setMenuVisible] = useState(false);

  const getNotificationIcon = (type: NotificationType) => {
    switch (type) {
      case 'info': return 'information';
      case 'success': return 'check-circle';
      case 'warning': return 'alert';
      case 'error': return 'alert-circle';
      case 'agent': return 'robot';
      case 'workflow': return 'sitemap';
      case 'system': return 'cog';
      default: return 'bell';
    }
  };

  const getNotificationColor = (type: NotificationType) => {
    switch (type) {
      case 'success': return colors.success;
      case 'error': return colors.error;
      case 'warning': return colors.warning;
      case 'info': return colors.info;
      default: return colors.primary;
    }
  };

  return (
    <Card 
      style={[
        styles.notificationCard,
        !notification.read && styles.unreadCard
      ]}
      onPress={onPress}
    >
      <Card.Content>
        <View style={styles.notificationHeader}>
          <View style={styles.iconContainer}>
            <IconButton
              icon={getNotificationIcon(notification.type)}
              size={28}
              iconColor={getNotificationColor(notification.type)}
              style={styles.notificationIcon}
            />
            {!notification.read && (
              <Badge style={styles.unreadBadge} size={12} />
            )}
          </View>
          
          <View style={styles.notificationContent}>
            <View style={styles.titleRow}>
              <Title style={styles.notificationTitle} numberOfLines={1}>
                {notification.title}
              </Title>
              <Menu
                visible={menuVisible}
                onDismiss={() => setMenuVisible(false)}
                anchor={
                  <IconButton
                    icon="dots-vertical"
                    size={20}
                    onPress={() => setMenuVisible(true)}
                  />
                }
              >
                {!notification.read && (
                  <Menu.Item 
                    onPress={() => { onMarkRead(); setMenuVisible(false); }} 
                    title="Mark as Read" 
                    leadingIcon="eye-check"
                  />
                )}
                <Menu.Item 
                  onPress={() => { onDismiss(); setMenuVisible(false); }} 
                  title="Dismiss" 
                  leadingIcon="close"
                />
              </Menu>
            </View>
            
            <Paragraph style={styles.notificationBody} numberOfLines={2}>
              {notification.body}
            </Paragraph>
            
            <View style={styles.notificationFooter}>
              <Chip 
                style={styles.typeChip} 
                textStyle={{ color: getNotificationColor(notification.type) }}
              >
                {notification.type}
              </Chip>
              <Text style={styles.timestamp}>
                {new Date(notification.timestamp).toLocaleTimeString()}
              </Text>
            </View>
          </View>
        </View>

        {notification.data && (
          <View style={styles.dataContainer}>
            <Divider style={styles.divider} />
            <Text style={styles.dataLabel}>Additional Data:</Text>
            <Text style={styles.dataText}>
              {JSON.stringify(notification.data, null, 2).substring(0, 200)}
            </Text>
          </View>
        )}
      </Card.Content>
    </Card>
  );
};

const NotificationsScreen: React.FC = () => {
  const {
    notifications,
    unreadCount,
    loading,
    error,
    pushEnabled,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    dismissNotification,
    clearAll,
    setPushEnabled,
    subscribeToTopics,
    unsubscribeFromTopics
  } = useNotificationStore();

  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<NotificationType | 'all'>('all');

  useEffect(() => {
    loadNotifications();
    setupPushNotifications();
  }, []);

  const loadNotifications = useCallback(async () => {
    try {
      await fetchNotifications();
    } catch (err) {
      console.error('Failed to load notifications:', err);
    }
  }, [fetchNotifications]);

  const setupPushNotifications = useCallback(async () => {
    try {
      const enabled = await NotificationService.requestPermissions();
      if (enabled) {
        await subscribeToTopics(['agent_updates', 'system_alerts', 'workflow_status']);
      }
    } catch (err) {
      console.error('Failed to setup push notifications:', err);
    }
  }, [subscribeToTopics]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadNotifications();
    setRefreshing(false);
  }, [loadNotifications]);

  const handleMarkAsRead = useCallback((id: string) => {
    markAsRead(id);
  }, [markAsRead]);

  const handleDismiss = useCallback((id: string) => {
    Alert.alert(
      'Dismiss Notification',
      'Are you sure you want to dismiss this notification?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Dismiss', 
          style: 'destructive',
          onPress: () => dismissNotification(id)
        }
      ]
    );
  }, [dismissNotification]);

  const handleClearAll = useCallback(() => {
    Alert.alert(
      'Clear All Notifications',
      'Are you sure you want to clear all notifications?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Clear All', 
          style: 'destructive',
          onPress: () => clearAll()
        }
      ]
    );
  }, [clearAll]);

  const togglePushNotifications = useCallback(async () => {
    try {
      if (!pushEnabled) {
        const granted = await NotificationService.requestPermissions();
        if (granted) {
          setPushEnabled(true);
          await subscribeToTopics(['agent_updates', 'system_alerts', 'workflow_status']);
        } else {
          Alert.alert('Permission Required', 'Please enable notifications in settings');
        }
      } else {
        setPushEnabled(false);
        await unsubscribeFromTopics(['agent_updates', 'system_alerts', 'workflow_status']);
      }
    } catch (err) {
      console.error('Failed to toggle notifications:', err);
    }
  }, [pushEnabled, setPushEnabled, subscribeToTopics, unsubscribeFromTopics]);

  const filteredNotifications = notifications.filter(notification => 
    filter === 'all' || notification.type === filter
  );

  const renderNotification = useCallback(({ item }: { item: Notification }) => (
    <NotificationItem
      notification={item}
      onPress={() => handleMarkAsRead(item.id)}
      onDismiss={() => handleDismiss(item.id)}
      onMarkRead={() => handleMarkAsRead(item.id)}
    />
  ), [handleMarkAsRead, handleDismiss]);

  const filterOptions: { label: string; value: NotificationType | 'all' }[] = [
    { label: 'All', value: 'all' },
    { label: 'Info', value: 'info' },
    { label: 'Success', value: 'success' },
    { label: 'Warning', value: 'warning' },
    { label: 'Error', value: 'error' },
    { label: 'Agent', value: 'agent' },
    { label: 'System', value: 'system' },
  ];

  return (
    <View style={styles.container}>
      <StatusBar style="auto" />
      
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <View>
            <Title style={styles.headerTitle}>Notifications</Title>
            <Paragraph style={styles.headerSubtitle}>
              {unreadCount} unread notification{unreadCount !== 1 ? 's' : ''}
            </Paragraph>
          </View>
          <View style={styles.headerActions}>
            <IconButton
              icon="check-all"
              size={24}
              onPress={markAllAsRead}
              disabled={unreadCount === 0}
            />
            <IconButton
              icon="delete-sweep"
              size={24}
              onPress={handleClearAll}
              disabled={notifications.length === 0}
            />
          </View>
        </View>

        <View style={styles.settingsRow}>
          <View style={styles.pushToggle}>
            <Text>Push Notifications</Text>
            <Switch
              value={pushEnabled}
              onValueChange={togglePushNotifications}
            />
          </View>
        </View>
      </View>

      <View style={styles.filterContainer}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {filterOptions.map((option) => (
            <Chip
              key={option.value}
              selected={filter === option.value}
              onPress={() => setFilter(option.value)}
              style={styles.filterChip}
              selectedColor={colors.primary}
            >
              {option.label}
            </Chip>
          ))}
        </ScrollView>
      </View>

      {loading && !refreshing && notifications.length === 0 ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Paragraph style={styles.loadingText}>Loading notifications...</Paragraph>
        </View>
      ) : (
        <FlatList
          data={filteredNotifications}
          renderItem={renderNotification}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContainer}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <IconButton icon="bell-off" size={64} iconColor={colors.gray} />
              <Title style={styles.emptyTitle}>No Notifications</Title>
              <Paragraph style={styles.emptyText}>
                {filter === 'all' 
                  ? "You're all caught up!" 
                  : `No ${filter} notifications found`}
              </Paragraph>
            </View>
          }
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    padding: spacing.medium,
    backgroundColor: colors.surface,
    elevation: 2,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  headerSubtitle: {
    color: colors.gray,
    marginTop: spacing.xsmall,
  },
  headerActions: {
    flexDirection: 'row',
  },
  settingsRow: {
    marginTop: spacing.medium,
    paddingTop: spacing.medium,
    borderTopWidth: 1,
    borderTopColor: colors.lightGray,
  },
  pushToggle: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  filterContainer: {
    paddingVertical: spacing.medium,
    paddingHorizontal: spacing.small,
    backgroundColor: colors.background,
  },
  filterChip: {
    marginHorizontal: spacing.xsmall,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: spacing.medium,
    color: colors.gray,
  },
  listContainer: {
    padding: spacing.medium,
    paddingBottom: 100,
  },
  notificationCard: {
    marginBottom: spacing.medium,
    elevation: 1,
  },
  unreadCard: {
    backgroundColor: colors.surface,
    borderLeftWidth: 4,
    borderLeftColor: colors.primary,
  },
  notificationHeader: {
    flexDirection: 'row',
  },
  iconContainer: {
    position: 'relative',
    marginRight: spacing.small,
  },
  notificationIcon: {
    margin: 0,
  },
  unreadBadge: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: colors.primary,
  },
  notificationContent: {
    flex: 1,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  notificationTitle: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
  },
  notificationBody: {
    fontSize: 14,
    color: colors.text,
    marginTop: spacing.xsmall,
  },
  notificationFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.small,
  },
  typeChip: {
    alignSelf: 'flex-start',
  },
  timestamp: {
    fontSize: 12,
    color: colors.gray,
  },
  dataContainer: {
    marginTop: spacing.small,
  },
  divider: {
    marginVertical: spacing.small,
  },
  dataLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.gray,
    marginBottom: spacing.xsmall,
  },
  dataText: {
    fontSize: 12,
    color: colors.gray,
    fontFamily: 'monospace',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xlarge,
  },
  emptyTitle: {
    marginTop: spacing.medium,
    color: colors.gray,
  },
  emptyText: {
    textAlign: 'center',
    color: colors.gray,
    marginTop: spacing.small,
  },
});

export default NotificationsScreen;