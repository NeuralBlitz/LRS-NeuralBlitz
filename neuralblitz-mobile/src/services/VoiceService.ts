import { NativeModules, NativeEventEmitter, Platform } from 'react-native';
import Voice from '@react-native-voice/voice';

class VoiceService {
  private static instance: VoiceService;
  private initialized = false;
  private listeners: { remove: () => void }[] = [];

  onSpeechStart: () => void = () => {};
  onSpeechEnd: () => void = () => {};
  onSpeechResults: (results: string[]) => void = () => {};
  onSpeechPartialResults: (results: string[]) => void = () => {};
  onSpeechError: (error: any) => void = () => {};

  static getInstance(): VoiceService {
    if (!VoiceService.instance) {
      VoiceService.instance = new VoiceService();
    }
    return VoiceService.instance;
  }

  async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      Voice.onSpeechStart = () => {
        this.onSpeechStart();
      };

      Voice.onSpeechEnd = () => {
        this.onSpeechEnd();
      };

      Voice.onSpeechResults = (e: any) => {
        this.onSpeechResults(e.value || []);
      };

      Voice.onSpeechPartialResults = (e: any) => {
        this.onSpeechPartialResults(e.value || []);
      };

      Voice.onSpeechError = (e: any) => {
        this.onSpeechError(e.error);
      };

      this.initialized = true;
    } catch (error) {
      console.error('Voice initialization error:', error);
      throw error;
    }
  }

  async requestPermissions(): Promise<boolean> {
    if (Platform.OS === 'android') {
      try {
        const PermissionsAndroid = NativeModules.PermissionsAndroid;
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
          {
            title: 'Microphone Permission',
            message: 'NeuralBlitz needs access to your microphone for voice commands',
            buttonNeutral: 'Ask Me Later',
            buttonNegative: 'Cancel',
            buttonPositive: 'OK'
          }
        );
        return granted === PermissionsAndroid.RESULTS.GRANTED;
      } catch (err) {
        console.error('Permission error:', err);
        return false;
      }
    }
    return true;
  }

  async startListening(): Promise<void> {
    try {
      await Voice.start('en-US');
    } catch (error) {
      console.error('Start listening error:', error);
      throw error;
    }
  }

  async stopListening(): Promise<void> {
    try {
      await Voice.stop();
    } catch (error) {
      console.error('Stop listening error:', error);
      throw error;
    }
  }

  async destroy(): Promise<void> {
    try {
      await Voice.destroy();
      this.listeners.forEach(listener => listener.remove());
      this.listeners = [];
      this.initialized = false;
    } catch (error) {
      console.error('Destroy error:', error);
    }
  }

  isAvailable(): boolean {
    return this.initialized;
  }
}

export default VoiceService.getInstance();