'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { Clock, User, Trophy, ListOrdered, ChevronUp, ChevronDown, Users } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { api, apiRequest } from '../../utils/api';
import { useToast } from '../../components/ToastProvider';
import { DraftPick, DraftStatus, Player, Team, TeamSummary, FreeAgent, TeamPlayer } from '../../types/api';
import { useSearchParams, useRouter } from 'next/navigation';

export default function DraftPage() {
  const { user, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialDraftId = Number(searchParams.get('draftId')) || undefined;
  const { showToast } = useToast();
  const wsRef = useRef<WebSocket | null>(null);
  const [draftStatus, setDraftStatus] = useState<DraftStatus | null>(null);
  const [draftPicks, setDraftPicks] = useState<DraftPick[]>([]);
  const [draftOrder, setDraftOrder] = useState<number[] | null>(null);
  const [usernamesById, setUsernamesById] = useState<Record<number, string>>({});
  const [availablePlayers, setAvailablePlayers] = useState<Array<Player | FreeAgent>>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<string>('');
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  // DraftId loaded from query param; if missing, we'll try to infer from leagueId param later
  const [draftId, setDraftId] = useState<number | undefined>(initialDraftId);
  const [team, setTeam] = useState<TeamSummary | null>(null);
  const [creatingTeam, setCreatingTeam] = useState(false);
  const [teamPlayers, setTeamPlayers] = useState<TeamPlayer[]>([]);
  const [showRoster, setShowRoster] = useState(false);

  // Update draftId when query param changes (router.replace adds it asynchronously)
  useEffect(() => {
    const qp = searchParams.get('draftId');
    if (qp) {
      const id = Number(qp);
      if (!Number.isNaN(id)) {
        setDraftId(id);
      }
    }
  }, [searchParams]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace('/signin');
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    if (!draftId || authLoading) return;
    fetchDraftStatus(draftId);
    fetchDraftPicks(draftId);
    // Connect WebSocket for live updates
    try {
      const token = localStorage.getItem('token');
      if (token) {
        const buildWsBase = () => {
          // Prefer explicit public backend URL if provided
          const backendUrl = (process.env.NEXT_PUBLIC_BACKEND_URL as string | undefined) || undefined;
          if (backendUrl) {
            try {
              const u = new URL(backendUrl);
              u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
              return u.origin;
            } catch { }
          }
          // Fallback: if frontend on 3000, assume backend on 8000
          const isHttps = window.location.protocol === 'https:';
          const host = window.location.hostname;
          const port = window.location.port === '3000' ? '8000' : window.location.port;
          return `${isHttps ? 'wss' : 'ws'}://${host}${port ? `:${port}` : ''}`;
        };

        const wsBase = buildWsBase();
        const wsUrl = `${wsBase}/ws/draft/${draftId}?token=${encodeURIComponent(token)}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        ws.onopen = () => {
          // Optionally request current state
          ws.send(JSON.stringify({ type: 'get_draft_state' }));
        };
        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'draft_state') {
              setDraftStatus(prev => ({
                ...(prev || {} as any), ...{
                  draft_id: draftId,
                  league_id: message.league_id || (prev?.league_id ?? undefined),
                  status: message.status,
                  current_pick: message.current_pick,
                  current_user_id: message.current_user_id,
                  pick_deadline: message.pick_deadline,
                }
              }));
            } else if (message.type === 'draft_pick') {
              // Update picks list and status
              fetchDraftPicks(draftId);
              fetchDraftStatus(draftId);
            } else if (message.type === 'user_joined' || message.type === 'user_left') {
              // Optional: show toast for join/leave
              // showToast(`${message.type === 'user_joined' ? 'User joined' : 'User left'}`, { type: 'info' });
            } else if (message.type === 'error') {
              showToast(message.message || 'WebSocket error', { type: 'error' });
            }
          } catch { }
        };
        ws.onerror = () => {
          showToast('Draft live connection error', { type: 'warning' });
        };
        ws.onclose = () => {
          wsRef.current = null;
        };
      }
    } catch { }

    // Fallback polling in case websocket doesn't deliver updates
    const poll = setInterval(() => {
      fetchDraftStatus(draftId);
      fetchDraftPicks(draftId);
    }, 3000);

    return () => {
      clearInterval(poll);
      if (wsRef.current) {
        try { wsRef.current.close(); } catch { }
        wsRef.current = null;
      }
    };
  }, [draftId, authLoading]);

  // If no draftId after auth loads, stop showing spinner and render fallback
  useEffect(() => {
    if (!authLoading && !draftId) {
      setLoading(false);
    }
  }, [authLoading, draftId]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (!draftStatus?.pick_deadline) return;
      const deadlineMs = new Date(draftStatus.pick_deadline).getTime();
      const remainingSec = Math.max(0, Math.floor((deadlineMs - Date.now()) / 1000));
      // Clamp to 60 seconds to avoid any clock skew / timezone parsing anomalies
      setTimeRemaining(Math.min(remainingSec, 60));
    }, 1000);
    return () => clearInterval(timer);
  }, [draftStatus?.pick_deadline]);

  const fetchDraftStatus = async (id: number) => {
    try {
      const status = await api.getDraftStatus(id);
      setDraftStatus(status);
      // Use pick_deadline from server for accurate timer
      if (status.pick_deadline) {
        const deadlineMs = new Date(status.pick_deadline).getTime();
        const remainingSec = Math.max(0, Math.floor((deadlineMs - Date.now()) / 1000));
        setTimeRemaining(Math.min(remainingSec, 60));
      } else {
        setTimeRemaining(0);
      }
      if (user && (!team || team.league_id !== status.league_id)) {
        try {
          const t = await api.getUserTeamByLeague(status.league_id, user.id);
          console.log('Fetched team:', t);
          setTeam(t);
          // Fetch team players when we get the team
          fetchTeamPlayers(t.id);
        } catch (err) {
          console.error('Failed to fetch team:', err);
          // No team found; create one on the fly for legacy members
          try {
            const defaultName = `${user.username}'s Team`;
            const created = await api.createTeam(status.league_id, user.id, defaultName);
            console.log('Created team:', created);
            setTeam(created);
          } catch (e2) {
            console.error('Failed to create team:', e2);
            // Leave team as null; UI will remain disabled
          }
        }
      }
    } catch (error) {
      console.error('Error fetching draft status:', error);
      // Show toast notification for specific errors
      if (error instanceof Error) {
        if (error.message.includes('Failed to auto-initialize draft order')) {
          showToast('Failed to initialize draft order. Please contact the league commissioner.', {
            type: 'error',
            title: 'Draft Error'
          });
        } else if (error.message.includes('Draft not found')) {
          showToast('Draft not found. Please check the URL or contact support.', {
            type: 'error',
            title: 'Draft Error'
          });
        } else {
          showToast('Failed to load draft status. Please try refreshing the page.', {
            type: 'error',
            title: 'Connection Error'
          });
        }
      } else {
        showToast('An unexpected error occurred while loading the draft.', {
          type: 'error',
          title: 'Error'
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchDraftPicks = async (id: number) => {
    try {
      const picks = await api.getDraftPicks(id);
      setDraftPicks(picks);
    } catch (error) {
      console.error('Error fetching draft picks:', error);
    }
  };

  const fetchDraftOrder = async (id: number) => {
    try {
      const res = await apiRequest<{ draft_id: number; draft_order: number[] }>(`/api/drafts/${id}/order`);
      setDraftOrder(res.draft_order);
    } catch (error) {
      // Order may not be set yet
      setDraftOrder(null);
    }
  };

  const fetchLeagueMembers = async (leagueId: number) => {
    try {
      const details = await api.getLeagueDetails(leagueId);
      const map: Record<number, string> = {};
      for (const m of details.members || []) {
        map[m.user_id] = m.username;
      }
      setUsernamesById(map);
    } catch { }
  };

  const fetchAvailablePlayers = async () => {
    try {
      if (!draftStatus?.league_id) return; // wait until we know league
      const freeAgents = await api.getFreeAgentPool(draftStatus.league_id);
      setAvailablePlayers(freeAgents);
    } catch (error) {
      console.error('Error fetching players:', error);
    }
  };

  // Load available players once we know the league id from draft status
  useEffect(() => {
    if (draftStatus?.league_id && draftId) {
      fetchAvailablePlayers();
      fetchDraftOrder(draftId);
      fetchLeagueMembers(draftStatus.league_id);
    }
  }, [draftStatus?.league_id, draftId]);

  // Ensure team is loaded when we have user and draft status
  useEffect(() => {
    if (user && draftStatus?.league_id && !team) {
      console.log('Fetching team for user:', user.id, 'league:', draftStatus.league_id);
      api.getUserTeamByLeague(draftStatus.league_id, user.id)
        .then(t => {
          console.log('Team fetched in separate effect:', t);
          setTeam(t);
        })
        .catch(err => {
          console.error('Team fetch error in separate effect:', err);
          // Try to create team
          const defaultName = `${user.username}'s Team`;
          api.createTeam(draftStatus.league_id, user.id, defaultName)
            .then(created => {
              console.log('Team created in separate effect:', created);
              setTeam(created);
              fetchTeamPlayers(created.id);
            })
            .catch(e2 => console.error('Team creation failed:', e2));
        });
    }
  }, [user, draftStatus?.league_id, team]);

  const fetchTeamPlayers = async (teamId: number) => {
    try {
      const players = await api.getTeamPlayers(teamId);
      setTeamPlayers(players);
    } catch (error) {
      console.error('Error fetching team players:', error);
    }
  };

  const handleTogglePlayer = async (player: TeamPlayer) => {
    if (!team) return;

    try {
      const updatedPlayer = await api.togglePlayerStartingStatus(team.id, player.player_name);
      // Update the local players array with the new status
      setTeamPlayers(prevPlayers =>
        prevPlayers.map(p =>
          p.id === player.id ? { ...p, is_starting: updatedPlayer.is_starting } : p
        )
      );
    } catch (error) {
      console.error('Error toggling player status:', error);
      const message = (error as any)?.message || 'Failed to update player status. Please try again.';
      showToast(message, { type: 'error' });
    }
  };

  const starters = useMemo(() => teamPlayers.filter(p => p.is_starting), [teamPlayers]);
  const bench = useMemo(() => teamPlayers.filter(p => !p.is_starting), [teamPlayers]);

  const makePick = async () => {
    if (!selectedPlayer || !user || !draftId || !team) return;

    try {
      await api.makeDraftPick(draftId, team.id, selectedPlayer);

      // Immediately remove the picked player from local state for instant UI feedback
      setAvailablePlayers(prevPlayers =>
        prevPlayers.filter(player => player.player_name !== selectedPlayer)
      );

      setSelectedPlayer('');

      // Refresh data with a slight delay to ensure database transaction is committed
      setTimeout(() => {
        fetchDraftStatus(draftId);
        fetchDraftPicks(draftId);
        fetchAvailablePlayers(); // This will correct any discrepancies
        fetchTeamPlayers(team.id);
      }, 500);
    } catch (error) {
      console.error('Error making pick:', error);
      const message = (error as any)?.message || 'Failed to make pick. Please try again.';
      showToast(message, { type: 'error' });
      // If the pick failed, we should refresh to get the correct state
      fetchAvailablePlayers();
    }
  };

  const createMyTeam = async () => {
    if (!user || !draftStatus?.league_id) return;
    try {
      setCreatingTeam(true);
      const defaultName = `${user.username}'s Team`;
      const t = await api.createTeam(draftStatus.league_id, user.id, defaultName);
      setTeam(t);
    } catch (e) {
      console.error('Error creating team', e);
      showToast('Failed to create team. Please ensure you joined the league.', { type: 'error' });
    } finally {
      setCreatingTeam(false);
    }
  };

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-valorant-600"></div>
      </div>
    );
  }

  if (!draftId) {
    return (
      <div className="card">
        <h2 className="text-xl font-bold mb-2">No draft found</h2>
        <p className="text-gray-600">This league has no active draft yet. Start the draft from the league page.</p>
      </div>
    );
  }

  // Show different UI for completed drafts
  if (draftStatus?.status === 'COMPLETED') {
    return (
      <div className="space-y-6">
        <div className="card">
          <div className="text-center">
            <Trophy className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold mb-2">Draft Complete!</h1>
            <p className="text-gray-600 mb-6">
              The draft for this league has been completed. You can now manage your roster and prepare for the season.
            </p>
          </div>
        </div>

        {/* Show final draft results */}
        <div className="card">
          <h2 className="text-xl font-bold mb-4">Final Draft Results</h2>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {draftPicks.map((pick) => (
              <div key={pick.id} className="flex justify-between items-center p-2 border rounded">
                <div>
                  <p className="font-medium text-sm">{pick.player_name}</p>
                  <p className="text-xs text-gray-600">Pick #{pick.pick_number}</p>
                </div>
                <div className="flex items-center">
                  <User className="h-4 w-4 mr-1 text-gray-400" />
                  <span className="text-xs">Team {pick.team_id}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Show roster management if user has players */}
        {teamPlayers.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="text-xl font-semibold mb-4 flex items-center">
                <Users className="h-5 w-5 mr-2 text-green-600" />
                Your Starters ({starters.length})
              </h3>
              {starters.length === 0 ? (
                <p className="text-gray-600">No starters set. Move players from bench to set your lineup.</p>
              ) : (
                <ul className="divide-y divide-gray-800/50">
                  {starters.map(p => (
                    <li key={p.id} className="py-3 flex items-center justify-between">
                      <div>
                        <div className="font-medium">{p.player_name}</div>
                        <div className="text-sm text-gray-500">{p.team}</div>
                      </div>
                      <button
                        onClick={() => handleTogglePlayer(p)}
                        className="flex items-center px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                        title="Move to bench"
                      >
                        <ChevronDown className="h-4 w-4 mr-1" />
                        Bench
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card">
              <h3 className="text-xl font-semibold mb-4 flex items-center">
                <Users className="h-5 w-5 mr-2 text-blue-600" />
                Your Bench ({bench.length})
              </h3>
              {bench.length === 0 ? (
                <p className="text-gray-600">No bench players.</p>
              ) : (
                <ul className="divide-y divide-gray-800/50">
                  {bench.map(p => (
                    <li key={p.id} className="py-3 flex items-center justify-between">
                      <div>
                        <div className="font-medium">{p.player_name}</div>
                        <div className="text-sm text-gray-500">{p.team}</div>
                      </div>
                      <button
                        onClick={() => handleTogglePlayer(p)}
                        className="flex items-center px-2 py-1 text-sm bg-green-100 hover:bg-green-200 text-green-700 rounded transition-colors"
                        title="Promote to starter"
                      >
                        <ChevronUp className="h-4 w-4 mr-1" />
                        Start
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Toggle between Draft and Roster views */}
      {teamPlayers.length > 0 && (
        <div className="flex justify-center">
          <div className="bg-gray-100 p-1 rounded-lg inline-flex">
            <button
              onClick={() => setShowRoster(false)}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${!showRoster
                  ? 'bg-valorant-600 text-white'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              Draft Board
            </button>
            <button
              onClick={() => setShowRoster(true)}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${showRoster
                  ? 'bg-valorant-600 text-white'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              My Roster ({teamPlayers.length})
            </button>
          </div>
        </div>
      )}

      {showRoster ? (
        // Roster Management View
        <div className="space-y-6">
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold">My Team</h2>
                <p className="text-gray-600">{team?.name || 'My Team'}</p>
              </div>
              <div className="text-sm text-gray-500">
                {teamPlayers.length} total players
              </div>
            </div>
            <p className="text-gray-600 mt-4">
              Manage your starting lineup. Players in the starting lineup will score points for your team.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="text-xl font-semibold mb-4 flex items-center">
                <Users className="h-5 w-5 mr-2 text-green-600" />
                Starters ({starters.length})
              </h3>
              {starters.length === 0 ? (
                <p className="text-gray-600">No starters set. Move players from bench to set your lineup.</p>
              ) : (
                <ul className="divide-y divide-gray-800/50">
                  {starters.map(p => (
                    <li key={p.id} className="py-3 flex items-center justify-between">
                      <div>
                        <div className="font-medium">{p.player_name}</div>
                        <div className="text-sm text-gray-500">{p.team}</div>
                      </div>
                      <button
                        onClick={() => handleTogglePlayer(p)}
                        className="flex items-center px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                        title="Move to bench"
                      >
                        <ChevronDown className="h-4 w-4 mr-1" />
                        Bench
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card">
              <h3 className="text-xl font-semibold mb-4 flex items-center">
                <Users className="h-5 w-5 mr-2 text-blue-600" />
                Bench ({bench.length})
              </h3>
              {bench.length === 0 ? (
                <p className="text-gray-600">No bench players.</p>
              ) : (
                <ul className="divide-y divide-gray-800/50">
                  {bench.map(p => (
                    <li key={p.id} className="py-3 flex items-center justify-between">
                      <div>
                        <div className="font-medium">{p.player_name}</div>
                        <div className="text-sm text-gray-500">{p.team}</div>
                      </div>
                      <button
                        onClick={() => handleTogglePlayer(p)}
                        className="flex items-center px-2 py-1 text-sm bg-green-100 hover:bg-green-200 text-green-700 rounded transition-colors"
                        title="Promote to starter"
                      >
                        <ChevronUp className="h-4 w-4 mr-1" />
                        Start
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      ) : (
        // Draft Board View
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Draft Status */}
          <div className="lg:col-span-3">
            <div className="card">
              <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold">Fantasy Draft</h1>
                {draftStatus && (
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center">
                      <Clock className="h-5 w-5 mr-2 text-valorant-600" />
                      <span className="font-medium">{formatTime(timeRemaining)}</span>
                    </div>
                    <div className="flex items-center">
                      <Trophy className="h-5 w-5 mr-2 text-valorant-600" />
                      <span>Pick #{draftStatus.current_pick}</span>
                    </div>
                  </div>
                )}
              </div>

              {timeRemaining > 0 && (
                <div className="mt-4 draft-timer">
                  <p className="font-medium">Time remaining for current pick: {formatTime(timeRemaining)}</p>
                </div>
              )}
            </div>
          </div>

          {/* Available Players */}
          <div className="lg:col-span-2">
            <div className="card">
              <h2 className="text-xl font-bold mb-4">Available Players</h2>
              {/* Team is now auto-created on league join; we can show a minimal note if still missing */}
              {!team && user && draftStatus?.league_id && (
                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded">
                  <p>Setting up your team... If this persists, refresh the page.</p>
                </div>
              )}
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {availablePlayers.map((player) => (
                  <div
                    key={'player_name' in player ? player.player_name : (player as any).id}
                    className={`player-card cursor-pointer ${selectedPlayer === player.player_name
                        ? 'border-valorant-500 bg-valorant-50'
                        : ''
                      }`}
                    onClick={() => setSelectedPlayer(player.player_name)}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <h3 className="font-medium">{player.player_name}</h3>
                        <p className="text-sm text-gray-600">{'team_name' in player ? player.team_name : (player as FreeAgent).team}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 flex space-x-2">
                <button
                  onClick={makePick}
                  disabled={!selectedPlayer || !team || !draftId || draftStatus?.status !== 'IN_PROGRESS'}
                  className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Make Pick
                </button>
              </div>
            </div>
          </div>

          {/* Draft Order + Draft Results */}
          <div className="lg:col-span-1 space-y-4">
            <div className="card">
              <h2 className="text-xl font-bold mb-4 flex items-center"><ListOrdered className="h-5 w-5 mr-2" />Draft Order</h2>
              {draftOrder && draftStatus ? (
                <ol className="space-y-2 list-decimal list-inside">
                  {draftOrder.map((userId, idx) => {
                    const isCurrent = draftStatus.current_user_id === userId;
                    return (
                      <li key={idx} className={isCurrent ? 'font-semibold text-valorant-600' : ''}>
                        {usernamesById[userId] || `User #${userId}`} {isCurrent ? '(Picking now)' : ''}
                      </li>
                    );
                  })}
                </ol>
              ) : (
                <p className="text-gray-600">Draft order not set yet.</p>
              )}
            </div>
            <div className="card">
              <h2 className="text-xl font-bold mb-4">Draft Board</h2>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {draftPicks.map((pick) => (
                  <div key={pick.id} className="flex justify-between items-center p-2 border rounded">
                    <div>
                      <p className="font-medium text-sm">{pick.player_name}</p>
                      <p className="text-xs text-gray-600">Pick #{pick.pick_number}</p>
                    </div>
                    <div className="flex items-center">
                      <User className="h-4 w-4 mr-1 text-gray-400" />
                      <span className="text-xs">Team {pick.team_id}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 