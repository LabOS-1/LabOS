'use client'

import { Inter } from 'next/font/google'
import { ConfigProvider, App as AntApp, theme } from 'antd';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { store, persistor } from '../store';
import { validateConfig, logConfig } from '@/config';
import { ThemeProvider } from '@/theme/ThemeProvider';
import WebSocketProvider from '@/components/providers/WebSocketProvider';
import IntercomProvider from '@/components/providers/IntercomProvider';
import { Auth0Provider } from '@auth0/nextjs-auth0';
import AuthSync from '@/components/Auth/AuthSync';
import AppLayout from '@/components/Layout/AppLayout';
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

// Wrapper component that decides layout structure immediately
function LayoutWrapper({ children }: { children: React.ReactNode }) {
  'use client'

  const { usePathname } = require('next/navigation');
  const pathname = usePathname();

  // Check localStorage immediately (synchronous, no delay)
  const hasToken = typeof window !== 'undefined' && localStorage.getItem('auth_token');

  // Pages that should NEVER use AppLayout
  const noLayoutPages = ['/', '/welcome', '/verify-email', '/onboarding', '/terms', '/privacy', '/cookies', '/profile', '/waitlist-pending', '/access-denied'];
  const isNoLayoutPage = noLayoutPages.includes(pathname) ||
                         pathname.startsWith('/welcome') ||
                         pathname.startsWith('/terms') ||
                         pathname.startsWith('/privacy') ||
                         pathname.startsWith('/cookies') ||
                         pathname.startsWith('/waitlist-pending') ||
                         pathname.startsWith('/access-denied');

  // Decision is made IMMEDIATELY based on token presence
  const shouldUseLayout = hasToken && !isNoLayoutPage;

  // Render AppLayout wrapper BEFORE children render
  if (shouldUseLayout) {
    return <AppLayout>{children}</AppLayout>;
  }

  return <>{children}</>;
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // Validate configuration on app start
  if (typeof window !== 'undefined') {
    const { isValid, errors } = validateConfig();
    if (!isValid) {
      console.error('❌ Configuration validation failed:', errors);
    }
    logConfig();
  }

  return (
    <html lang="en">
      <head>
        <link rel="icon" type="image/png" href="/logo.png" />
        <link rel="apple-touch-icon" href="/logo.png" />
        <title>LABOS AI Assistant</title>
        <meta name="description" content="Self-Evolving Intelligent Laboratory Assistant - Advanced AI for biomedical research" />
      </head>
      <body className={inter.className}>
        <Auth0Provider>
          <Provider store={store}>
            <PersistGate loading={null} persistor={persistor}>
              <WebSocketProvider>
                <ThemeProvider>
                  <IntercomProvider>
                    <ConfigProvider
                      theme={{
                        algorithm: theme.darkAlgorithm,
                        token: {
                          colorPrimary: '#0ea5e9',
                          colorBgBase: '#0f172a',
                          colorBgContainer: '#1e293b',
                          colorBorder: '#334155',
                          colorText: '#f1f5f9',
                          borderRadius: 8,
                        },
                        components: {
                          Layout: {
                            bodyBg: '#0f172a',
                            siderBg: '#1e293b',
                            headerBg: '#1e293b',
                          },
                          Menu: {
                            darkItemBg: '#1e293b',
                            darkSubMenuItemBg: '#334155',
                          },
                          Card: {
                            colorBgContainer: '#1e293b',
                            colorBorder: '#334155',
                          },
                        },
                      }}
                    >
                      <AntApp>
                        <div id="root">
                          <AuthSync />
                          <LayoutWrapper>
                            {children}
                          </LayoutWrapper>
                        </div>
                      </AntApp>
                    </ConfigProvider>
                  </IntercomProvider>
                </ThemeProvider>
              </WebSocketProvider>
            </PersistGate>
          </Provider>
        </Auth0Provider>
      </body>
    </html>
  )
}