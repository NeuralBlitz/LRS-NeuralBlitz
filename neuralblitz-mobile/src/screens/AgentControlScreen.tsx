import React, { useEffect, useState, useCallback } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, Alert } from 'react-native';
import { 
  Card, 
  Title, 
  Paragraph, 
  Button, 
  FAB, 
  ActivityIndicator,
  Chip,
  Searchbar,
  Avatar,
  IconButton,
  Menu,
  Divider,
  Portal,
  Dialog,
  TextInput
} from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import { useAgentStore, Agent, AgentType, AgentStatus } from '../store/agentStore';
import { useAuthStore } from '../store/authStore';
import { colors, spacing, typography } from '../theme';

const AgentCard: React.FC<{ 
  agent: Agent; 
  onPress: () => void;
  onToggleStatus: () => void;
  onDelete: () => void;
}> = ({ agent, onPress, onToggleStatus, onDelete }) => {
  const [menuVisible, setMenuVisible] = useState(false);

  const getStatusColor = (status: AgentStatus) => {
    switch (status) {
      case 'active': return colors.success;
      case 'idle': return colors.warning;
      case 'error': return colors.error;
      case 'paused': return colors.gray;
      default: return colors.gray;
    }
  };

  const getAgentIcon = (type: AgentType) => {
    switch (type) {
      case 'cognitive': return 'brain';
      case 'analysis': return 'chart-line';
      case 'coordination': return 'users';
      case 'execution': return 'play-circle';
      default: return 'robot';
    }
  };

  return (
    <Card style={styles.card} onPress={onPress}>
      <Card.Content>
        <View style={styles.cardHeader}>
          <Avatar.Icon 
            size={50} 
            icon={getAgentIcon(agent.type)} 
            style={{ backgroundColor: colors.primary }}
          />
          <View style={styles.headerContent}>
            <Title style={styles.agentName}>{agent.name}</Title>
            <Paragraph style={styles.agentId}>ID: {agent.id}</Paragraph>
          </View>
          <Chip 
            style={[styles.statusChip, { backgroundColor: getStatusColor(agent.status) + '20' }]}
            textStyle={{ color: getStatusColor(agent.status) }}
          >
            {agent.status.toUpperCase()}
          </Chip>
        </View>
        
        <View style={styles.statsRow}>
          <View style={styles.stat}>
            <Paragraph style={styles.statLabel}>Type</Paragraph>
            <Paragraph style={styles.statValue}>{agent.type}</Paragraph>
          </View>
          <View style={styles.stat}>
            <Paragraph style={styles.statLabel}>Success Rate</Paragraph>
            <Paragraph style={styles.statValue}>{(agent.successRate * 100).toFixed(1)}%</Paragraph>
          </View>
          <View style={styles.stat}>
            <Paragraph style={styles.statLabel}>Tasks</Paragraph>
            <Paragraph style={styles.statValue}>{agent.completedTasks}</Paragraph>
          </View>
        </View>

        {agent.currentTask && (
          <View style={styles.currentTask}>
            <Chip icon="clock-outline" style={styles.taskChip}>
              {agent.currentTask}
            </Chip>
          </View>
        )}
      </Card.Content>
      
      <Card.Actions style={styles.cardActions}>
        <Button 
          mode="outlined" 
          onPress={onToggleStatus}
          icon={agent.status === 'active' ? 'pause' : 'play'}
        >
          {agent.status === 'active' ? 'Pause' : 'Activate'}
        </Button>
        <Menu
          visible={menuVisible}
          onDismiss={() => setMenuVisible(false)}
          anchor={
            <IconButton 
              icon="dots-vertical" 
              onPress={() => setMenuVisible(true)}
            />
          }
        >
          <Menu.Item onPress={onPress} title="View Details" leadingIcon="eye" />
          <Menu.Item onPress={() => {}} title="Edit Configuration" leadingIcon="pencil" />
          <Menu.Item onPress={() => {}} title="View Logs" leadingIcon="file-document" />
          <Divider />
          <Menu.Item onPress={onDelete} title="Delete Agent" leadingIcon="delete" titleStyle={{ color: colors.error }} />
        </Menu>
      </Card.Actions>
    </Card>
  );
};

