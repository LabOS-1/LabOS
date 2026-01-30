import React from 'react';
import { 
  Card as MuiCard, 
  CardContent as MuiCardContent,
  CardHeader as MuiCardHeader,
  Typography,
  SxProps, 
  Theme 
} from '@mui/material';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  sx?: SxProps<Theme>;
  elevation?: number;
}

interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
  sx?: SxProps<Theme>;
}

interface CardContentProps {
  children: React.ReactNode;
  className?: string;
  sx?: SxProps<Theme>;
}

interface CardTitleProps {
  children: React.ReactNode;
  className?: string;
  sx?: SxProps<Theme>;
  variant?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}

export const Card: React.FC<CardProps> = ({ 
  children, 
  className = '', 
  sx,
  elevation = 1 
}) => {
  return (
    <MuiCard 
      className={className}
      elevation={elevation}
      sx={{
        borderRadius: 2,
        ...sx,
      }}
    >
      {children}
    </MuiCard>
  );
};

export const CardHeader: React.FC<CardHeaderProps> = ({ 
  children, 
  className = '', 
  sx 
}) => {
  return (
    <MuiCardHeader 
      className={className}
      sx={{
        borderBottom: '1px solid',
        borderColor: 'divider',
        ...sx,
      }}
      title={children}
    />
  );
};

export const CardContent: React.FC<CardContentProps> = ({ 
  children, 
  className = '', 
  sx 
}) => {
  return (
    <MuiCardContent 
      className={className}
      sx={sx}
    >
      {children}
    </MuiCardContent>
  );
};

export const CardTitle: React.FC<CardTitleProps> = ({ 
  children, 
  className = '', 
  sx,
  variant = 'h6' 
}) => {
  return (
    <Typography 
      variant={variant}
      component="h3"
      className={className}
      sx={{
        fontWeight: 600,
        ...sx,
      }}
    >
      {children}
    </Typography>
  );
};
