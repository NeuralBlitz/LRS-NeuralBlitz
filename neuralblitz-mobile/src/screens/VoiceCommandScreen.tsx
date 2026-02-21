import React, { useState, useEffect, useCallback, useRef } from 'react';
import { View, StyleSheet, ScrollView, Animated, Vibration } from 'react-native';
import { 
  Card, 
  Title, 
  Paragraph, 
  Button, 
  FAB, 
  ActivityIndicator,
  Chip,
  List,
  Divider,
  Banner,
  IconButton,
  Surface,
  Text
} from 'react-native-paper';
import { StatusBar } from 'expo-status-bar';
import VoiceService from '../services/VoiceService';
import ApiService from '../services/ApiService';
import { useVoiceStore, VoiceCommand, CommandType } from '../store/voiceStore';
import { useNotificationStore } from '../store/notificationStore';
import { colors, spacing, typography } from '../theme';
import * as Speech from 'expo-speech';

const WAVE_BARS = 5;

const VoiceWave: React.FC<{ isListening: boolean }> = ({ isListening }) => {
  const animations = useRef(
    Array(WAVE_BARS).fill(0).map(() => new Animated.Value(0))
  ).current;

  useEffect(() => {
    if (isListening) {
      animations.forEach((anim, index) => {
        Animated.loop(
          Animated.sequence([
            Animated.timing(anim, {
              toValue: 1,
              duration: 400 + index * 100,
              useNativeDriver: true,
            }),
            Animated.timing(anim, {
              toValue: 0,
              duration: 400 + index * 100,
              useNativeDriver: true,
            }),
          ])
        ).start();
      });
    } else {
      animations.forEach(anim => anim.setValue(0));
    }
  }, [isListening, animations]);

  return (
    <View style={styles.waveContainer}>
      {animations.map((anim, index) => (
        <Animated.View
          key={index}
          style={[
            styles.waveBar,
            {
              transform: [{
                scaleY: anim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.3, 1],
                })
              }],
              opacity: anim.interpolate({
                inputRange: [0, 1],
                outputRange: [0.3, 1],
              })
            }
          ]}
        />
      ))}
    </View>
  );
};

const CommandCard: React.FC<{ command: VoiceCommand; onExecute: () => void }> = ({ 
  command, 
  onExecute 
}) => {
  const getCommandIcon = (type: CommandType) => {
    switch (type) {
      case 'agent': return 'robot';
      case 'workflow': return 'sitemap';
      case 'analysis': return 'chart-bar';
      case 'status': return 'information';
      case 'control': return 'controller-classic';
      default: return 'microphone';
    }
  };

  const getStatusColor = (status: VoiceCommand['status']) => {
    switch (status) {
      case 'executed': return colors.success;
      case 'failed': return colors.error;
      case 'processing': return colors.primary;
      default: return colors.gray;
    }
  };

  return (
    <Card style={styles.commandCard}>
      <Card.Content>
        <View style={styles.commandHeader}>
          <View style={styles.commandInfo}>
            <Title style={styles.commandText}>{command.command}</Title>
            <Paragraph style={styles.timestamp}>
              {new Date(command.timestamp).toLocaleTimeString()}
            </Paragraph>
          </View>
          <IconButton
            icon={getCommandIcon(command.type)}
            size={24}
            iconColor={colors.primary}
          />
        </View>
        
        <View style={styles.commandDetails}>
          <Chip style={styles.typeChip}>
            {command.type}
          </Chip>
          <Chip 
            style={[styles.statusChip, { backgroundColor: getStatusColor(command.status) + '20' }]}
            textStyle={{ color: getStatusColor(command.status) }}
          >
            {command.status}
          </Chip>
        </View>

        {command.response && (
          <View style={styles.responseContainer}>
            <Divider style={styles.divider} />
            <Paragraph style={styles.responseText}>{command.response}</Paragraph>
          </View>
        )}

        {command.error && (
          <View style={styles.errorContainer}>
            <Divider style={styles.divider} />
            <Text style={styles.errorText}>{command.error}</Text>
          </View>
        )}
      </Card.Content>
      {command.status === 'pending' && (
        <Card.Actions>
          <Button mode="contained" onPress={onExecute} icon="play">
            Execute
          </Button>
          <Button mode="outlined" onPress={() => {}} icon="close">
            Cancel
          </Button>
        </Card.Actions>
      )}
    </Card>
  );
};