const AgentControlScreen: React.FC = () => {
  const navigation = useNavigation();
  const { agents, loading, error, fetchAgents, toggleAgentStatus, deleteAgent, createAgent } = useAgentStore();
  const token = useAuthStore(state => state.token);
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [createDialogVisible, setCreateDialogVisible] = useState(false);
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentType, setNewAgentType] = useState<AgentType>('cognitive');

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = useCallback(async () => {
    try {
      await fetchAgents();
    } catch (err) {
      Alert.alert('Error', 'Failed to load agents');
    }
  }, [fetchAgents]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadAgents();
    setRefreshing(false);
  }, [loadAgents]);

  const handleToggleStatus = useCallback(async (agentId: string) => {
    try {
      await toggleAgentStatus(agentId);
    } catch (err) {
      Alert.alert('Error', 'Failed to toggle agent status');
    }
  }, [toggleAgentStatus]);

  const handleDelete = useCallback((agentId: string, agentName: string) => {
    Alert.alert(
      'Delete Agent',
      `Are you sure you want to delete agent "${agentName}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Delete', 
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteAgent(agentId);
            } catch (err) {
              Alert.alert('Error', 'Failed to delete agent');
            }
          }
        }
      ]
    );
  }, [deleteAgent]);

  const handleCreateAgent = useCallback(async () => {
    if (!newAgentName.trim()) {
      Alert.alert('Error', 'Agent name is required');
      return;
    }
    try {
      await createAgent({ name: newAgentName, type: newAgentType });
      setCreateDialogVisible(false);
      setNewAgentName('');
      Alert.alert('Success', 'Agent created successfully');
    } catch (err) {
      Alert.alert('Error', 'Failed to create agent');
    }
  }, [createAgent, newAgentName, newAgentType]);

  const filteredAgents = agents.filter(agent => 
    agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    agent.type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const renderAgent = useCallback(({ item }: { item: Agent }) => (
    <AgentCard
      agent={item}
      onPress={() => navigation.navigate('AgentDetail', { agentId: item.id })}
      onToggleStatus={() => handleToggleStatus(item.id)}
      onDelete={() => handleDelete(item.id, item.name)}
    />
  ), [navigation, handleToggleStatus, handleDelete]);

  if (loading && !refreshing && agents.length === 0) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Paragraph style={styles.loadingText}>Loading agents...</Paragraph>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="auto" />
      
      <Searchbar
        placeholder="Search agents..."
        onChangeText={setSearchQuery}
        value={searchQuery}
        style={styles.searchBar}
      />

      <View style={styles.statsContainer}>
        <Card style={styles.statCard}>
          <Card.Content>
            <Title style={styles.statNumber}>{agents.length}</Title>
            <Paragraph>Total Agents</Paragraph>
          </Card.Content>
        </Card>
        <Card style={styles.statCard}>
          <Card.Content>
            <Title style={[styles.statNumber, { color: colors.success }]}>
              {agents.filter(a => a.status === 'active').length}
            </Title>
            <Paragraph>Active</Paragraph>
          </Card.Content>
        </Card>
        <Card style={styles.statCard}>
          <Card.Content>
            <Title style={[styles.statNumber, { color: colors.warning }]}>
              {agents.filter(a => a.status === 'idle').length}
            </Title>
            <Paragraph>Idle</Paragraph>
          </Card.Content>
        </Card>
      </View>

      <FlatList
        data={filteredAgents}
        renderItem={renderAgent}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Paragraph style={styles.emptyText}>
              {searchQuery ? 'No agents match your search' : 'No agents found'}
            </Paragraph>
          </View>
        }
      />

      <FAB
        style={styles.fab}
        icon="plus"
        onPress={() => setCreateDialogVisible(true)}
        label="Create Agent"
      />

      <Portal>
        <Dialog visible={createDialogVisible} onDismiss={() => setCreateDialogVisible(false)}>
          <Dialog.Title>Create New Agent</Dialog.Title>
          <Dialog.Content>
            <TextInput
              label="Agent Name"
              value={newAgentName}
              onChangeText={setNewAgentName}
              mode="outlined"
              style={styles.input}
            />
            <Title style={styles.typeLabel}>Agent Type</Title>
            <View style={styles.typeContainer}>
              {(['cognitive', 'analysis', 'coordination', 'execution'] as AgentType[]).map((type) => (
                <Chip
                  key={type}
                  selected={newAgentType === type}
                  onPress={() => setNewAgentType(type)}
                  style={styles.typeChip}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </Chip>
              ))}
            </View>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setCreateDialogVisible(false)}>Cancel</Button>
            <Button onPress={handleCreateAgent} mode="contained">Create</Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  searchBar: {
    margin: spacing.medium,
    elevation: 2,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: spacing.small,
    marginBottom: spacing.small,
  },
  statCard: {
    flex: 1,
    marginHorizontal: spacing.xsmall,
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  listContainer: {
    padding: spacing.medium,
    paddingBottom: 100,
  },
  card: {
    marginBottom: spacing.medium,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.small,
  },
  headerContent: {
    flex: 1,
    marginLeft: spacing.medium,
  },
  agentName: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  agentId: {
    fontSize: 12,
    color: colors.gray,
  },
  statusChip: {
    marginLeft: spacing.small,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginVertical: spacing.small,
    paddingVertical: spacing.small,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.lightGray,
  },
  stat: {
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 12,
    color: colors.gray,
  },
  statValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  currentTask: {
    marginTop: spacing.small,
  },
  taskChip: {
    alignSelf: 'flex-start',
  },
  cardActions: {
    justifyContent: 'space-between',
    paddingHorizontal: spacing.small,
  },
  fab: {
    position: 'absolute',
    margin: spacing.medium,
    right: 0,
    bottom: 0,
    backgroundColor: colors.primary,
  },
  loadingText: {
    marginTop: spacing.medium,
    color: colors.gray,
  },
  emptyContainer: {
    padding: spacing.xlarge,
    alignItems: 'center',
  },
  emptyText: {
    color: colors.gray,
    fontSize: 16,
  },
  input: {
    marginBottom: spacing.medium,
  },
  typeLabel: {
    fontSize: 14,
    marginBottom: spacing.small,
  },
  typeContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  typeChip: {
    margin: spacing.xsmall,
  },
});

export default AgentControlScreen;