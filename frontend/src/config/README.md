# Configuration System

This directory contains the centralized configuration system for the LabOS AI frontend application.

## Files

- `index.ts` - Main configuration file with environment-aware settings
- `production.ts` - Production-specific configuration overrides
- `README.md` - This documentation file

## Usage

### Basic Configuration

```typescript
import { config, apiConfig, websocketConfig } from '@/config';

// Use the full config object
console.log(config.api.baseUrl);

// Or use specific config sections
const wsUrl = websocketConfig.url;
const apiTimeout = apiConfig.timeout;
```

### Environment Variables

The configuration system supports environment variables through Next.js public variables (prefixed with `NEXT_PUBLIC_`):

#### Required Variables
- `NEXT_PUBLIC_BACKEND_URL` - Backend API base URL
- `NEXT_PUBLIC_WEBSOCKET_URL` - WebSocket connection URL

#### Optional Variables
- `NEXT_PUBLIC_API_TIMEOUT` - API request timeout (default: 30000ms)
- `NEXT_PUBLIC_WS_RECONNECT_ATTEMPTS` - WebSocket reconnection attempts (default: 12)
- `NEXT_PUBLIC_WS_RECONNECT_DELAY` - Delay between reconnection attempts (default: 5000ms)
- `NEXT_PUBLIC_WS_HEARTBEAT_INTERVAL` - WebSocket heartbeat interval (default: 30000ms)
- `NEXT_PUBLIC_ENABLE_WEBSOCKET` - Enable/disable WebSocket features (default: true)
- `NEXT_PUBLIC_ENABLE_NOTIFICATIONS` - Enable/disable notifications (default: true)
- `NEXT_PUBLIC_ENABLE_ANALYTICS` - Enable/disable analytics (default: false)

#### Application Meta
- `NEXT_PUBLIC_APP_NAME` - Application name (default: "LabOS AI")
- `NEXT_PUBLIC_APP_VERSION` - Application version (default: "1.0.0")
- `NEXT_PUBLIC_APP_DESCRIPTION` - Application description

## Environment Setup

### Development

Create a `.env.local` file in the project root:

```bash
# Backend Configuration
NEXT_PUBLIC_BACKEND_URL=http://localhost:18800
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:18800/ws

# Feature Flags
NEXT_PUBLIC_ENABLE_WEBSOCKET=true
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true
NEXT_PUBLIC_ENABLE_ANALYTICS=false
```

### Production

Environment variables should be set in your deployment environment (Cloud Run, Vercel, etc.):

```bash
NEXT_PUBLIC_BACKEND_URL=https://labos-backend-843173980594.us-central1.run.app
NEXT_PUBLIC_WEBSOCKET_URL=wss://labos-backend-843173980594.us-central1.run.app/ws
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

## Configuration Validation

The configuration system includes validation:

```typescript
import { validateConfig } from '@/config';

const { isValid, errors } = validateConfig();
if (!isValid) {
  console.error('Configuration errors:', errors);
}
```

## Debug Information

In development mode, configuration can be logged:

```typescript
import { logConfig } from '@/config';

logConfig(); // Logs current configuration to console
```

## Best Practices

1. **Always use the centralized config** instead of hardcoding URLs or settings
2. **Use environment variables** for deployment-specific settings
3. **Validate configuration** on application startup
4. **Use feature flags** to enable/disable functionality
5. **Keep sensitive data** out of client-side configuration (use server-side env vars)

## Migration from Hardcoded Values

When migrating from hardcoded values:

1. Import the config: `import { websocketConfig } from '@/config';`
2. Replace hardcoded values: `websocketConfig.url` instead of `'ws://localhost:18800/ws'`
3. Add any new configuration options to the config file
4. Update environment variables as needed
