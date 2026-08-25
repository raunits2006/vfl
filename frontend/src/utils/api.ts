import {
  League,
  DraftStatus,
  DraftPick,
  DraftPickDetailed,
  Player,
  Team,
  TeamSummary,
  TeamPlayer,
  TeamPlayerWithScore,
  FantasyScore,
  LeagueLeaderboard,
  LeagueLeaderboardEnvelope,
  LiveMatch,
  MatchStatus,
  AuthToken,
  FreeAgent,
  LeagueSettings,
} from '../types/api';

// API utility functions with authentication
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('token');

  const baseHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const providedHeaders: Record<string, string> = (options.headers as Record<string, string>) || {};
  const headers: Record<string, string> = { ...baseHeaders, ...providedHeaders };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Token is invalid, clear it
      localStorage.removeItem('token');
      window.location.href = '/signin';
    }

    return response;
  } catch (_err) {
    // Network error: backend unreachable (ECONNREFUSED, DNS, etc.)
    // Return a synthetic 503 response so callers get a proper ApiError
    throw new ApiError(503, 'Backend is unreachable — server may be starting up or offline.');
  }
}

export async function apiRequest<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await authenticatedFetch(url, options);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new ApiError(response.status, errorData.detail || 'Request failed');
  }

  return response.json();
}