const VoiceCommandScreen: React.FC = () => {
  const [isListening, setIsListening] = useState(false);
  const [partialResults, setPartialResults] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  
  const { 
    commands, 
    addCommand, 
    updateCommand, 
    clearCommands,
    loading,
    isVoiceInitialized 
  } = useVoiceStore();
  const addNotification = useNotificationStore(state => state.addNotification);

  useEffect(() => {
    checkPermissions();
    setupVoiceListeners();
    return () => {
      VoiceService.destroy();
    };
  }, []);

  const checkPermissions = async () => {
    try {
      const granted = await VoiceService.requestPermissions();
      setHasPermission(granted);
      if (!granted) {
        setError('Microphone permission is required for voice commands');
      }
    } catch (err) {
      setError('Failed to check permissions');
    }
  };

  const setupVoiceListeners = () => {
    VoiceService.onSpeechStart = () => {
      setIsListening(true);
      setError(null);
      Vibration.vibrate(50);
    };

    VoiceService.onSpeechEnd = () => {
      setIsListening(false);
      setPartialResults([]);
    };

    VoiceService.onSpeechResults = (results: string[]) => {
      handleVoiceResults(results);
    };

    VoiceService.onSpeechPartialResults = (results: string[]) => {
      setPartialResults(results);
    };

    VoiceService.onSpeechError = (err: any) => {
      setIsListening(false);
      setError(err.message || 'Voice recognition error');
      Vibration.vibrate([0, 100, 50, 100]);
    };
  };

  const handleVoiceResults = async (results: string[]) => {
    if (results.length === 0) return;

    const commandText = results[0];
    const commandType = parseCommandType(commandText);
    
    const newCommand: VoiceCommand = {
      id: Date.now().toString(),
      command: commandText,
      type: commandType,
      status: 'pending',
      timestamp: new Date().toISOString(),
    };

    addCommand(newCommand);
    
    addNotification({
      id: `voice-${newCommand.id}`,
      title: 'Voice Command Received',
      body: commandText,
      type: 'info',
      timestamp: new Date().toISOString(),
      read: false,
    });

    Speech.speak(`Command received: ${commandText}`, {
      language: 'en',
      pitch: 1.0,
      rate: 0.9,
    });

    await executeCommand(newCommand);
  };

  const parseCommandType = (command: string): CommandType => {
    const lowerCmd = command.toLowerCase();
    if (lowerCmd.includes('agent') || lowerCmd.includes('create') || lowerCmd.includes('delete')) {
      return 'agent';
    }
    if (lowerCmd.includes('workflow') || lowerCmd.includes('execute') || lowerCmd.includes('run')) {
      return 'workflow';
    }
    if (lowerCmd.includes('analyze') || lowerCmd.includes('check') || lowerCmd.includes('review')) {
      return 'analysis';
    }
    if (lowerCmd.includes('status') || lowerCmd.includes('health') || lowerCmd.includes('metrics')) {
      return 'status';
    }
    return 'control';
  };

  const executeCommand = async (command: VoiceCommand) => {
    updateCommand(command.id, { status: 'processing' });

    try {
      let response: string;
      let success = true;

      switch (command.type) {
        case 'agent':
          const agentResult = await handleAgentCommand(command.command);
          response = agentResult.message;
          success = agentResult.success;
          break;
        
        case 'workflow':
          const workflowResult = await handleWorkflowCommand(command.command);
          response = workflowResult.message;
          success = workflowResult.success;
          break;
        
        case 'analysis':
          const analysisResult = await handleAnalysisCommand(command.command);
          response = analysisResult.message;
          success = analysisResult.success;
          break;
        
        case 'status':
          const statusResult = await handleStatusCommand(command.command);
          response = statusResult.message;
          success = statusResult.success;
          break;
        
        default:
          response = 'Command type not yet implemented';
          success = false;
      }

      updateCommand(command.id, { 
        status: success ? 'executed' : 'failed',
        response: success ? response : undefined,
        error: success ? undefined : response
      });

      Speech.speak(success ? response : `Command failed: ${response}`, {
        language: 'en',
        pitch: success ? 1.0 : 0.8,
        rate: 0.9,
      });

      addNotification({
        id: `voice-result-${command.id}`,
        title: success ? 'Command Executed' : 'Command Failed',
        body: response,
        type: success ? 'success' : 'error',
        timestamp: new Date().toISOString(),
        read: false,
      });

    } catch (err) {
      updateCommand(command.id, { 
        status: 'failed',
        error: 'Execution error occurred'
      });
    }
  };

  const handleAgentCommand = async (command: string): Promise<{ success: boolean; message: string }> => {
    try {
      const lowerCmd = command.toLowerCase();
      
      if (lowerCmd.includes('status') || lowerCmd.includes('list')) {
        const response = await ApiService.get('/api/multi-agent/status');
        const data = response.data;
        return {
          success: true,
          message: `You have ${data.active_agents} active agents and ${data.completed_tasks} completed tasks`
        };
      }
      
      if (lowerCmd.includes('create') || lowerCmd.includes('new')) {
        return {
          success: true,
          message: 'Agent creation initiated. Please use the agent control screen to configure details.'
        };
      }
      
      return { success: false, message: 'Agent command not recognized' };
    } catch (err) {
      return { success: false, message: 'Failed to execute agent command' };
    }
  };

  const handleWorkflowCommand = async (command: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await ApiService.post('/api/multi-agent/execute-workflow', {
        workflow_type: 'code_review_and_optimization',
        agents: ['lrs_agent', 'cognitive_agent'],
        coordination_strategy: 'hierarchical'
      });
      
      return {
        success: true,
        message: `Workflow ${response.data.workflow_id} started successfully`
      };
    } catch (err) {
      return { success: false, message: 'Failed to start workflow' };
    }
  };

  const handleAnalysisCommand = async (command: string): Promise<{ success: boolean; message: string }> => {
    return {
      success: true,
      message: 'Analysis command queued. Results will be available in the dashboard.'
    };
  };

  const handleStatusCommand = async (command: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await ApiService.get('/enterprise/monitoring/health');
      const data = response.data;
      return {
        success: true,
        message: `System is ${data.overall_health}. CPU at ${data.cpu_usage_percent}%, Memory at ${data.memory_usage_percent}%`
      };
    } catch (err) {
      return { success: false, message: 'Failed to retrieve system status' };
    }
  };

  const startListening = useCallback(async () => {
    try {
      setError(null);
      await VoiceService.startListening();
    } catch (err) {
      setError('Failed to start voice recognition');
    }
  }, []);

  const stopListening = useCallback(async () => {
    try {
      await VoiceService.stopListening();
      setIsListening(false);
    } catch (err) {
      console.error('Error stopping voice:', err);
    }
  }, []);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  if (hasPermission === false) {
    return (
      <View style={styles.container}>
        <Banner
          visible={true}
          icon="microphone-off"
          actions={[
            {
              label: 'Grant Permission',
              onPress: checkPermissions,
            },
          ]}
        >
          Microphone permission is required for voice commands
        </Banner>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="auto" />
      
      <Surface style={styles.header} elevation={2}>
        <Title style={styles.headerTitle}>Voice Commands</Title>
        <Paragraph style={styles.headerSubtitle}>
          Speak to control your NeuralBlitz agents
        </Paragraph>
      </Surface>

      <View style={styles.waveSection}>
        <VoiceWave isListening={isListening} />
        {isListening && partialResults.length > 0 && (
          <Text style={styles.partialText}>{partialResults[0]}</Text>
        )}
        {!isListening && !loading && (
          <Text style={styles.hintText}>
            Tap the microphone to start speaking
          </Text>
        )}
      </View>

      {error && (
        <Banner
          visible={true}
          icon="alert-circle"
          actions={[
            {
              label: 'Dismiss',
              onPress: () => setError(null),
            },
          ]}
          style={styles.errorBanner}
        >
          {error}
        </Banner>
      )}

      <View style={styles.commandsSection}>
        <View style={styles.commandsHeader}>
          <Title style={styles.sectionTitle}>Command History</Title>
          <Button 
            mode="text" 
            onPress={clearCommands}
            disabled={commands.length === 0}
          >
            Clear
          </Button>
        </View>

        <ScrollView style={styles.commandsList}>
          {commands.length === 0 ? (
            <View style={styles.emptyState}>
              <IconButton icon="microphone" size={48} iconColor={colors.gray} />
              <Paragraph style={styles.emptyText}>
                No voice commands yet. Tap the microphone to start.
              </Paragraph>
            </View>
          ) : (
            commands.map((command) => (
              <CommandCard
                key={command.id}
                command={command}
                onExecute={() => executeCommand(command)}
              />
            ))
          )}
        </ScrollView>
      </View>

      <View style={styles.quickCommands}>
        <Text style={styles.quickTitle}>Quick Commands</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <Chip 
            style={styles.quickChip} 
            icon="information"
            onPress={() => {}}
          >
            System Status
          </Chip>
          <Chip 
            style={styles.quickChip} 
            icon="robot"
            onPress={() => {}}
          >
            List Agents
          </Chip>
          <Chip 
            style={styles.quickChip} 
            icon="sitemap"
            onPress={() => {}}
          >
            Run Workflow
          </Chip>
          <Chip 
            style={styles.quickChip} 
            icon="chart-bar"
            onPress={() => {}}
          >
            Health Check
          </Chip>
        </ScrollView>
      </View>

      <FAB
        style={[
          styles.fab,
          isListening && { backgroundColor: colors.error }
        ]}
        icon={isListening ? 'stop' : 'microphone'}
        onPress={toggleListening}
        loading={loading}
        color={colors.white}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    padding: spacing.large,
    backgroundColor: colors.surface,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  headerSubtitle: {
    color: colors.gray,
    marginTop: spacing.xsmall,
  },
  waveSection: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xlarge,
    backgroundColor: colors.surface,
    marginBottom: spacing.medium,
  },
  waveContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 80,
    marginBottom: spacing.medium,
  },
  waveBar: {
    width: 8,
    height: 60,
    backgroundColor: colors.primary,
    marginHorizontal: 4,
    borderRadius: 4,
  },
  partialText: {
    fontSize: 18,
    color: colors.primary,
    textAlign: 'center',
    paddingHorizontal: spacing.large,
  },
  hintText: {
    fontSize: 16,
    color: colors.gray,
    textAlign: 'center',
  },
  errorBanner: {
    margin: spacing.medium,
  },
  commandsSection: {
    flex: 1,
    padding: spacing.medium,
  },
  commandsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.medium,
  },
  sectionTitle: {
    fontSize: 18,
  },
  commandsList: {
    flex: 1,
  },
  commandCard: {
    marginBottom: spacing.medium,
  },
  commandHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  commandInfo: {
    flex: 1,
  },
  commandText: {
    fontSize: 16,
  },
  timestamp: {
    fontSize: 12,
    color: colors.gray,
  },
  commandDetails: {
    flexDirection: 'row',
    marginTop: spacing.small,
  },
  typeChip: {
    marginRight: spacing.small,
  },
  statusChip: {
    marginRight: spacing.small,
  },
  divider: {
    marginVertical: spacing.small,
  },
  responseContainer: {
    marginTop: spacing.small,
  },
  responseText: {
    fontSize: 14,
    color: colors.text,
  },
  errorContainer: {
    marginTop: spacing.small,
  },
  errorText: {
    fontSize: 14,
    color: colors.error,
  },
  emptyState: {
    alignItems: 'center',
    padding: spacing.xlarge,
  },
  emptyText: {
    textAlign: 'center',
    color: colors.gray,
    marginTop: spacing.medium,
  },
  quickCommands: {
    padding: spacing.medium,
    backgroundColor: colors.surface,
  },
  quickTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: spacing.small,
  },
  quickChip: {
    marginRight: spacing.small,
    marginBottom: spacing.small,
  },
  fab: {
    position: 'absolute',
    margin: spacing.medium,
    right: 0,
    bottom: 100,
    backgroundColor: colors.primary,
  },
});

export default VoiceCommandScreen;