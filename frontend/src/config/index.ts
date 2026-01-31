/**
 * Application Configuration
 * Centralized configuration management for the LabOS AI frontend
 */

interface AppConfig {
  // Environment
  isDevelopment: boolean;
  isProduction: boolean;
  
  // API Configuration
  api: {
    baseUrl: string;
    timeout: number;
  };
  
  // WebSocket Configuration
  websocket: {
    url: string;
    reconnectAttempts: number;
    reconnectDelay: number;
    heartbeatInterval: number;
  };
  
  // Application Settings
  app: {
    name: string;
    version: string;
    description: string;
  };
  
  // Feature Flags
  features: {
    enableWebSocket: boolean;
    enableNotifications: boolean;
    enableAnalytics: boolean;
  };
}

// Get environment variables with fallbacks
const getEnvVar = (key: string, fallback: string = ''): string => {
  if (typeof window !== 'undefined') {
    // Client-side: use Next.js public env vars (NEXT_PUBLIC_*)
    return (window as any).__ENV?.[key] || process.env[`NEXT_PUBLIC_${key}`] || fallback;
  }
  // Server-side: use process.env directly
  return process.env[key] || process.env[`NEXT_PUBLIC_${key}`] || fallback;
};

const isDevelopment = process.env.NODE_ENV === 'development';
const isProduction = process.env.NODE_ENV === 'production';

// Backend URLs
// Use empty string for relative URLs (both dev and prod go through Next.js proxy)
const BACKEND_BASE_URL = getEnvVar('BACKEND_URL', ''); // Empty = relative URLs

// WebSocket URL: Must be set via NEXT_PUBLIC_WEBSOCKET_URL environment variable
const WEBSOCKET_URL = process.env.NEXT_PUBLIC_WEBSOCKET_URL || '';

// Application configuration
export const config: AppConfig = {
  // Environment
  isDevelopment,
  isProduction,
  
  // API Configuration
  api: {
    baseUrl: BACKEND_BASE_URL,
    timeout: parseInt(getEnvVar('API_TIMEOUT', '30000'), 10),
  },
  
  // WebSocket Configuration
  websocket: {
    url: WEBSOCKET_URL,
    reconnectAttempts: parseInt(getEnvVar('WS_RECONNECT_ATTEMPTS', '12'), 10),
    reconnectDelay: parseInt(getEnvVar('WS_RECONNECT_DELAY', '5000'), 10),
    heartbeatInterval: parseInt(getEnvVar('WS_HEARTBEAT_INTERVAL', '30000'), 10),
  },
  
  // Application Settings
  app: {
    name: getEnvVar('APP_NAME', 'LabOS AI'),
    version: getEnvVar('APP_VERSION', '1.0.0'),
    description: getEnvVar('APP_DESCRIPTION', 'Intelligent Research Assistant'),
  },
  
  // Feature Flags
  features: {
    enableWebSocket: getEnvVar('ENABLE_WEBSOCKET', 'true') === 'true',
    enableNotifications: getEnvVar('ENABLE_NOTIFICATIONS', 'true') === 'true',
    enableAnalytics: getEnvVar('ENABLE_ANALYTICS', 'false') === 'true',
  },
};

// Export individual config sections for convenience
export const apiConfig = config.api;
export const websocketConfig = config.websocket;
export const appConfig = config.app;
export const featureFlags = config.features;

// Validation function
export const validateConfig = (): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];


  if (!config.websocket.url) {
    errors.push('WebSocket URL is not configured');
  }

  if (config.websocket.reconnectAttempts < 0) {
    errors.push('WebSocket reconnect attempts must be positive');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
};

// Debug function
export const logConfig = (): void => {
  if (isDevelopment) {
    console.log('🔧 Application Configuration:', {
      environment: process.env.NODE_ENV,
      api: config.api,
      websocket: config.websocket,
      features: config.features,
    });
  }
};

// Default export
export default config;