// Specific API functions
export const api = {
  // Leagues
  getLeagues: () => apiRequest<League[]>('/api/leagues'),
  getUserLeagues: (userId: number) => apiRequest<League[]>(`/api/leagues/user/${userId}`),
  createLeague: (data: Partial<League> & { creator_user_id?: number }) => apiRequest<League>('/api/leagues', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getLeagueDetails: (leagueId: number) => apiRequest<any>(`/api/leagues/${leagueId}/details`),
  getLeagueSettings: (leagueId: number) => apiRequest<LeagueSettings>(`/api/leagues/${leagueId}/settings`),
  updateLeagueSettings: (
    leagueId: number,
    data: Partial<{ max_players: number; starting_players: number; bench_players: number; points_per_kill: number; points_per_assist: number; use_best_2_of_3: boolean; draft_type: string; agent_exact_match_multiplier: number; agent_class_match_multiplier: number; agent_miss_multiplier: number }>
  ) => apiRequest<LeagueSettings>(`/api/leagues/${leagueId}/settings`, { method: 'PUT', body: JSON.stringify(data) }),

  // Commissioner management
  setCommissionerStatus: (leagueId: number, userId: number, isCommissioner: boolean) =>
    apiRequest<{ user_id: number; is_commissioner: boolean }>(`/api/leagues/${leagueId}/members/${userId}/commissioner`, {
      method: 'PUT',
      body: JSON.stringify({ is_commissioner: isCommissioner }),
    }),
  regenerateLeaguePin: (leagueId: number) => apiRequest<{ join_pin: string }>(`/api/leagues/${leagueId}/regenerate-pin`, { method: 'POST' }),
  joinLeague: (leagueId: number, userId: number, pin?: string) => apiRequest<void>(`/api/leagues/${leagueId}/join`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, pin }),
  }),
  joinByPin: (userId: number, pin: string) => apiRequest<{ message: string; league_id: number }>(`/api/leagues/join-by-pin`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, pin }),
  }),

  // Players
  getPlayers: () => apiRequest<Player[]>('/api/players'),

  // Draft
  getDraftStatus: (draftId: number) => apiRequest<DraftStatus>(`/api/drafts/${draftId}/status`),
  getDraftByLeague: (leagueId: number) => apiRequest<DraftStatus>(`/api/drafts/by-league/${leagueId}`),
  startDraft: (leagueId: number) => apiRequest<DraftStatus>(`/api/drafts/start`, {
    method: 'POST',
    body: JSON.stringify({ league_id: leagueId }),
  }),
  getDraftPicks: (draftId: number) => apiRequest<DraftPick[]>(`/api/drafts/${draftId}/results`),
  getDraftResults: (draftId: number) => apiRequest<DraftPickDetailed[]>(`/api/drafts/${draftId}/results`),
  resetDraft: (draftId: number) => apiRequest<{ message: string }>(`/api/drafts/${draftId}/reset`, { method: 'POST' }),
  setDraftOrder: (draftId: number, userIds: number[], randomize: boolean = false) =>
    apiRequest<{ draft_id: number; draft_order: number[] }>(`/api/drafts/${draftId}/order`, {
      method: 'POST',
      body: JSON.stringify({ user_ids: userIds, randomize }),
    }),
  makeDraftPick: (draftId: number, teamId: number, playerName: string) =>
    apiRequest<DraftPick>(`/api/drafts/${draftId}/pick`, {
      method: 'POST',
      body: JSON.stringify({ team_id: teamId, player_name: playerName }),
    }),

  // Teams
  getTeam: (teamId: number) => apiRequest<TeamSummary>(`/api/teams/${teamId}`),
  getTeamPlayers: (teamId: number) => apiRequest<TeamPlayer[]>(`/api/teams/${teamId}/players`),
  getUserTeamByLeague: (leagueId: number, userId: number) => apiRequest<TeamSummary>(`/api/teams/user-team?league_id=${leagueId}&user_id=${userId}`),
  createTeam: (leagueId: number, userId: number, name: string) => apiRequest<TeamSummary>(`/api/teams`, {
    method: 'POST',
    body: JSON.stringify({ league_id: leagueId, user_id: userId, name }),
  }),
  addTeamPlayer: (teamId: number, playerName: string, isStarting = false) =>
    apiRequest<TeamPlayer>(`/api/teams/${teamId}/players`, {
      method: 'POST',
      body: JSON.stringify({ player_name: playerName, is_starting: isStarting }),
    }),
  setTeamLineup: (teamId: number, startingPlayers: string[], benchPlayers: string[]) =>
    apiRequest<{ message: string }>(`/api/teams/${teamId}/lineup`, {
      method: 'PUT',
      body: JSON.stringify({ starting_players: startingPlayers, bench_players: benchPlayers }),
    }),
  removeTeamPlayer: (teamId: number, playerName: string) =>
    apiRequest<{ message: string }>(`/api/teams/${teamId}/players/${encodeURIComponent(playerName)}`, {
      method: 'DELETE',
    }),
  getTeamLockStatus: (teamId: number) =>
    apiRequest<{ is_locked: boolean; message: string; next_match_time?: string | null; lock_reason?: string | null }>(`/api/teams/${teamId}/lock-status`),
  togglePlayerStartingStatus: (teamId: number, playerName: string) =>
    apiRequest<TeamPlayer>(`/api/teams/${teamId}/players/${encodeURIComponent(playerName)}/toggle-starter`, {
      method: 'PATCH',
    }),
  getAgentPredictions: (teamId: number) => apiRequest<Array<{ team_id: number; player_name: string; picks: string[]; updated_at: string }>>(`/api/teams/${teamId}/agent-predictions`),
  setAgentPrediction: (teamId: number, playerName: string, picks: string[]) => apiRequest<{ team_id: number; player_name: string; picks: string[]; updated_at: string }>(`/api/teams/${teamId}/agent-predictions`, {
    method: 'POST',
    body: JSON.stringify({ player_name: playerName, picks }),
  }),
  renameTeam: (teamId: number, name: string) => apiRequest<TeamSummary>(`/api/teams/${teamId}/rename`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  }),
  getTeamPlayerScores: (teamId: number) => apiRequest<TeamPlayerWithScore[]>(`/api/teams/${teamId}/player-scores`),
  swapPlayers: (teamId: number, benchPlayer: string, starterPlayer: string) =>
    apiRequest<{ message: string; promoted_player: TeamPlayer; demoted_player: TeamPlayer }>(
      `/api/teams/${teamId}/swap-players`,
      {
        method: 'POST',
        body: JSON.stringify({ bench_player: benchPlayer, starter_player: starterPlayer }),
      }
    ),

  // Fantasy Scores
  getLeagueLeaderboardCurrentEvent: (leagueId: number) => apiRequest<LeagueLeaderboardEnvelope>(`/api/fantasy/leagues/${leagueId}/leaderboard`),
  getLeagueLeaderboardWeekly: (leagueId: number, days = 7) => apiRequest<LeagueLeaderboardEnvelope>(`/api/fantasy/leagues/${leagueId}/leaderboard/weekly?days=${days}`),
  getLeagueLeaderboardSeason: (leagueId: number, year?: number) => apiRequest<LeagueLeaderboardEnvelope>(`/api/fantasy/leagues/${leagueId}/leaderboard/season${year ? `?year=${year}` : ''}`),
  getPlayerStats: (playerName: string) => apiRequest<FantasyScore>(`/api/fantasy/players/${playerName}/stats`),
  getLiveMatches: () => apiRequest<LiveMatch[]>('/api/fantasy/matches/live'),
  getMatchesWithStatus: () => apiRequest<MatchStatus[]>('/api/fantasy/matches'),

  // Free Agents / Player Pool (league-aware available players)
  getFreeAgentPool: (leagueId: number) => apiRequest<FreeAgent[]>(`/api/free-agents/${leagueId}/pool`),
  swapFreeAgent: (leagueId: number, teamId: number, dropPlayerName: string, addPlayerName: string) =>
    apiRequest<{ success: boolean; message: string; dropped_player: string; added_player: string; transaction_date: string }>(
      `/api/free-agents/${leagueId}/swap`,
      {
        method: 'POST',
        body: JSON.stringify({ team_id: teamId, drop_player_name: dropPlayerName, add_player_name: addPlayerName }),
      }
    ),
  addFreeAgent: (leagueId: number, teamId: number, addPlayerName: string) =>
    apiRequest<{ success: boolean; message: string; added_player: string; transaction_date: string }>(
      `/api/free-agents/${leagueId}/add`,
      { method: 'POST', body: JSON.stringify({ team_id: teamId, add_player_name: addPlayerName }) }
    ),
  dropPlayer: (leagueId: number, teamId: number, dropPlayerName: string) =>
    apiRequest<{ success: boolean; message: string; dropped_player: string; transaction_date: string }>(
      `/api/free-agents/${leagueId}/drop`,
      { method: 'POST', body: JSON.stringify({ team_id: teamId, drop_player_name: dropPlayerName }) }
    ),
  // Trades
  proposeTrade: (
    leagueId: number,
    offeringTeamId: number,
    receivingTeamId: number,
    offeringPlayers: string[],
    receivingPlayers: string[]
  ) => apiRequest<{ id: number }>(`/api/trades/${leagueId}/propose`, {
    method: 'POST',
    body: JSON.stringify({
      offering_team_id: offeringTeamId,
      receiving_team_id: receivingTeamId,
      offering_players: offeringPlayers,
      receiving_players: receivingPlayers,
    }),
  }),
  getLeagueTrades: (leagueId: number) => apiRequest<any[]>(`/api/trades/${leagueId}`),
  getTeamTrades: (teamId: number) => apiRequest<any[]>(`/api/trades/team/${teamId}`),
  acceptTrade: (tradeId: number) => apiRequest<{ message: string }>(`/api/trades/${tradeId}/accept`, { method: 'PUT' }),
  rejectTrade: (tradeId: number) => apiRequest<{ message: string }>(`/api/trades/${tradeId}/reject`, { method: 'PUT' }),
  cancelTrade: (tradeId: number) => apiRequest<{ message: string }>(`/api/trades/${tradeId}/cancel`, { method: 'PUT' }),

  // League activity (free agents)
  getLeagueTransactions: (leagueId: number) =>
    apiRequest<Array<{ id: number; team_id: number; player_name: string; transaction_type: string; transaction_date: string }>>(
      `/api/free-agents/${leagueId}/transactions`
    ),
};
