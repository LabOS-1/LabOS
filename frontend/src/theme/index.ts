import { createTheme, ThemeOptions } from '@mui/material/styles';

// LABOS AI theme colors based on current design
const labosColors = {
  primary: '#0ea5e9',
  secondary: '#a855f7',
  accent: '#ec4899',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#3b82f6',
};

// Common theme configuration
const baseTheme: ThemeOptions = {
  typography: {
    fontFamily: [
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
    borderRadius: 8,
  },
  spacing: 8,
};

// Light theme
export const lightTheme = createTheme({
  ...baseTheme,
  palette: {
    mode: 'light',
    primary: {
      main: labosColors.primary,
      light: '#38bdf8',
      dark: '#0284c7',
    },
    secondary: {
      main: labosColors.secondary,
      light: '#c084fc',
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
      default: '#f8fafc',
      paper: '#ffffff',
    },
    text: {
      primary: '#1f2937',
      secondary: '#6b7280',
    },
  },
});

// Dark theme (current LABOS design)
export const darkTheme = createTheme({
  ...baseTheme,
  palette: {
    mode: 'dark',
    primary: {
      main: labosColors.primary,
      light: '#38bdf8',
      dark: '#0284c7',
    },
    secondary: {
      main: labosColors.secondary,
      light: '#c084fc',
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
    // Custom component overrides
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


