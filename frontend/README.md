# Valorant Fantasy League - Frontend

A modern Next.js frontend for the Valorant Fantasy League application.

## Features

- **Modern UI**: Built with Next.js 14, React 18, and Tailwind CSS
- **TypeScript**: Full type safety throughout the application
- **Responsive Design**: Mobile-first responsive design with Tailwind CSS
- **Real-time Updates**: Live draft updates and scoring
- **Fantasy Features**:
  - League creation and management
  - Player drafting with timer and autopick
  - Team management and lineup setting
  - Live scoring from Champions Tour matches

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP Client**: Fetch API with Next.js rewrites
- **Date Handling**: date-fns

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn package manager

### Installation

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

### Environment Variables

Create a `.env.local` file in the root directory:

```bash
# Backend API URL (for production)
BACKEND_URL=http://backend:8000

# For development, the app will proxy to localhost:8000 by default
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Project Structure

```
src/
├── app/                 # Next.js App Router pages
│   ├── layout.tsx      # Root layout
│   ├── page.tsx        # Homepage
│   ├── globals.css     # Global styles
│   ├── leagues/        # League pages
│   └── draft/          # Draft pages
├── components/         # Reusable components (to be added)
├── lib/               # Utility functions (to be added)
└── types/             # TypeScript type definitions (to be added)
```

## Key Pages

- **Homepage** (`/`) - Welcome page with features overview
- **Leagues** (`/leagues`) - View and join fantasy leagues
- **Draft** (`/draft`) - Participate in player drafts
- **Teams** (`/teams`) - Manage your fantasy team (to be added)

## Docker Deployment

The application is containerized using Docker with multi-stage builds for optimal production size.

```bash
# Build the Docker image
docker build -t valorant-fantasy-frontend .

# Run the container
docker run -p 3000:3000 valorant-fantasy-frontend
```

## API Integration

The frontend communicates with the FastAPI backend through Next.js API rewrites. All `/api/*` requests are automatically proxied to the backend server.

## Styling

The application uses Tailwind CSS with custom Valorant-themed colors and components. Key utility classes:

- `.btn-primary` - Primary action buttons
- `.btn-secondary` - Secondary action buttons  
- `.card` - Card container
- `.player-card` - Player selection cards
- `.team-card` - Team display cards
- `.draft-timer` - Draft countdown timer

## Development Notes

- Uses Next.js App Router (not Pages Router)
- TypeScript strict mode enabled
- ESLint configured with Next.js rules
- Responsive design with mobile-first approach
- Real-time features implemented with polling (WebSocket integration planned)

## Future Enhancements

- User authentication and session management
- WebSocket integration for real-time updates
- Progressive Web App (PWA) features
- Advanced team management features
- Performance optimizations with React 18 features
