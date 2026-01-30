import React from 'react';
import { Box, SxProps, Theme } from '@mui/material';

interface ScrollAreaProps {
  children: React.ReactNode;
  className?: string;
  sx?: SxProps<Theme>;
  maxHeight?: string | number;
  direction?: 'vertical' | 'horizontal' | 'both';
}

export const ScrollArea: React.FC<ScrollAreaProps> = ({ 
  children, 
  className = '',
  sx,
  maxHeight,
  direction = 'vertical'
}) => {
  const getOverflowStyle = (): Record<string, string> => {
    switch (direction) {
      case 'horizontal':
        return { overflowX: 'auto', overflowY: 'hidden' };
      case 'both':
        return { overflow: 'auto' };
      case 'vertical':
      default:
        return { overflowY: 'auto', overflowX: 'hidden' };
    }
  };

  return (
    <Box 
      className={className}
      sx={{
        ...getOverflowStyle(),
        ...(maxHeight && { maxHeight }),
        '&::-webkit-scrollbar': {
          width: '8px',
          height: '8px',
        },
        '&::-webkit-scrollbar-track': {
          backgroundColor: 'grey.100',
          borderRadius: 1,
        },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: 'grey.400',
          borderRadius: 1,
          '&:hover': {
            backgroundColor: 'grey.500',
          },
        },
        ...sx,
      }}
    >
      {children}
    </Box>
  );
};
