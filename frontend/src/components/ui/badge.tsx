import React from 'react';
import { Chip, SxProps, Theme } from '@mui/material';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary';
  className?: string;
  sx?: SxProps<Theme>;
  size?: 'small' | 'medium';
  onDelete?: () => void;
}

export const Badge: React.FC<BadgeProps> = ({ 
  children, 
  variant = 'default', 
  className = '',
  sx,
  size = 'small',
  onDelete
}) => {
  const getChipProps = () => {
    switch (variant) {
      case 'destructive':
        return {
          color: 'error' as const,
          variant: 'filled' as const,
        };
      case 'outline':
        return {
          color: 'default' as const,
          variant: 'outlined' as const,
        };
      case 'secondary':
        return {
          color: 'secondary' as const,
          variant: 'filled' as const,
        };
      case 'default':
      default:
        return {
          color: 'primary' as const,
          variant: 'filled' as const,
        };
    }
  };

  const chipProps = getChipProps();
  
  return (
    <Chip
      label={children}
      className={className}
      size={size}
      onDelete={onDelete}
      {...chipProps}
      sx={{
        fontSize: '0.75rem',
        fontWeight: 500,
        ...sx,
      }}
    />
  );
};
