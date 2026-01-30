/**
 * Onboarding Tour Steps Configuration
 *
 * Defines the 8-step guided tour for new users to understand LABOS's core features.
 * Each step highlights a specific UI element and explains its functionality.
 */

import { DriveStep } from 'driver.js';

export const onboardingSteps: DriveStep[] = [
  // Step 1: Welcome
  {
    popover: {
      title: '👋 Welcome to LABOS',
      description: `
        <div style="line-height: 1.8;">
          <p style="margin-bottom: 12px;"><strong>Discover core features in 3 minutes:</strong></p>
          <ul style="margin: 8px 0; padding-left: 20px;">
            <li>🤖 Multi-Agent collaboration system</li>
            <li>🛠️ 110+ biomedical research tools</li>
            <li>📷 Image/video analysis capabilities</li>
          </ul>
          <p style="margin-top: 12px; font-size: 0.9em; color: #666;">Click "Next" to start the tour, or "Skip" to explore on your own.</p>
        </div>
      `,
    },
  },

  // Step 2: Chat Projects List
  {
    element: '.chat-projects-section',
    popover: {
      title: '💬 Chat Projects',
      description: `
        <div style="line-height: 1.8;">
          <p>Manage all your conversation projects here.</p>
          <p style="margin-top: 8px;">Each project independently saves:</p>
          <ul style="margin: 8px 0; padding-left: 20px;">
            <li>Chat history</li>
            <li>Uploaded files</li>
            <li>AI workflow records</li>
          </ul>
        </div>
      `,
      side: 'right',
      align: 'start',
    },
  },

  // Step 3: Message Input
  {
    element: '.message-input-area',
    popover: {
      title: '✍️ Powerful Input Capabilities',
      description: `
        <div style="line-height: 1.8;">
          <p>Not just text - you can also:</p>
          <ul style="margin: 8px 0; padding-left: 20px;">
            <li>📎 Upload images/videos/PDFs</li>
            <li>📊 Upload CSV data files</li>
            <li>🧬 Paste DNA/protein sequences</li>
          </ul>
          <p style="margin-top: 12px; font-style: italic; color: #1976d2;">
            Example: "Analyze this Western Blot image"
          </p>
        </div>
      `,
      side: 'top',
      align: 'center',
    },
  },

  // Step 4: Workflow Panel (Core Feature)
  {
    element: '.workflow-panel-toggle',
    popover: {
      title: '🔍 AI\'s Transparent Thinking Process',
      description: `
        <div style="line-height: 1.8;">
          <p><strong>LABOS's unique multi-agent collaboration:</strong></p>
          <p style="margin: 12px 0; padding: 8px; background: #f5f5f5; border-radius: 4px;">
            Manager → Dev → Critic
          </p>
          <p>Click here to see:</p>
          <ul style="margin: 8px 0; padding-left: 20px;">
            <li>How AI breaks down tasks</li>
            <li>Which tools are being used</li>
            <li>Generated charts and files</li>
          </ul>
          <p style="margin-top: 12px; font-size: 0.9em; color: #d32f2f;">
            ⭐ This transparency sets LABOS apart from other AI tools!
          </p>
        </div>
      `,
      side: 'left',
      align: 'start',
    },
  },

  // Step 5: Tools Library
  {
    element: '[href="/tools"]',
    popover: {
      title: '🛠️ 110+ Biomedical Tools',
      description: `
        <div style="line-height: 1.8;">
          <p>Built-in tool library includes:</p>
          <ul style="margin: 8px 0; padding-left: 20px;">
            <li>🔬 PubMed/arXiv literature search</li>
            <li>📊 Data analysis & visualization</li>
            <li>🧬 Sequence analysis</li>
            <li>🐍 Python code execution</li>
          </ul>
          <p style="margin-top: 12px; padding: 8px; background: #e3f2fd; border-radius: 4px; color: #1976d2;">
            💡 You can also create custom tools!
          </p>
        </div>
      `,
      side: 'bottom',
      align: 'center',
    },
  },

  // Step 6: Files Management
  {
    element: '[href="/files"]',
    popover: {
      title: '📁 File Center',
      description: `
        <div style="line-height: 1.8;">
          <p>Centrally manage all files:</p>
          <ul style="margin: 8px 0; padding-left: 20px;">
            <li>Your uploaded data</li>
            <li>AI-generated charts</li>
            <li>Analysis reports & code</li>
          </ul>
          <p style="margin-top: 12px;">
            Download and reuse across projects.
          </p>
        </div>
      `,
      side: 'bottom',
      align: 'center',
    },
  },

  // Step 7: Quick Start with Templates
  {
    element: '.new-project-button',
    popover: {
      title: '🚀 Quick Start',
      description: `
        <div style="line-height: 1.8;">
          <p>Choose a scenario template:</p>
          <ul style="margin: 8px 0; padding-left: 20px;">
            <li>📚 Literature Review</li>
            <li>📊 Data Analysis</li>
            <li>🧬 Sequence Analysis</li>
            <li>📷 Image Analysis</li>
          </ul>
          <p style="margin-top: 12px;">
            Or start with a blank project to explore freely.
          </p>
        </div>
      `,
      side: 'right',
      align: 'start',
    },
  },

  // Step 8: Completion
  {
    popover: {
      title: '✅ You\'re All Set!',
      description: `
        <div style="line-height: 1.8;">
          <p style="margin-bottom: 12px;"><strong>Now you can:</strong></p>
          <ol style="margin: 8px 0; padding-left: 20px;">
            <li>Choose a scenario template to start</li>
            <li>Or ask a question directly</li>
          </ol>
          <p style="margin-top: 16px; padding: 12px; background: #fff3e0; border-radius: 4px; color: #e65100;">
            💡 Click the <strong>[?]</strong> button in the top-right corner anytime to revisit this tour.
          </p>
        </div>
      `,
    },
  },
];

/**
 * Default configuration for the onboarding tour
 */
export const onboardingConfig = {
  animate: true,
  opacity: 0.75,
  padding: 10,
  allowClose: true,
  overlayClickNext: false,
  doneBtnText: 'Get Started',
  closeBtnText: 'Skip',
  nextBtnText: 'Next',
  prevBtnText: 'Back',
  showProgress: true,
  progressText: 'Step {{current}} of {{total}}',
  onDestroyed: () => {
    // Mark onboarding as completed
    localStorage.setItem('labos_onboarding_completed', 'true');
  },
};