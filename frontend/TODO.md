### Valorant Fantasy League - Development Status & TODO

Last Updated: Fixed draft navigation team creation and username display

## ✅ Completed Features

### Frontend
- [x] Draft routing moved to `/leagues/[id]/draft` with proper `draftId` resolution
- [x] Dynamic draft ID and team ID resolution (no hardcoded values)
- [x] Auth guard for draft page (redirects unauthenticated users)
- [x] "Start Draft" button wired to backend and navigates correctly
- [x] League details page with member list and basic info
- [x] User authentication with JWT tokens
- [x] Join league functionality with PIN
- [x] Create league modal
- [x] Basic navbar with auth state
- [x] Added Matches page at `/matches` showing live/upcoming/completed
- [x] Added Matches link to navbar (desktop + mobile)
- [x] Added per-league My Team page at `/leagues/[id]/team` and My Team button
- [x] Fixed draft timer to read `pick_deadline` from backend
- [x] Wired available players to league-specific free agent pool
- [x] Leagues list: context-aware actions with View Details always and Go To Draft when a draft exists
- [x] Fixed draft page to display usernames instead of user IDs in draft order
- [x] Fixed "Setting up your team" stuck issue when navigating to draft from league details
- [x] Fixed draft navigation to ensure user has a team before entering draft page

### Backend
- [x] Complete authentication system with JWT
- [x] All major API routers implemented (auth, draft, league, team, user, fantasy_scores, free_agents, trade, websocket)
- [x] WebSocket endpoints for real-time updates
- [x] Live match scraping from VLR.gg
- [x] Fantasy scoring calculation system
- [x] Draft auto-pick functionality with Celery
- [x] Trade system models and endpoints
- [x] Free agents/waiver system
- [x] Database migrations with Alembic
- [x] League PIN generation and management
- [x] Draft status now returns `pick_deadline` for accurate timer

## ❌ Remaining Tasks

### MVP Frontend (must-finish)
- [ ] Team page enhancements
  - [ ] Add lineup edit controls (promote/demote starters, remove players)
  - [ ] Show lock status inline on actions
  - [ ] Add free-agent add flow (league-aware)
  
- [ ] Auth improvements
  - [ ] Change 401 redirect from `/` to `/signin` in `authenticatedFetch`
  - [ ] Add auth guards for `/leagues/*` and `/team` routes

- [ ] League management features
  - [ ] Implement "Set Draft Order" modal with drag-and-drop reordering
  - [ ] Add copy-to-clipboard for league PIN with success feedback
  - [ ] Add league leaderboard section using `api.getLeagueLeaderboard`

- [ ] TypeScript improvements
  - [ ] Create `LeagueDetails` interface to replace `any` type
  - [ ] Type all API responses properly

- [ ] UX/UI improvements
  - [ ] Replace all `alert()` calls with toast notifications system
  - [ ] Add loading states and skeleton loaders
  - [ ] Add empty states for lists and data

### Real-time features
- [ ] WebSocket integration
  - [ ] Replace 5s polling with WebSocket connection for draft updates
  - [ ] Implement real-time draft pick notifications
  - [ ] Show current turn indicator and disable UI for non-active users
  - [ ] Auto-update available players list when picks are made
  
### Draft improvements  
- [ ] Filter available players to exclude already drafted
- [ ] Add position-based filtering for draft board
- [ ] Show autopick timer countdown

### Configuration
- [ ] Environment setup
  - [ ] Create `.env.local` with proper `NEXT_PUBLIC_API_URL`
  - [ ] Document all required environment variables
  
- [ ] League settings UI
  - [ ] Add "use best 2 of 3" toggle in CreateLeagueModal
  - [ ] Add other league settings (max teams, draft timer duration)

### Additional features
- [ ] Free agents/waivers
  - [ ] Create free agents page with available players
  - [ ] Implement waiver claims UI
  - [ ] Add transaction history
  
- [ ] Trading
  - [ ] Create trade proposal interface
  - [ ] Show pending trades with accept/reject
  - [ ] Add trade history
  
- [ ] Player stats
  - [ ] Create player profile/stats page
  - [ ] Show recent match performance
  - [ ] Display season averages

### Polish & Nice-to-have
- [ ] Visual enhancements
  - [ ] Add animations for draft picks
  - [ ] Improve mobile responsiveness
  - [ ] Dark mode support
  - [ ] Better loading animations
  
- [ ] Testing
  - [ ] E2E tests for critical user flows
  - [ ] Unit tests for API utilities
  - [ ] Component tests for complex interactions
  
- [ ] Accessibility
  - [ ] ARIA labels for all interactive elements
  - [ ] Keyboard navigation for modals and dropdowns
  - [ ] Screen reader support
  
## Backend Improvements Needed

- [ ] WebSocket implementation completion
  - [ ] Finish auth integration for WebSocket connections
  - [ ] Implement draft event broadcasting
  - [ ] Add connection management and reconnection logic
  
- [ ] Performance optimizations
  - [ ] Add caching for player stats
  - [ ] Optimize draft queries
  - [ ] Add database indexes for common queries
  
- [ ] Error handling
  - [ ] Standardize error responses
  - [ ] Add proper logging
  - [ ] Implement retry logic for external API calls

- [ ] Re-enable weekly team lock enforcement (temporarily disabled for testing)
  - [ ] Restore `validate_team_not_locked` in `backend/app/utils/draft_utils.py`
  - [ ] Restore real lock status in `GET /api/teams/{team_id}/lock-status`

## Deployment Preparation

- [ ] Docker configuration
  - [ ] Verify Dockerfile configurations
  - [ ] Test docker-compose setup
  - [ ] Add health checks
  
- [ ] Production readiness
  - [ ] Set up proper CORS for production domain
  - [ ] Configure production database
  - [ ] Set up Redis for production
  - [ ] Configure Celery workers
  - [ ] SSL/TLS setup
  
- [ ] Documentation
  - [ ] API documentation
  - [ ] Deployment guide
  - [ ] User guide

## Priority Order

1. **Critical** (blocks core functionality)
   - Team page lineup editing UI
   - Auth redirect fix
   - Toast notifications
   - WebSocket-based draft updates (replace polling) and current-turn UI

2. **High** (core features)
   - WebSocket integration
   - Draft order setting
   - League leaderboard
   - TypeScript types

3. **Medium** (enhances experience)
   - Free agents UI
   - Trading UI
   - Player stats page
   - Copy PIN to clipboard

4. **Low** (nice to have)
   - Animations
   - Dark mode
   - Advanced filtering


