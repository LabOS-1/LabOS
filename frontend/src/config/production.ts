/**
 * Production Environment Configuration
 * This file contains production-specific overrides
 */

export const productionConfig = {
  // Backend URLs for production
  BACKEND_URL: 'https://labos-backend-843173980594.us-central1.run.app',
  WEBSOCKET_URL: 'wss://labos-backend-843173980594.us-central1.run.app/ws',
  
  // Performance optimizations for production
  API_TIMEOUT: 60000, // Increased timeout for production
  WS_RECONNECT_ATTEMPTS: 5, // Fewer attempts in production
  WS_RECONNECT_DELAY: 10000, // Longer delay between attempts
  
  // Feature flags for production
  ENABLE_ANALYTICS: true,
  ENABLE_ERROR_REPORTING: true,
  DEBUG: false,
};

export default productionConfig;
