import { createTheme, ThemeOptions } from '@mui/material/styles';

// LABOS AI theme colors aligned with ai4labos.com branding
const labosColors = {
  primary: '#4f46e5',    // indigo (website primary)
  secondary: '#8b5cf6',  // violet (gradient start)
  accent: '#22d3ee',     // cyan (gradient end)
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#3b82f6',
};

// Common theme configuration
const baseTheme: ThemeOptions = {
  typography: {
    fontFamily: [
      '"Inter"',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
  shape: {
    borderRadius: 12,
  },
  spacing: 8,
};

// Light theme (aligned with ai4labos.com)
export const lightTheme = createTheme({
  ...baseTheme,
  palette: {
    mode: 'light',
    primary: {
      main: labosColors.primary,
      light: '#6366f1',
      dark: '#4338ca',
    },
    secondary: {
      main: labosColors.secondary,
      light: '#a78bfa',
      dark: '#7c3aed',
    },
    error: {
      main: labosColors.error,
    },
    warning: {
      main: labosColors.warning,
    },
    info: {
      main: labosColors.info,
    },
    success: {
      main: labosColors.success,
    },
    background: {
      default: '#f7f9ff',
      paper: '#ffffff',
    },
    text: {
      primary: '#1f2937',
      secondary: '#6b7280',
    },
  },
});

// Dark theme
export const darkTheme = createTheme({
  ...baseTheme,
  palette: {
    mode: 'dark',
    primary: {
      main: labosColors.primary,
      light: '#6366f1',
      dark: '#4338ca',
    },
    secondary: {
      main: labosColors.secondary,
      light: '#a78bfa',
      dark: '#7c3aed',
    },
    error: {
      main: labosColors.error,
    },
    warning: {
      main: labosColors.warning,
    },
    info: {
      main: labosColors.info,
    },
    success: {
      main: labosColors.success,
    },
    background: {
      default: '#0f172a',
      paper: '#1e293b',
    },
    text: {
      primary: '#f1f5f9',
      secondary: '#94a3b8',
    },
    divider: '#334155',
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(30, 41, 59, 0.9)',
          backdropFilter: 'blur(10px)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: 'rgba(30, 41, 59, 0.9)',
          backdropFilter: 'blur(10px)',
          borderRight: '1px solid #334155',
        },
      },
    },
  },
});
