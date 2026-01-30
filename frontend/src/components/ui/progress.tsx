import React from 'react';
import { LinearProgress, Box, SxProps, Theme } from '@mui/material';

interface ProgressProps {
  value: number;
  className?: string;
  max?: number;
  sx?: SxProps<Theme>;
  color?: 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning';
  variant?: 'determinate' | 'indeterminate';
}

export const Progress: React.FC<ProgressProps> = ({ 
  value, 
  className = '', 
  max = 100,
  sx,
  color = 'primary',
  variant = 'determinate'
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  
  return (
    <Box 
      className={className}
      sx={{ 
        width: '100%', 
        ...sx 
      }}
    >
      <LinearProgress 
        variant={variant}
        value={percentage}
        color={color}
        sx={{
          height: 8,
          borderRadius: 1,
          backgroundColor: 'grey.200',
          '& .MuiLinearProgress-bar': {
            borderRadius: 1,
            transition: 'width 300ms ease-out',
          },
        }}
      />
    </Box>
  );
};
