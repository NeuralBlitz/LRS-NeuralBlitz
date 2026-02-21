import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

import LoginScreen from '../screens/LoginScreen';
import DashboardScreen from '../screens/DashboardScreen';
import AgentControlScreen from '../screens/AgentControlScreen';
import NotificationsScreen from '../screens/NotificationsScreen';
import VoiceCommandScreen from '../screens/VoiceCommandScreen';
import AgentDetailScreen from '../screens/AgentDetailScreen';
import WorkflowScreen from '../screens/WorkflowScreen';
import SettingsScreen from '../screens/SettingsScreen';
import { useAuthStore } from '../store/authStore';
import { colors } from '../theme';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

const AgentStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="AgentList" 
      component={AgentControlScreen}
      options={{ title: 'Agents' }}
    />
    <Stack.Screen 
      name="AgentDetail" 
      component={AgentDetailScreen}
      options={{ title: 'Agent Detail' }}
    />
    <Stack.Screen 
      name="Workflow" 
      component={WorkflowScreen}
      options={{ title: 'Workflow' }}
    />
  </Stack.Navigator>
);

const TabNavigator = () => (
  <Tab.Navigator
    screenOptions={({ route }) => ({
      tabBarIcon: ({ focused, color, size }) => {
        let iconName: keyof typeof Ionicons.glyphMap;
        switch (route.name) {
          case 'Dashboard':
            iconName = focused ? 'home' : 'home-outline';
            break;
          case 'Agents':
            iconName = focused ? 'people' : 'people-outline';
            break;
          case 'Voice':
            iconName = focused ? 'mic' : 'mic-outline';
            break;
          case 'Notifications':
            iconName = focused ? 'notifications' : 'notifications-outline';
            break;
          case 'Settings':
            iconName = focused ? 'settings' : 'settings-outline';
            break;
          default:
            iconName = 'help-outline';
        }
        return <Ionicons name={iconName} size={size} color={color} />;
      },
      tabBarActiveTintColor: colors.primary,
      tabBarInactiveTintColor: colors.gray,
      headerShown: false,
    })}
  >
    <Tab.Screen name="Dashboard" component={DashboardScreen} />
    <Tab.Screen name="Agents" component={AgentStack} />
    <Tab.Screen name="Voice" component={VoiceCommandScreen} />
    <Tab.Screen name="Notifications" component={NotificationsScreen} />
    <Tab.Screen name="Settings" component={SettingsScreen} />
  </Tab.Navigator>
);

const AppNavigator = () => {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!isAuthenticated ? (
        <Stack.Screen name="Login" component={LoginScreen} />
      ) : (
        <Stack.Screen name="Main" component={TabNavigator} />
      )}
    </Stack.Navigator>
  );
};

export default AppNavigator;