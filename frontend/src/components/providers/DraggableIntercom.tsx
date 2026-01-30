'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Box, Fab, Tooltip } from '@mui/material';
import { Chat as ChatIcon } from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';

export const DraggableIntercom: React.FC = () => {
  const theme = useTheme();
  const [position, setPosition] = useState({ x: 20, y: 20 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [hasMoved, setHasMoved] = useState(false);
  const fabRef = useRef<HTMLButtonElement>(null);

  // Handle mouse/touch start
  const handleStart = (clientX: number, clientY: number) => {
    if (fabRef.current) {
      const rect = fabRef.current.getBoundingClientRect();
      setDragOffset({
        x: clientX - rect.left,
        y: clientY - rect.top
      });
      setIsDragging(true);
      setHasMoved(false);
    }
  };

  // Handle movement
  const handleMove = (clientX: number, clientY: number) => {
    if (isDragging) {
      setHasMoved(true);
      
      // Calculate new position relative to viewport (bottom-right origin)
      const x = window.innerWidth - clientX + dragOffset.x - (fabRef.current?.offsetWidth || 56);
      const y = window.innerHeight - clientY + dragOffset.y - (fabRef.current?.offsetHeight || 56);
      
      // Boundary checks
      const maxX = window.innerWidth - (fabRef.current?.offsetWidth || 56);
      const maxY = window.innerHeight - (fabRef.current?.offsetHeight || 56);
      
      setPosition({
        x: Math.max(20, Math.min(x, maxX)),
        y: Math.max(20, Math.min(y, maxY))
      });
    }
  };

  // Handle end
  const handleEnd = () => {
    setIsDragging(false);
  };

  // Add global event listeners for dragging
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => handleMove(e.clientX, e.clientY);
    const onMouseUp = () => handleEnd();
    const onTouchMove = (e: TouchEvent) => handleMove(e.touches[0].clientX, e.touches[0].clientY);
    const onTouchEnd = () => handleEnd();

    if (isDragging) {
      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
      window.addEventListener('touchmove', onTouchMove);
      window.addEventListener('touchend', onTouchEnd);
    }

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('touchmove', onTouchMove);
      window.removeEventListener('touchend', onTouchEnd);
    };
  }, [isDragging, dragOffset]);

  const handleClick = () => {
    // Only open if not dragged significantly
    if (!hasMoved && window.Intercom) {
      window.Intercom('show');
    }
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: position.y,
        right: position.x,
        zIndex: 9999,
        touchAction: 'none', // Prevent scrolling while dragging
        cursor: isDragging ? 'grabbing' : 'grab',
        transition: isDragging ? 'none' : 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
        '&:hover': {
          transform: 'scale(1.1)'
        }
      }}
      onMouseDown={(e) => handleStart(e.clientX, e.clientY)}
      onTouchStart={(e) => handleStart(e.touches[0].clientX, e.touches[0].clientY)}
    >
      <Tooltip title="Support Chat (Drag to move)" placement="left">
        <Fab
          ref={fabRef}
          color="primary"
          onClick={handleClick}
          sx={{
            width: 56,
            height: 56,
            bgcolor: theme.palette.primary.main,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            '&:hover': {
              bgcolor: theme.palette.primary.dark,
            }
          }}
        >
          <ChatIcon sx={{ color: 'white' }} />
        </Fab>
      </Tooltip>
    </Box>
  );
};

export default DraggableIntercom;

