# LABOS AI Frontend

Next.js frontend for LABOS (Self-Evolving Intelligent Laboratory Assistant) - Advanced AI for biomedical research.

## 🚀 Quick Start

### Prerequisites

#### Install Node.js and npm

**macOS:**
```bash
# Using Homebrew
brew install node

# Verify installation
node --version  # Should be 18+
npm --version
```

**Windows:**
1. Download Node.js installer from [nodejs.org](https://nodejs.org/)
2. Run the installer (includes npm automatically)
3. Verify installation in PowerShell/CMD:
   ```bash
   node --version  # Should be 18+
   npm --version
   ```

**Linux (Ubuntu/Debian):**
```bash
# Using NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

**Linux (using nvm - recommended):**
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Install Node.js
nvm install 18
nvm use 18
```

#### Other Prerequisites
- LABOS Backend running on port 18800 (see [Backend README](../labos-be/README.md))

### Installation

1. **Clone repository and navigate to frontend directory:**
   ```bash
   git clone <repository-url>
   cd labos-fe
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Open in browser:**
   ```
   http://localhost:3000
   ```

## 📦 Available Scripts

- `npm run dev` - Start development server with Turbopack
- `npm run build` - Build for production with Turbopack
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## 🏗️ Architecture

### Tech Stack

- **Framework:** Next.js 14 with App Router
- **Build Tool:** Turbopack (faster than Webpack)
- **UI Components:** Ant Design 5.27+
- **Styling:** Tailwind CSS + CSS Modules
- **State Management:** Zustand
- **HTTP Client:** Axios
- **Real-time Communication:** WebSocket
- **Language:** TypeScript

### Project Structure

```
labos-fe/
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── layout.tsx       # Root layout with Ant Design theme
│   │   ├── page.tsx         # Homepage (redirects to Dashboard)
│   │   ├── dashboard/       # Dashboard page
│   │   ├── chat/           # Chat interface
│   │   ├── tools/          # Tools management
│   │   ├── files/          # File management
│   │   ├── memory/         # Memory/Knowledge base
│   │   └── settings/       # Settings
│   ├── components/         # Reusable components
│   │   ├── Layout/         # Main layout components
│   │   ├── DualPaneChatComponent.tsx  # Chat interface
│   │   └── WorkflowPanel.tsx          # Real-time workflow display
│   ├── stores/             # Zustand state stores
│   ├── hooks/              # Custom React hooks
│   └── styles/             # Global styles
├── public/                 # Static assets
├── next.config.js          # Next.js configuration with API proxy
├── package.json            # Dependencies and scripts
├── tailwind.config.js      # Tailwind CSS configuration
└── tsconfig.json          # TypeScript configuration
```

## 🔧 Configuration

### API Proxy

The frontend automatically proxies API requests to the backend:
- Frontend: `http://localhost:3000/api/*`
- Backend: `http://localhost:18800/api/*`

### Theme Configuration

Dark theme is configured in `src/app/layout.tsx` using Ant Design's `ConfigProvider`:
- Primary color: `#0ea5e9` (sky blue)
- Background: `#0f172a` (dark blue)
- Container background: `#1e293b` (slate)

### Environment Variables

Create `.env.local` for custom configuration:
```bash
# Backend API URL (default: http://localhost:18800)
NEXT_PUBLIC_API_URL=http://localhost:18800

# WebSocket URL (default: ws://localhost:18800)
NEXT_PUBLIC_WS_URL=ws://localhost:18800
```

## 🌐 Features

### 🎯 Main Pages

- **Dashboard** - System status, quick actions, recent activity
- **Chat** - Interactive AI conversation with dual-pane layout
- **Tools** - Tool management and creation
- **Files** - File upload, management, and processing
- **Memory** - Knowledge base and memory management
- **Settings** - Configuration and preferences

### 🔄 Real-time Features

- **WebSocket Integration** - Real-time workflow updates
- **Live Status** - Backend connectivity monitoring
- **Instant Updates** - Workflow steps, progress, and system status

### 🎨 UI/UX Features

- **Dark Theme** - Consistent dark mode throughout
- **Responsive Design** - Works on desktop and mobile
- **Loading States** - Smooth loading indicators
- **Error Handling** - Graceful error displays
- **Accessibility** - ARIA labels and keyboard navigation

## 🔌 Backend Integration

### API Endpoints

The frontend connects to these backend endpoints:

- `GET /api/system/health` - System health check
- `POST /api/chat/send` - Send chat messages
- `GET /api/agents` - Get agent list
- `GET /api/tools` - Get tool list
- `WebSocket /ws` - Real-time updates

### State Management

Uses Zustand for global state:
- Connection status
- Theme preferences
- User settings
- Chat history

## 🐛 Troubleshooting

### Common Issues

1. **"System Offline" status:**
   - Ensure backend is running on port 18800
   - Check `curl http://localhost:18800/api/system/health`

2. **WebSocket connection errors:**
   - Backend must be running
   - Check browser console for detailed errors
   - Try refreshing the page

3. **Build/compilation errors:**
   - Clear Next.js cache: `rm -rf .next`
   - Reinstall dependencies: `rm -rf node_modules && npm install`

4. **Turbopack issues:**
   - Ensure Next.js 14+ is installed
   - Check for conflicting webpack configurations

### Development Tips

- Use `npm run dev` for hot reloading
- Check browser console for WebSocket connection logs
- Backend health status is displayed in the dashboard
- Use React DevTools for component debugging

## 🔧 Development

### Code Style

- TypeScript for type safety
- Functional components with hooks
- Consistent naming conventions
- ESLint for code quality

### Adding New Pages

1. Create page component in `src/app/[page-name]/page.tsx`
2. Wrap with `Layout` component for consistent UI
3. Add navigation link in `src/components/Layout/Layout.tsx`

### Adding New Components

1. Create component in `src/components/`
2. Use TypeScript interfaces for props
3. Follow Ant Design design system
4. Add proper error handling

## 📚 Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [Ant Design Components](https://ant.design/components/overview/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Zustand State Management](https://github.com/pmndrs/zustand)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is part of the LABOS AI system for biomedical research.