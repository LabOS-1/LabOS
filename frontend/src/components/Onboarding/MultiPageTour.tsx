/**
 * MultiPageTour Component
 *
 * Enhanced onboarding tour that navigates across multiple pages.
 */

'use client';

import { useEffect, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { driver, Driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import {
  multiPageTourSteps,
  multiPageTourConfig,
  TourStepWithNavigation,
} from './multiPageTourSteps';

interface MultiPageTourProps {
  autoStart?: boolean;
  onComplete?: () => void;
  forceRestart?: boolean;
}

const TOUR_STEP_KEY = 'labos_tour_current_step';

/**
 * Wait for a DOM element to appear
 */
const waitForElement = (selector: string, timeout = 3000): Promise<void> => {
  return new Promise<void>((resolve) => {
    const startTime = Date.now();

    const checkElement = () => {
      if (selector && document.querySelector(selector)) {
        console.log(`✅ Element found: ${selector}`);
        resolve();
      } else if (Date.now() - startTime > timeout) {
        console.log(`⏰ Timeout waiting for element: ${selector}`);
        resolve(); // Resolve anyway to continue tour
      } else {
        setTimeout(checkElement, 100);
      }
    };

    // Start checking after a short delay for page load
    setTimeout(checkElement, 200);
  });
};

export default function MultiPageTour({
  autoStart = false,
  onComplete,
  forceRestart = false,
}: MultiPageTourProps) {
  const router = useRouter();
  const pathname = usePathname();
  const driverRef = useRef<Driver | null>(null);
  const hasStartedRef = useRef(false);
  const isNavigatingRef = useRef(false);

  // Initialize driver instance (can be called multiple times)
  const initializeDriver = () => {
    if (driverRef.current) {
      console.log(`⚠️ Driver already exists, destroying first`);
      driverRef.current.destroy();
    }

    // Build steps with custom navigation
    const steps = multiPageTourSteps.map((step, stepIndex) => {
      const tourStep = step as TourStepWithNavigation;
      const nextStep = multiPageTourSteps[stepIndex + 1] as TourStepWithNavigation | undefined;

      return {
        element: tourStep.element,
        popover: {
          ...tourStep.popover,
          // Override next button click
          onNextClick: () => {
            console.log(`📍 Step ${stepIndex + 1}: Next button clicked`);

            // Check if NEXT step needs navigation
            if (nextStep?.navigateTo && nextStep.waitForNavigation) {
              console.log(`🚀 Next step needs navigation to: ${nextStep.navigateTo}`);

              // Save next step index and mark as navigating
              const nextStepIndex = stepIndex + 1;
              localStorage.setItem(TOUR_STEP_KEY, nextStepIndex.toString());
              isNavigatingRef.current = true;

              // Destroy current tour before navigation
              console.log(`🔄 Destroying tour before navigation`);
              driverRef.current?.destroy();

              // Navigate to next page
              router.push(nextStep.navigateTo);
            } else {
              // Normal step - use default driver behavior
              console.log(`➡️ Moving to step ${stepIndex + 2}`);
              driverRef.current?.moveNext();
            }
          },
        },
      };
    });

    // Initialize driver
    driverRef.current = driver({
      ...multiPageTourConfig,
      steps,
      onDestroyed: () => {
        // Only mark completed if not navigating
        if (!isNavigatingRef.current) {
          console.log(`✅ Tour completed`);
          localStorage.removeItem(TOUR_STEP_KEY);
          localStorage.setItem('labos_onboarding_completed', 'true');
          window.dispatchEvent(new Event('onboarding-status-changed'));

          if (onComplete) {
            onComplete();
          }

          hasStartedRef.current = false;
        } else {
          console.log(`🔄 Tour destroyed for navigation, will resume`);
        }
      },
      onHighlighted: (element, step) => {
        console.log(`🎯 Highlighted step:`, {
          element: element?.tagName,
          stepElement: (step as any)?.element,
          hasPopover: !!(step as any)?.popover,
        });
      },
      onHighlightStarted: (element, step) => {
        console.log(`🔍 Attempting to highlight:`, {
          element: element?.tagName,
          stepElement: (step as any)?.element,
          found: !!element,
        });

        // Check if element exists
        const selector = (step as any)?.element;
        if (selector && !element) {
          console.error(`❌ Element not found: ${selector}`);
        }
      },
      onDeselected: (element, step, options) => {
        console.log(`⚠️ onDeselected called:`, {
          element: element?.tagName,
          stepElement: (step as any)?.element,
          allowClose: options.config.allowClose,
          isNavigating: isNavigatingRef.current,
        });

        // Don't close tour on deselect - this was the bug!
        // onDeselected fires when moving between steps, not just when user closes
        // We should only mark complete when onDestroyed is called
      },
    });

    console.log(`🔧 Driver instance created with ${steps.length} steps`);
  };

  // Resume tour after navigation
  useEffect(() => {
    const currentStep = localStorage.getItem(TOUR_STEP_KEY);

    if (currentStep && isNavigatingRef.current) {
      console.log(`🔄 Resuming tour at step ${currentStep} on ${pathname}`);
      isNavigatingRef.current = false;

      const stepIndex = parseInt(currentStep, 10);

      // Need to recreate driver if it was destroyed
      if (!driverRef.current) {
        console.log(`🔧 Recreating driver instance for resume`);
        initializeDriver();
      }

      // Wait for element to be available
      const step = multiPageTourSteps[stepIndex] as TourStepWithNavigation;
      if (step?.element) {
        waitForElement(step.element as string).then(() => {
          if (driverRef.current) {
            console.log(`✅ Driving to step ${stepIndex + 1}`);
            driverRef.current.drive(stepIndex);
          }
        });
      } else {
        // No element needed, just drive to step
        setTimeout(() => {
          if (driverRef.current) {
            driverRef.current.drive(stepIndex);
          }
        }, 300);
      }
    }
  }, [pathname]);

  useEffect(() => {
    const isCompleted = localStorage.getItem('labos_onboarding_completed');

    if (isCompleted && !forceRestart) {
      return;
    }

    if (!autoStart && !forceRestart) {
      return;
    }

    if (hasStartedRef.current) {
      return;
    }

    const timeout = setTimeout(() => {
      startTour();
    }, 500);

    return () => {
      clearTimeout(timeout);
      // Don't destroy if we're navigating
      if (driverRef.current && !isNavigatingRef.current) {
        driverRef.current.destroy();
      }
    };
  }, [autoStart, forceRestart]);

  const startTour = () => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;

    // Initialize driver and start tour
    initializeDriver();

    console.log(`🎬 Starting tour from beginning`);
    driverRef.current?.drive();
  };

  // Expose restart method
  useEffect(() => {
    (window as any).restartOnboardingTour = () => {
      console.log('🔄 Restarting onboarding tour...');

      // Clear all tour state
      localStorage.removeItem('labos_onboarding_completed');
      localStorage.removeItem(TOUR_STEP_KEY);
      window.dispatchEvent(new Event('onboarding-status-changed'));
      hasStartedRef.current = false;
      isNavigatingRef.current = false;

      // Destroy current tour if exists
      if (driverRef.current) {
        driverRef.current.destroy();
      }

      // Navigate to dashboard if not already there
      const currentPath = window.location.pathname;
      if (currentPath !== '/dashboard') {
        console.log('📍 Not on dashboard, navigating...');
        router.push('/dashboard');
        // Dashboard will show WelcomeCard automatically when isCompleted changes
      } else {
        console.log('📍 Already on dashboard, WelcomeCard should appear automatically');
        // Already on dashboard, WelcomeCard will show via useEffect in AppLayout
      }
    };

    return () => {
      delete (window as any).restartOnboardingTour;
    };
  }, [router]);

  return null;
}
