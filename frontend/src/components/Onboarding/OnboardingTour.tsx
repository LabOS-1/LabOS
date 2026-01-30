/**
 * OnboardingTour Component
 *
 * Displays an interactive guided tour for first-time users.
 * Uses driver.js to highlight UI elements and explain features.
 *
 * Features:
 * - 8-step walkthrough of core LABOS features
 * - Skippable at any time
 * - Remembered via localStorage
 * - Can be restarted from Help menu
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import { driver, Driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import { onboardingSteps, onboardingConfig } from './onboardingSteps';

interface OnboardingTourProps {
  /**
   * Whether to show the tour immediately on mount
   * @default false
   */
  autoStart?: boolean;

  /**
   * Callback when tour is completed or skipped
   */
  onComplete?: () => void;

  /**
   * Force restart even if previously completed
   * @default false
   */
  forceRestart?: boolean;
}

export default function OnboardingTour({
  autoStart = false,
  onComplete,
  forceRestart = false,
}: OnboardingTourProps) {
  const driverRef = useRef<Driver | null>(null);
  const hasStartedRef = useRef(false);

  useEffect(() => {
    // Check if onboarding has been completed before
    const isCompleted = localStorage.getItem('labos_onboarding_completed');

    // Don't show if already completed (unless force restart)
    if (isCompleted && !forceRestart) {
      return;
    }

    // Don't auto-start if not requested
    if (!autoStart && !forceRestart) {
      return;
    }

    // Prevent multiple initializations
    if (hasStartedRef.current) {
      return;
    }

    // Wait for DOM to be ready
    const timeout = setTimeout(() => {
      startTour();
    }, 500);

    return () => {
      clearTimeout(timeout);
      if (driverRef.current) {
        driverRef.current.destroy();
      }
    };
  }, [autoStart, forceRestart]);

  const startTour = () => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;

    // Initialize driver.js with custom configuration
    driverRef.current = driver({
      ...onboardingConfig,
      steps: onboardingSteps,
      onDestroyed: () => {
        // Mark as completed
        localStorage.setItem('labos_onboarding_completed', 'true');
        window.dispatchEvent(new Event('onboarding-status-changed'));

        // Call parent callback
        if (onComplete) {
          onComplete();
        }

        hasStartedRef.current = false;
      },
      onDeselected: (_element, _step, options) => {
        // Handle case where user clicks outside
        if (options.config.allowClose) {
          // Mark as completed even if user closed early
          localStorage.setItem('labos_onboarding_completed', 'true');
          window.dispatchEvent(new Event('onboarding-status-changed'));
          if (onComplete) {
            onComplete();
          }
        }
      },
    });

    // Start the tour
    driverRef.current.drive();
  };

  // NOTE: Global restart function disabled - MultiPageTour handles this now
  // Expose method to restart tour programmatically
  // useEffect(() => {
  //   // Make restart function available globally for Help menu
  //   (window as any).restartOnboardingTour = () => {
  //     localStorage.removeItem('labos_onboarding_completed');
  //     window.dispatchEvent(new Event('onboarding-status-changed'));
  //     hasStartedRef.current = false;

  //     // Wait a bit for DOM to be ready
  //     setTimeout(() => {
  //       startTour();
  //     }, 100);
  //   };

  //   return () => {
  //     delete (window as any).restartOnboardingTour;
  //   };
  // }, []);

  // This component doesn't render anything visible
  return null;
}

/**
 * Hook to check if onboarding should be shown
 * Reactively updates when localStorage changes
 */
export function useOnboardingStatus() {
  const [isCompleted, setIsCompleted] = useState(() => {
    // During SSR, assume not completed to show WelcomeCard
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('labos_onboarding_completed') === 'true';
  });

  // Listen for storage changes (from other tabs or programmatic changes)
  useEffect(() => {
    const checkStatus = () => {
      const completed = localStorage.getItem('labos_onboarding_completed') === 'true';
      setIsCompleted(completed);
    };

    // Check on mount
    checkStatus();

    // Listen for storage events (cross-tab communication)
    window.addEventListener('storage', checkStatus);

    // Custom event for same-tab changes
    window.addEventListener('onboarding-status-changed', checkStatus);

    return () => {
      window.removeEventListener('storage', checkStatus);
      window.removeEventListener('onboarding-status-changed', checkStatus);
    };
  }, []);

  const markCompleted = () => {
    localStorage.setItem('labos_onboarding_completed', 'true');
    window.dispatchEvent(new Event('onboarding-status-changed'));
  };

  const reset = () => {
    localStorage.removeItem('labos_onboarding_completed');
    window.dispatchEvent(new Event('onboarding-status-changed'));
  };

  return {
    isCompleted,
    markCompleted,
    reset,
  };
}
