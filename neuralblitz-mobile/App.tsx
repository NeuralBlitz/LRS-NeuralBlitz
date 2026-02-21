import React, { useEffect, useCallback } from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { Provider as PaperProvider, DefaultTheme } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import AppNavigator from './src/navigation/AppNavigator';
import { useAuthStore } from './src/store/authStore';
import { useNotificationStore } from './src/store/notificationStore';
import { useVoiceStore } from './src/store/voiceStore';
import NotificationService from './src/services/NotificationService';
import VoiceService from './src/services/VoiceService';
import { colors, typography, spacing } from './src/theme';

const theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: colors.primary,
    accent: colors.secondary,
    background: colors.background,
    surface: colors.surface,
    text: colors.text,
    error: colors.error,
  },
  fonts: {
    ...DefaultTheme.fonts,
    regular: { fontFamily: typography.regular },
    medium: { fontFamily: typography.medium },
    light: { fontFamily: typography.light },
    thin: { fontFamily: typography.thin },
  },
};

export default function App() {
  const initializeAuth = useAuthStore(state => state.initialize);
  const initializeNotifications = useNotificationStore(state => state.initialize);
  const initializeVoice = useVoiceStore(state => state.initialize);

  useEffect(() => {
    const setup = async () => {
      try {
        await initializeAuth();
        await NotificationService.initialize();
        await VoiceService.initialize();
        await initializeNotifications();
        await initializeVoice();
      } catch (error) {
        console.error('Initialization error:', error);
      }
    };
    setup();
  }, [initializeAuth, initializeNotifications, initializeVoice]);

  return (
    <SafeAreaProvider>
      <PaperProvider theme={theme}>
        <NavigationContainer>
          <AppNavigator />
          <StatusBar style="auto" />
        </NavigationContainer>
      </PaperProvider>
    </SafeAreaProvider>
  );
}