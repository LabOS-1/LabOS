'use client'

import React, { useEffect } from 'react'
import { Box, CircularProgress, Typography } from '@mui/material'
import { useRouter } from 'next/navigation'
import WelcomePage from '@/app/welcome/page'
import { useAppSelector } from '@/store/hooks'

export default function HomePage() {
  const { isAuthenticated, isLoading, user } = useAppSelector((state) => state.auth)
  const router = useRouter()

  // Redirect authenticated users based on their status
  useEffect(() => {
    if (isAuthenticated && !isLoading && user) {
      // Only approved users go to dashboard
      if (user.status === 'approved') {
        router.push('/dashboard')
      }
      // Waitlist users should stay on waitlist page or be redirected there
      else if (user.status === 'waitlist') {
        router.push(`/waitlist-pending?email=${encodeURIComponent(user.email)}`)
      }
      // Rejected users stay on waitlist page with status
      else if (user.status === 'rejected') {
        router.push(`/waitlist-pending?email=${encodeURIComponent(user.email)}&status=rejected`)
      }
      // Suspended users get logged out
      else if (user.status === 'suspended') {
        localStorage.removeItem('auth_token')
        router.push('/welcome')
      }
    }
  }, [isAuthenticated, isLoading, user, router])

  if (isLoading) {
    return (
      <Box
        sx={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2
        }}
      >
        <CircularProgress />
        <Typography variant="body2" color="text.secondary">
          Checking authentication...
        </Typography>
      </Box>
    )
  }

  // Show welcome page for unauthenticated users
  return <WelcomePage />
}