// API Response Types
export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
}

export interface League {
  id: number;
  name: string;
  description?: string;
  max_teams: number;
  status: string;
  created_at: string;
  member_count: number;
  join_pin?: string;
}

export interface DraftStatus {
  draft_id: number;
  league_id: number;
  status: string;
  current_pick: number;
  current_user_id: number;
  started_at: string;
  pick_deadline?: string | null;
  completed_at?: string;
}

export interface DraftPick {
  id: number;
  player_name: string;
  team_id: number;
  pick_number: number;
  picked_at: string;
}

export interface DraftPickDetailed {
  id: number;
  draft_session_id: number;
  team_id: number;
  team_name: string;
  username: string;
  player_name: string;
  player_team: string;
  pick_number: number;
  picked_at: string;
}

export interface Player {
  id: number;
  player_name: string;
  team_name: string;
  role: string;
}

export interface Team {
  id: number;
  name: string;
  league_id: number;
  user_id: number;
  created_at: string;
}

// Enriched summary returned by GET /api/teams/user-team
export interface TeamSummary extends Team {
  player_count: number;
  starting_players: number;
  bench_players: number;
}

export interface TeamPlayer {
  id: number;
  player_name: string;
  team: string;
  is_starting: boolean;
  added_at: string;
}

export interface TeamPlayerWithScore {
  player_name: string;
  team: string;  // Valorant team
  is_starting: boolean;
  total_points: number;
  agent_predictions: string[];  // 3 agent names or empty
  agent_classes: string[];      // corresponding classes
}

export interface FantasyScore {
  player_name: string;
  event_id: number;
  total_score: number;
  kills: number;
  deaths: number;
  assists: number;
  adr: number;
  rating: number;
}

export interface LeagueLeaderboard {
  team_id: number;
  team_name: string;
  username?: string;
  user_id: number;
  total_score: number;
  player_count: number;
  average_player_score: number;
  top_player?: string | null;
  top_player_score?: number | null;
}

export interface LeagueLeaderboardEnvelope {
  league_id: number;
  league_name: string;
  teams: LeagueLeaderboard[];
  last_updated: string;
}

export interface LiveMatch {
  match_id: number;
  team1: string;
  team2: string;
  current_map: string;
  team1_score: string;
  team2_score: string;
  live_player_scores: Array<{
    player_name: string;
    map_name: string;
    agent: string | null;
    kills: number;
    deaths: number;
    assists: number;
    score: number;
  }>;
}

export interface MatchStatus {
  match_id: number;
  team1: string;
  team2: string;
  match_event: string;
  scheduled_time: number; // unix timestamp (seconds)
  status: 'upcoming' | 'live' | 'completed';
  time_until_match?: number | null;
  match_page: string;
  last_scraped?: string | null;
  has_live_data: boolean;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface FreeAgent {
  player_name: string;
  team: string;
  primary_role?: string;
  image_url?: string | null;
}

export interface LeagueSettings {
  max_players: number;
  starting_players: number;
  bench_players: number;
  points_per_kill: number;
  points_per_assist: number;
  use_best_2_of_3: boolean;
  draft_type: string;
  agent_exact_match_multiplier: number;
  agent_class_match_multiplier: number;
  agent_miss_multiplier: number;
  max_duelist_agent_players: number;
}
