// Admin API utility functions with authentication
export class AdminApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'AdminApiError';
  }
}

export async function adminAuthenticatedFetch(
  url: string, 
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('adminToken');

  const baseHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const providedHeaders: Record<string, string> = (options.headers as Record<string, string>) || {};
  const headers: Record<string, string> = { ...baseHeaders, ...providedHeaders };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Token is invalid, clear it
    localStorage.removeItem('adminToken');
    window.location.href = '/admin/login';
  }

  return response;
}

export async function adminApiRequest<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await adminAuthenticatedFetch(url, options);
  
  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `Request failed with status ${response.status}`;
    
    try {
      const errorData = JSON.parse(errorText);
      errorMessage = errorData.detail || errorMessage;
    } catch {
      // If parsing fails, use the status message
      errorMessage = errorText || errorMessage;
    }
    
    throw new AdminApiError(response.status, errorMessage);
  }
  
  // Handle 204 No Content responses
  if (response.status === 204) {
    return null as T;
  }
  
  return response.json();
}

// Player management interfaces
export interface PlayerResponse {
  player_name: string;
  team: string;
  primary_role?: string;
  image_url?: string;
  total_matches: number;
  total_points: number;
  average_points: number;
  total_kills: number;
  total_assists: number;
  total_deaths: number;
}

export interface PlayerUpdate {
  team?: string;
  primary_role?: string;
  image_url?: string;
}

export interface PlayerCreate {
  player_name: string;
  team: string;
  primary_role?: string;
  image_url?: string;
}

export interface AgentResponse {
  id: number;
  name: string;
  agent_class: string;
  is_active: boolean;
  release_date?: string;
  image_url?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  agent_class: string;
  release_date?: string;
  image_url?: string;
  description?: string;
}

export interface AgentUpdate {
  agent_class?: string;
  is_active?: boolean;
  release_date?: string;
  image_url?: string;
  description?: string;
}

export interface UserAnalytics {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
  leagues_count: number;
  teams_count: number;
}

export interface LeagueAnalytics {
  id: number;
  name: string;
  description?: string;
  max_teams: number;
  current_teams: number;
  status: string;
  created_at: string;
  members_count: number;
}

export interface SystemAnalytics {
  total_users: number;
  active_users_last_30_days: number;
  total_leagues: number;
  active_leagues: number;
  total_players: number;
  total_matches: number;
  recent_registrations: Array<{
    username: string;
    created_at: string;
  }>;
}

// Player API functions
export const adminPlayerApi = {
  async getAll(
    limit = 100, 
    offset = 0, 
    teamFilter?: string, 
    roleFilter?: string
  ): Promise<PlayerResponse[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    
    if (teamFilter) params.append('team_filter', teamFilter);
    if (roleFilter) params.append('role_filter', roleFilter);
    
    return adminApiRequest<PlayerResponse[]>(`/api/admin/players?${params}`);
  },

  async create(player: PlayerCreate): Promise<PlayerResponse> {
    return adminApiRequest<PlayerResponse>('/api/admin/players', {
      method: 'POST',
      body: JSON.stringify(player),
    });
  },

  async update(playerName: string, updates: PlayerUpdate): Promise<PlayerResponse> {
    return adminApiRequest<PlayerResponse>(`/api/admin/players/${encodeURIComponent(playerName)}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  },

  async delete(playerName: string): Promise<void> {
    return adminApiRequest<void>(`/api/admin/players/${encodeURIComponent(playerName)}`, {
      method: 'DELETE',
    });
  },

  async getTopPlayers(
    limit = 10, 
    sortBy: 'total_points' | 'average_points' | 'total_kills' = 'total_points'
  ): Promise<PlayerResponse[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      sort_by: sortBy,
    });
    
    return adminApiRequest<PlayerResponse[]>(`/api/admin/analytics/players/top?${params}`);
  },
};

// User API functions
export const adminUserApi = {
  async getAll(limit = 100, offset = 0): Promise<UserAnalytics[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    
    return adminApiRequest<UserAnalytics[]>(`/api/admin/users?${params}`);
  },
};

// League API functions
export const adminLeagueApi = {
  async getAll(limit = 100, offset = 0): Promise<LeagueAnalytics[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    
    return adminApiRequest<LeagueAnalytics[]>(`/api/admin/leagues?${params}`);
  },
};

// Agent API functions
export const adminAgentApi = {
  async getAll(
    limit = 100,
    offset = 0,
    classFilter?: string,
    activeOnly = true
  ): Promise<AgentResponse[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
      active_only: activeOnly.toString(),
    });
    
    if (classFilter) params.append('class_filter', classFilter);
    
    return adminApiRequest<AgentResponse[]>(`/api/admin/agents?${params}`);
  },

  async create(agent: AgentCreate): Promise<AgentResponse> {
    return adminApiRequest<AgentResponse>('/api/admin/agents', {
      method: 'POST',
      body: JSON.stringify(agent),
    });
  },

  async update(agentId: number, updates: AgentUpdate): Promise<AgentResponse> {
    return adminApiRequest<AgentResponse>(`/api/admin/agents/${agentId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  },

  async delete(agentId: number): Promise<void> {
    return adminApiRequest<void>(`/api/admin/agents/${agentId}`, {
      method: 'DELETE',
    });
  },

  async importDefaults(): Promise<{message: string; imported_count: number}> {
    return adminApiRequest('/api/admin/agents/import-defaults', {
      method: 'POST',
    });
  },
};

// Analytics API functions
export const adminAnalyticsApi = {
  async getSystemAnalytics(): Promise<SystemAnalytics> {
    return adminApiRequest<SystemAnalytics>('/api/admin/analytics/system');
  },

  async getTeamAnalytics(): Promise<{
    team_distribution: Array<{
      team: string;
      player_count: number;
    }>;
  }> {
    return adminApiRequest('/api/admin/analytics/teams');
  },
};
