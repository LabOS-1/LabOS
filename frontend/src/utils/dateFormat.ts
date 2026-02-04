/**
 * Date/Time formatting utilities
 * Backend stores UTC time, frontend converts to local time for display
 */

/**
 * Parse timestamp as UTC (backend always sends UTC)
 * If no timezone info, treat as UTC
 */
function parseAsUTC(timestamp: string | Date): Date {
  if (timestamp instanceof Date) return timestamp;

  // If string doesn't have timezone info, append 'Z' to treat as UTC
  if (timestamp && !timestamp.endsWith('Z') && !timestamp.includes('+') && !timestamp.includes('-', 10)) {
    return new Date(timestamp + 'Z');
  }
  return new Date(timestamp);
}

/**
 * Format timestamp to local time string (HH:mm)
 * Uses 24-hour format for consistency
 */
export function formatTime(timestamp: string | Date): string {
  if (!timestamp) return '';

  const date = parseAsUTC(timestamp);

  return date.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

/**
 * Format timestamp to local time string with seconds (HH:mm:ss)
 * Uses 24-hour format for consistency
 */
export function formatTimeWithSeconds(timestamp: string | Date): string {
  if (!timestamp) return '';

  const date = parseAsUTC(timestamp);

  return date.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
}

/**
 * Format timestamp to local date and time (MMM D, HH:mm)
 * Uses 24-hour format for consistency
 */
export function formatDateTime(timestamp: string | Date): string {
  if (!timestamp) return '';

  const date = parseAsUTC(timestamp);

  return date.toLocaleString('en-GB', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

/**
 * Format timestamp to full date and time with year (YYYY MMM D, HH:mm)
 * Uses 24-hour format for consistency
 */
export function formatFullDateTime(timestamp: string | Date): string {
  if (!timestamp) return '';

  const date = parseAsUTC(timestamp);

  return date.toLocaleString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

/**
 * Format timestamp to date only
 */
export function formatDate(timestamp: string | Date): string {
  if (!timestamp) return '';

  const date = parseAsUTC(timestamp);

  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Get relative time string (e.g., "5 minutes ago")
 */
export function formatRelativeTime(timestamp: string | Date): string {
  if (!timestamp) return '';

  const date = parseAsUTC(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
  if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
  if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;

  return formatDate(date);
}
