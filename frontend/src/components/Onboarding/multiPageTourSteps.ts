/**
 * Multi-Page Onboarding Tour Steps
 *
 * Comprehensive tour that navigates across different pages to showcase
 * all major features of LABOS. Each step can trigger page navigation.
 */

import { DriveStep } from 'driver.js';

/**
 * Tour step with optional navigation
 */
export interface TourStepWithNavigation extends DriveStep {
  /**
   * URL to navigate to before showing this step
   */
  navigateTo?: string;

  /**
   * Whether to wait for navigation to complete
   */
  waitForNavigation?: boolean;
}

export const multiPageTourSteps: TourStepWithNavigation[] = [
  // ============================================
  // SECTION 1: Welcome (Dashboard)
  // ============================================
  {
    popover: {
      title: 'Welcome to LABOS',
      description: `
        <div style="line-height: 1.6;">
          <p style="margin-bottom: 16px; font-size: 1em; color: #1976d2;">
            <strong>Let's Explore LABOS Together</strong>
          </p>
          <p style="margin-bottom: 8px; color: #555; font-weight: 500;">This interactive tour will guide you through:</p>
          <ul style="margin: 12px 0; padding-left: 20px; color: #333;">
            <li style="margin-bottom: 6px;"><strong>Multi-Agent System</strong> - 4 AI specialists working together</li>
            <li style="margin-bottom: 6px;"><strong>Chat Projects</strong> - Organize research conversations</li>
            <li style="margin-bottom: 6px;"><strong>Tools Library</strong> - 110+ biomedical research tools</li>
            <li style="margin-bottom: 6px;"><strong>File Management</strong> - Centralized storage system</li>
          </ul>
          <p style="margin-top: 16px; font-size: 0.9em; color: #757575; font-style: italic;">
            The tour will automatically navigate between pages
          </p>
        </div>
      `,
    },
  },

  // ============================================
  // SECTION 2: Chat Projects Page (with navigation)
  // ============================================
  {
    navigateTo: '/chat/projects',
    waitForNavigation: true,
    element: '.new-project-button',
    popover: {
      title: 'Chat Projects',
      description: `
        <div style="line-height: 1.6;">
          <p style="margin-bottom: 16px; font-size: 1em; color: #1976d2;">
            <strong>Your Research Project Workspace</strong>
          </p>

          <p style="margin-bottom: 8px; color: #555; font-weight: 500;">Key Features:</p>
          <ul style="margin: 12px 0; padding-left: 20px; color: #333;">
            <li style="margin-bottom: 6px;"><strong>Create Projects</strong> - Start from templates (Literature Review, Data Analysis, etc.)</li>
            <li style="margin-bottom: 6px;"><strong>View Projects</strong> - Browse all projects with message counts and activity status</li>
            <li style="margin-bottom: 6px;"><strong>Continue Work</strong> - Resume any conversation by clicking a project card</li>
          </ul>

          <div style="margin-top: 16px; padding: 10px; background: #f5f5f5; border-left: 3px solid #1976d2; border-radius: 2px;">
            <p style="margin: 0; font-size: 0.9em; color: #424242;">
              Each project keeps your chat history, files, and workflow records organized together
            </p>
          </div>

          <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;" />

          <p style="margin-bottom: 10px; font-weight: 600; color: #333;">Multi-Agent Collaboration</p>
          <p style="font-size: 0.9em; color: #616161; line-height: 1.6; margin: 0;">
            When you chat, the <strong>Manager</strong> coordinates the team by delegating tasks to specialized agents.
            The <strong>Dev Agent</strong> handles research and analysis, <strong>Tool Creator</strong> builds custom tools when needed,
            and <strong>Critic</strong> ensures quality results. View their work in real-time through the workflow panel.
          </p>
        </div>
      `,
    },
  },

  // ============================================
  // SECTION 4: Tools Page
  // ============================================
  {
    navigateTo: '/tools',
    waitForNavigation: true,
    element: '.builtin-tools-section',
    popover: {
      title: 'Tools Library',
      description: `
        <div style="line-height: 1.6;">
          <p style="margin-bottom: 16px; font-size: 1em; color: #1976d2;">
            <strong>110+ Specialized Research Tools</strong>
          </p>

          <p style="margin-bottom: 8px; color: #555; font-weight: 500;">Tool Categories:</p>
          <ul style="margin: 12px 0; padding-left: 20px; color: #333;">
            <li style="margin-bottom: 6px;"><strong>Literature Search</strong> - PubMed, arXiv, Google Scholar</li>
            <li style="margin-bottom: 6px;"><strong>Data Analysis</strong> - Pandas, NumPy, Matplotlib</li>
            <li style="margin-bottom: 6px;"><strong>Sequence Processing</strong> - BLAST, alignment tools</li>
            <li style="margin-bottom: 6px;"><strong>Code Execution</strong> - Python interpreter</li>
            <li style="margin-bottom: 6px;"><strong>Media Analysis</strong> - Image and video processing</li>
          </ul>

          <div style="margin-top: 16px; padding: 10px; background: #f5f5f5; border-left: 3px solid #2e7d32; border-radius: 2px;">
            <p style="margin: 0; font-size: 0.9em; color: #424242;">
              All built-in tools are automatically available to AI agents
            </p>
          </div>

          <p style="margin-top: 12px; font-size: 0.9em; color: #616161; font-style: italic;">
            Custom tools can be created for team-specific workflows
          </p>
        </div>
      `,
    },
  },

  // ============================================
  // SECTION 5: Files Page
  // ============================================
  {
    navigateTo: '/files',
    waitForNavigation: true,
    element: '.files-management-section',
    popover: {
      title: 'File Management',
      description: `
        <div style="line-height: 1.6;">
          <p style="margin-bottom: 16px; font-size: 1em; color: #1976d2;">
            <strong>Centralized File Storage</strong>
          </p>

          <p style="margin-bottom: 8px; color: #555; font-weight: 500;">File Types:</p>
          <ul style="margin: 12px 0; padding-left: 20px; color: #333;">
            <li style="margin-bottom: 6px;"><strong>Uploaded Files</strong> - Documents, datasets, images you shared</li>
            <li style="margin-bottom: 6px;"><strong>Generated Outputs</strong> - Charts, plots, visualizations</li>
            <li style="margin-bottom: 6px;"><strong>Analysis Results</strong> - Reports and code files</li>
            <li style="margin-bottom: 6px;"><strong>Processed Media</strong> - Edited images and videos</li>
          </ul>

          <div style="margin-top: 16px; padding: 10px; background: #f5f5f5; border-left: 3px solid #ff6f00; border-radius: 2px;">
            <p style="margin: 0; font-size: 0.9em; color: #424242;">
              Download, preview, or reuse files across different projects
            </p>
          </div>
        </div>
      `,
    },
  },

  // ============================================
  // SECTION 6: Return to Dashboard - Workflow Feature
  // ============================================
  {
    navigateTo: '/dashboard',
    waitForNavigation: true,
    element: '.active-agents-stat-card',
    popover: {
      title: 'Multi-Agent System',
      description: `
        <div style="line-height: 1.6;">
          <p style="margin-bottom: 16px; font-size: 1em; color: #1976d2;">
            <strong>4 Specialized AI Agents</strong>
          </p>

          <div style="margin-bottom: 10px; padding: 8px; background: #fafafa; border-radius: 4px;">
            <p style="margin: 0 0 4px 0; font-weight: 600; color: #333;">Manager Agent</p>
            <p style="margin: 0; font-size: 0.9em; color: #616161; line-height: 1.5;">
              Strategic coordinator who analyzes requests, breaks down complex tasks, and delegates work to specialists
            </p>
          </div>

          <div style="margin-bottom: 10px; padding: 8px; background: #fafafa; border-radius: 4px;">
            <p style="margin: 0 0 4px 0; font-weight: 600; color: #333;">Dev Agent</p>
            <p style="margin: 0; font-size: 0.9em; color: #616161; line-height: 1.5;">
              Execution specialist handling research, data analysis, visualizations, and all 110+ tool operations
            </p>
          </div>

          <div style="margin-bottom: 10px; padding: 8px; background: #fafafa; border-radius: 4px;">
            <p style="margin: 0 0 4px 0; font-weight: 600; color: #333;">Tool Creation Agent</p>
            <p style="margin: 0; font-size: 0.9em; color: #616161; line-height: 1.5;">
              Innovation expert who designs and builds custom Python tools for unique research workflows
            </p>
          </div>

          <div style="margin-bottom: 10px; padding: 8px; background: #fafafa; border-radius: 4px;">
            <p style="margin: 0 0 4px 0; font-weight: 600; color: #333;">Critic Agent</p>
            <p style="margin: 0; font-size: 0.9em; color: #616161; line-height: 1.5;">
              Quality evaluator who assesses results, validates findings, and suggests improvements
            </p>
          </div>

          <hr style="margin: 16px 0; border: none; border-top: 1px solid #e0e0e0;" />

          <div style="padding: 10px; background: #f5f5f5; border-left: 3px solid #ff6f00; border-radius: 2px;">
            <p style="margin: 0; font-size: 0.9em; color: #424242;">
              Watch agents work in the <strong>Workflow Panel</strong> (right side when chatting) to see their strategic thinking in real-time
            </p>
          </div>
        </div>
      `,
    },
  },

  // ============================================
  // SECTION 7: Tour Complete
  // ============================================
  {
    popover: {
      title: 'Tour Complete',
      description: `
        <div style="line-height: 1.6;">
          <p style="margin-bottom: 16px; font-size: 1em; color: #1976d2;">
            <strong>You're Ready to Use LABOS</strong>
          </p>

          <p style="margin-bottom: 8px; color: #555; font-weight: 500;">Key Features Review:</p>
          <ol style="margin: 12px 0; padding-left: 20px; color: #333;">
            <li style="margin-bottom: 6px;"><strong>Projects</strong> - Organize research conversations</li>
            <li style="margin-bottom: 6px;"><strong>Tools</strong> - 110+ built-in + custom tools</li>
            <li style="margin-bottom: 6px;"><strong>Files</strong> - Centralized storage system</li>
            <li style="margin-bottom: 6px;"><strong>Workflow</strong> - Transparent AI thinking process</li>
          </ol>

          <hr style="margin: 16px 0; border: none; border-top: 1px solid #e0e0e0;" />

          <div style="padding: 10px; background: #f5f5f5; border-left: 3px solid #1976d2; border-radius: 2px;">
            <p style="margin: 0 0 8px 0; font-weight: 600; color: #333;">Need Help?</p>
            <p style="margin: 0; font-size: 0.9em; color: #616161; line-height: 1.5;">
              Click the <strong>[?]</strong> button in the top-right corner to restart this tour or view usage examples
            </p>
          </div>
        </div>
      `,
    },
  },
];

/**
 * Configuration for multi-page tour
 */
export const multiPageTourConfig = {
  animate: true,
  showProgress: true,
  progressText: 'Step {{current}} of {{total}}',

  // NO OVERLAY - completely disable the dark background
  showButtons: ['next', 'previous', 'close'],

  // Button text
  doneBtnText: 'Get Started! 🚀',
  closeBtnText: '×',
  nextBtnText: 'Next →',
  prevBtnText: '← Back',

  // Allow closing
  allowClose: true,

  // Custom styling
  popoverClass: 'labos-tour-popover',

  // Callbacks handled in component
  onDestroyed: () => {
    localStorage.setItem('labos_onboarding_completed', 'true');
  },
};
