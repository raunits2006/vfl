'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Users, X, Edit2, Check } from 'lucide-react';
import { api, apiRequest } from '../../../../utils/api';
import { useToast } from '../../../../components/ToastProvider';
import { useAuth } from '../../../../contexts/AuthContext';
import SidePanel from '../../../../components/SidePanel';
import AgentSelectionPanel from '../../../../components/AgentSelectionPanel';
import { TeamSummary, TeamPlayer, FreeAgent, TeamPlayerWithScore } from '../../../../types/api';

// Agent to class mapping for display
const AGENT_TO_CLASS: Record<string, string> = {
  'Jett': 'Duelist', 'Phoenix': 'Duelist', 'Neon': 'Duelist', 'Raze': 'Duelist',
  'Reyna': 'Duelist', 'Yoru': 'Duelist', 'Iso': 'Duelist', 'Waylay': 'Duelist',
  'Astra': 'Controller', 'Brimstone': 'Controller', 'Omen': 'Controller',
  'Viper': 'Controller', 'Harbor': 'Controller', 'Clove': 'Controller',
  'Breach': 'Initiator', 'Gekko': 'Initiator', 'KAY/O': 'Initiator',
  'Skye': 'Initiator', 'Sova': 'Initiator', 'Fade': 'Initiator', 'Tejo': 'Initiator',
  'Chamber': 'Sentinel', 'Cypher': 'Sentinel', 'Deadlock': 'Sentinel',
  'Killjoy': 'Sentinel', 'Sage': 'Sentinel', 'Vyse': 'Sentinel',
};

export default function MyTeamPage() {
  const params = useParams<{ id: string }>();
  const leagueId = Number(params.id);
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { showToast } = useToast();
  const [freeAgentPool, setFreeAgentPool] = useState<FreeAgent[]>([]);
  const [dropSelection, setDropSelection] = useState<string | null>(null);
  const [addSelection, setAddSelection] = useState<string | null>(null);
  const [tradeMode, setTradeMode] = useState(false);
  const [receivingTeamId, setReceivingTeamId] = useState<number | null>(null);
  const [leagueTeams, setLeagueTeams] = useState<Array<{ id: number; name: string; user_id: number }>>([]);
  const [offeringPlayers, setOfferingPlayers] = useState<string[]>([]);
  const [receivingPlayers, setReceivingPlayers] = useState<string[]>([]);
  const [receivingTeamPlayers, setReceivingTeamPlayers] = useState<TeamPlayer[]>([]);

  const [team, setTeam] = useState<TeamSummary | null>(null);
  const [players, setPlayers] = useState<TeamPlayer[]>([]);
  const [playerScores, setPlayerScores] = useState<TeamPlayerWithScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [isLocked, setIsLocked] = useState<boolean>(false);
  const [lockMessage, setLockMessage] = useState<string>('');
  const [draftCompleted, setDraftCompleted] = useState<boolean>(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editName, setEditName] = useState('');
  const [maxStarters, setMaxStarters] = useState<number>(5);

  // Swap modal state
  const [swapModalOpen, setSwapModalOpen] = useState(false);
  const [playerToPromote, setPlayerToPromote] = useState<string | null>(null);

  // Agent selection panel state
  const [agentPanelOpen, setAgentPanelOpen] = useState(false);
  const [selectedPlayerForAgents, setSelectedPlayerForAgents] = useState<TeamPlayerWithScore | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace('/signin');
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    let active = true;
    async function load() {
      if (!Number.isFinite(leagueId) || !user) return;
      setLoading(true);
      try {
        // Enforce that draft must be IN_PROGRESS or COMPLETED to access team page
        try {
          const draft = await api.getDraftByLeague(leagueId);
          if (draft.status === 'PENDING') {
            showToast('Draft has not started yet. You will be redirected.', { type: 'info' });
            router.replace(`/leagues/${leagueId}`);
            return;
          }
          setDraftCompleted(draft.status === 'COMPLETED');
        } catch { }

        // Get league settings for max starters
        try {
          const settings = await api.getLeagueSettings(leagueId);
          setMaxStarters(settings.starting_players);
        } catch { }

        const t = await api.getUserTeamByLeague(leagueId, user.id);
        if (!active) return;
        setTeam(t);

        // Get player list (for trades/free agents compatibility)
        const list = await api.getTeamPlayers(t.id);
        if (!active) return;
        setPlayers(list);

        // Get player scores with agent predictions
        try {
          const scores = await api.getTeamPlayerScores(t.id);
          if (!active) return;
          setPlayerScores(scores);
        } catch { }

        // Lock status
        const lock = await apiRequest<{ is_locked: boolean; message: string }>(`/api/teams/${t.id}/lock-status`);
        if (!active) return;
        setIsLocked(!!lock.is_locked);
        setLockMessage(lock.message || '');
      } catch (e) {
        // Team not found; redirect back to league page
        router.replace(`/leagues/${leagueId}`);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [leagueId, user, router]);

  useEffect(() => {
    // Load free agent pool when we know leagueId and have a team
    async function loadPool() {
      if (!team?.league_id) return;
      try {
        const pool = await api.getFreeAgentPool(team.league_id);
        setFreeAgentPool(pool);
      } catch { }
      try {
        // Reuse league details to list member teams
        const details = await api.getLeagueDetails(leagueId);
        const teams: Array<{ id: number; name: string; user_id: number }> = [];
        for (const m of details.members || []) {
          try {
            const t = await api.getUserTeamByLeague(leagueId, m.user_id);
            teams.push({ id: t.id, name: t.name, user_id: t.user_id });
          } catch { }
        }
        setLeagueTeams(teams.filter(t => t.id !== team?.id));
      } catch { }
    }
    loadPool();
  }, [team?.league_id]);

  // Load receiving team's roster when selection changes
  useEffect(() => {
    async function loadReceivingTeamPlayers() {
      if (!receivingTeamId) { setReceivingTeamPlayers([]); return; }
      try {
        const recPlayers = await api.getTeamPlayers(receivingTeamId);
        setReceivingTeamPlayers(recPlayers);
      } catch { }
    }
    loadReceivingTeamPlayers();
  }, [receivingTeamId]);

  // Compute starters and bench from playerScores
  const starters = useMemo(() => playerScores.filter(p => p.is_starting), [playerScores]);
  const bench = useMemo(() => playerScores.filter(p => !p.is_starting), [playerScores]);
  const startersAtMax = starters.length >= maxStarters;

  const refreshPlayerData = async () => {
    if (!team) return;
    try {
      const list = await api.getTeamPlayers(team.id);
      setPlayers(list);
      const scores = await api.getTeamPlayerScores(team.id);
      setPlayerScores(scores);
    } catch { }
  };

  const handleTogglePlayer = async (player: TeamPlayerWithScore) => {
    if (!team || isLocked) return;

    // If promoting from bench and starters are at max, open swap modal
    if (!player.is_starting && startersAtMax) {
      setPlayerToPromote(player.player_name);
      setSwapModalOpen(true);
      return;
    }

    try {
      await api.togglePlayerStartingStatus(team.id, player.player_name);
      await refreshPlayerData();
    } catch (error) {
      console.error('Error toggling player status:', error);
      const message = (error as any)?.message || 'Failed to update player status. Please try again.';
      showToast(message, { type: 'error' });
    }
  };

  const handleSwapPlayers = async (starterToDemote: string) => {
    if (!team || !playerToPromote) return;

    try {
      await api.swapPlayers(team.id, playerToPromote, starterToDemote);
      showToast(`Swapped ${playerToPromote} with ${starterToDemote}`, { type: 'success' });
      await refreshPlayerData();
      setSwapModalOpen(false);
      setPlayerToPromote(null);
    } catch (error) {
      console.error('Error swapping players:', error);
      const message = (error as any)?.message || 'Failed to swap players. Please try again.';
      showToast(message, { type: 'error' });
    }
  };

  const performFreeAgentSwap = async () => {
    if (!team) return;
    if (!dropSelection || !addSelection) {
      showToast('Select a player to drop and a free agent to add', { type: 'warning' });
      return;
    }
    try {
      const res = await api.swapFreeAgent(team.league_id, team.id, dropSelection, addSelection);
      showToast(res.message, { type: 'success' });
      await refreshPlayerData();
      const pool = await api.getFreeAgentPool(team.league_id);
      setFreeAgentPool(pool);
      setDropSelection(null);
      setAddSelection(null);
    } catch (e: any) {
      showToast(e?.message || 'Swap failed', { type: 'error' });
    }
  };

  const submitTrade = async () => {
    if (!team || !receivingTeamId) { showToast('Select a receiving team', { type: 'warning' }); return; }
    if (offeringPlayers.length === 0 || receivingPlayers.length === 0) { showToast('Select at least one player on each side', { type: 'warning' }); return; }
    try {
      await api.proposeTrade(team.league_id, team.id, receivingTeamId, offeringPlayers, receivingPlayers);
      showToast('Trade proposed', { type: 'success' });
      setTradeMode(false);
      setOfferingPlayers([]);
      setReceivingPlayers([]);
      setReceivingTeamId(null);
    } catch (e: any) {
      showToast(e?.message || 'Failed to propose trade', { type: 'error' });
    }
  };

  // Agent display component
  const AgentSlot = ({ agentName, agentClass }: { agentName?: string; agentClass?: string }) => {
    if (!agentName) {
      return (
        <div className="text-center px-2 py-1">
          <div className="text-sm text-gray-400 italic">No Agent</div>
          <div className="text-xs text-gray-500">Selected</div>
        </div>
      );
    }
    return (
      <div className="text-center px-2 py-1">
        <div className="text-sm font-medium">{agentName}</div>
        <div className="text-xs text-gray-500">{agentClass || AGENT_TO_CLASS[agentName] || 'Unknown'}</div>
      </div>
    );
  };

  // Player row component
  const PlayerRow = ({ player }: { player: TeamPlayerWithScore }) => {
    const hasAgents = player.agent_predictions.length > 0;

    return (
      <tr className="border-b border-gray-700/50 hover:bg-gray-800/30">
        {/* Player Name & Team */}
        <td className="py-3 px-4">
          <div className="font-medium">{player.player_name}</div>
          <div className="text-sm text-gray-500">{player.team}</div>
        </td>

        {/* Action Button */}
        <td className="py-3 px-2">
          {!isLocked && (
            <button
              onClick={() => handleTogglePlayer(player)}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${player.is_starting
                ? 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                : 'bg-green-100 hover:bg-green-200 text-green-700'
                }`}
            >
              {player.is_starting ? 'Bench' : 'Start'}
            </button>
          )}
        </td>

        {/* Agent Slots */}
        <td className="py-3 px-2">
          <AgentSlot
            agentName={player.agent_predictions[0]}
            agentClass={player.agent_classes[0]}
          />
        </td>
        <td className="py-3 px-2">
          <AgentSlot
            agentName={player.agent_predictions[1]}
            agentClass={player.agent_classes[1]}
          />
        </td>
        <td className="py-3 px-2">
          <AgentSlot
            agentName={player.agent_predictions[2]}
            agentClass={player.agent_classes[2]}
          />
        </td>

        {/* Modify/Select Agents Button */}
        <td className="py-3 px-2">
          <button
            onClick={() => {
              setSelectedPlayerForAgents(player);
              setAgentPanelOpen(true);
            }}
            disabled={isLocked}
            className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${isLocked
              ? 'bg-valorant-600/20 text-valorant-400 cursor-not-allowed opacity-60'
              : 'bg-valorant-600/30 hover:bg-valorant-600/50 text-valorant-400'
              }`}
          >
            {hasAgents ? 'Modify' : 'Select'}
          </button>
        </td>

        {/* Total Points */}
        <td className="py-3 px-4 text-right">
          <span className="font-semibold text-lg">{player.total_points.toFixed(1)}</span>
        </td>
      </tr>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-valorant-600"></div>
      </div>
    );
  }

  if (!team) {
    return (
      <div className="card">
        <h2 className="text-xl font-bold mb-2">No team found</h2>
        <p className="text-gray-600">Join this league and create your team to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Team Header */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            {isEditingName ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="input-field text-2xl font-bold py-1"
                  autoFocus
                />
                <button
                  onClick={async () => {
                    if (!team || !editName.trim()) return;
                    try {
                      const updated = await api.renameTeam(team.id, editName.trim());
                      setTeam({ ...team, name: updated.name });
                      setIsEditingName(false);
                      showToast('Team renamed successfully!', { type: 'success' });
                    } catch (e: any) {
                      showToast(e?.message || 'Failed to rename team', { type: 'error' });
                    }
                  }}
                  className="p-1 text-green-600 hover:bg-green-50 rounded"
                  title="Save"
                >
                  <Check className="h-5 w-5" />
                </button>
                <button
                  onClick={() => {
                    setIsEditingName(false);
                    setEditName(team.name);
                  }}
                  className="p-1 text-gray-500 hover:bg-gray-100 rounded"
                  title="Cancel"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold">{team.name}</h2>
                <button
                  onClick={() => {
                    setEditName(team.name);
                    setIsEditingName(true);
                  }}
                  className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
                  title="Edit team name"
                >
                  <Edit2 className="h-4 w-4" />
                </button>
              </div>
            )}
            <p className="text-gray-600">{user?.username}</p>
          </div>
          {isLocked && (
            <div className="text-sm text-red-500">{lockMessage || 'Team changes are currently locked.'}</div>
          )}
        </div>
      </div>

      {/* Unified Player Table */}
      <div className="card overflow-x-auto">
        <h3 className="text-xl font-semibold mb-4 flex items-center">
          <Users className="h-5 w-5 mr-2 text-valorant-500" />
          Team Roster
        </h3>

        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-700 text-left text-sm text-gray-400">
              <th className="py-2 px-4">Player</th>
              <th className="py-2 px-2">Action</th>
              <th className="py-2 px-2 text-center">Agent 1</th>
              <th className="py-2 px-2 text-center">Agent 2</th>
              <th className="py-2 px-2 text-center">Agent 3</th>
              <th className="py-2 px-2">Agents</th>
              <th className="py-2 px-4 text-right">Points</th>
            </tr>
          </thead>
          <tbody>
            {/* Starters Section */}
            {starters.map(player => (
              <PlayerRow key={player.player_name} player={player} />
            ))}

            {/* Divider */}
            {bench.length > 0 && (
              <tr>
                <td colSpan={7} className="py-4">
                  <div className="flex items-center gap-4">
                    <div className="flex-1 h-px bg-gray-700"></div>
                    <span className="text-sm text-gray-400 font-medium">Bench Players</span>
                    <div className="flex-1 h-px bg-gray-700"></div>
                  </div>
                </td>
              </tr>
            )}

            {/* Bench Section */}
            {bench.map(player => (
              <PlayerRow key={player.player_name} player={player} />
            ))}
          </tbody>
        </table>

        {playerScores.length === 0 && (
          <p className="text-gray-500 text-center py-8">No players on your team yet.</p>
        )}
      </div>

      {/* Swap Side Panel */}
      <SidePanel
        isOpen={swapModalOpen}
        onClose={() => {
          setSwapModalOpen(false);
          setPlayerToPromote(null);
        }}
        title="Select Player to Bench"
        footer={
          <button
            onClick={() => {
              setSwapModalOpen(false);
              setPlayerToPromote(null);
            }}
            className="w-full py-3 px-4 bg-gray-600 hover:bg-gray-500 text-white font-medium rounded-lg transition-colors"
          >
            Cancel
          </button>
        }
      >
        <p className="text-gray-300 mb-6">
          Your starting lineup is full. Select a starter to bench in order to start <strong className="text-white">{playerToPromote}</strong>.
        </p>

        <div className="space-y-3">
          {starters.map(starter => (
            <button
              key={starter.player_name}
              onClick={() => handleSwapPlayers(starter.player_name)}
              className="w-full flex items-center justify-between p-4 border border-gray-600 rounded-lg hover:border-gray-500 transition-colors text-left"
              style={{ backgroundColor: 'rgb(30, 41, 52)' }}
            >
              <div className="text-left">
                <div className="font-medium text-white">{starter.player_name}</div>
                <div className="text-sm text-gray-400">{starter.team}</div>
              </div>
              <span className="text-sm font-medium text-valorant-400 flex-shrink-0 ml-4">{starter.total_points.toFixed(1)} pts</span>
            </button>
          ))}
        </div>
      </SidePanel>

      {/* Agent Selection Panel */}
      {selectedPlayerForAgents && team && (
        <AgentSelectionPanel
          isOpen={agentPanelOpen}
          onClose={() => {
            setAgentPanelOpen(false);
            setSelectedPlayerForAgents(null);
          }}
          playerName={selectedPlayerForAgents.player_name}
          teamId={team.id}
          existingAgents={selectedPlayerForAgents.agent_predictions}
          onSave={refreshPlayerData}
        />
      )}

      {/* Free Agent Swap */}
      {draftCompleted && (
        <div className="card">
          <h3 className="text-xl font-semibold mb-4">Free Agents</h3>
          <p className="text-sm text-gray-600 mb-3">Drop or add players independently. Max 2 Duelists; cannot add already taken players. Rosters must be 7 by lock.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium mb-2">Select player to drop</div>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {players.map(p => (
                  <label key={p.id} className={`flex items-center justify-between p-2 border rounded cursor-pointer ${dropSelection === p.player_name ? 'border-valorant-600 bg-valorant-50' : ''}`}>
                    <div>
                      <div className="font-medium text-sm">{p.player_name}</div>
                      <div className="text-xs text-gray-500">{p.team}</div>
                    </div>
                    <input type="radio" name="drop" checked={dropSelection === p.player_name} onChange={() => setDropSelection(p.player_name)} />
                  </label>
                ))}
              </div>
            </div>
            <div>
              <div className="text-sm font-medium mb-2">Select free agent to add</div>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {freeAgentPool.map((fa) => (
                  <label key={fa.player_name} className={`flex items-center justify-between p-2 border rounded cursor-pointer ${addSelection === fa.player_name ? 'border-valorant-600 bg-valorant-50' : ''}`}>
                    <div>
                      <div className="font-medium text-sm">{fa.player_name}</div>
                      <div className="text-xs text-gray-500">{fa.team}</div>
                    </div>
                    <input type="radio" name="add" checked={addSelection === fa.player_name} onChange={() => setAddSelection(fa.player_name)} />
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-end gap-2">
            <button
              onClick={async () => {
                if (!team) return;
                if (!dropSelection) { showToast('Select a player to drop', { type: 'warning' }); return; }
                try {
                  const res = await api.dropPlayer(team.league_id, team.id, dropSelection);
                  showToast(res.message, { type: 'success' });
                  await refreshPlayerData();
                  setDropSelection(null);
                } catch (e: any) {
                  showToast(e?.message || 'Drop failed', { type: 'error' });
                }
              }}
              disabled={isLocked}
              className="btn-secondary disabled:opacity-50"
            >
              Drop Only
            </button>
            <button
              onClick={async () => {
                if (!team) return;
                if (!addSelection) { showToast('Select a player to add', { type: 'warning' }); return; }
                try {
                  const res = await api.addFreeAgent(team.league_id, team.id, addSelection);
                  showToast(res.message, { type: 'success' });
                  await refreshPlayerData();
                  const pool = await api.getFreeAgentPool(team.league_id);
                  setFreeAgentPool(pool);
                  setAddSelection(null);
                } catch (e: any) {
                  showToast(e?.message || 'Add failed', { type: 'error' });
                }
              }}
              disabled={isLocked}
              className="btn-secondary disabled:opacity-50"
            >
              Add Only
            </button>
            <button onClick={performFreeAgentSwap} disabled={isLocked} className="btn-primary disabled:opacity-50">Submit Swap</button>
          </div>
        </div>
      )}

      {/* Trade Proposal */}
      {draftCompleted && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xl font-semibold">Propose Trade</h3>
            <button onClick={() => setTradeMode(!tradeMode)} className="btn-secondary text-sm">{tradeMode ? 'Close' : 'Open'}</button>
          </div>
          {tradeMode && (
            <div className="space-y-4">
              <div>
                <div className="text-sm font-medium mb-2">Select receiving team</div>
                <select value={receivingTeamId ?? ''} onChange={e => setReceivingTeamId(Number(e.target.value) || null)} className="input-field">
                  <option value="">Select a team</option>
                  {leagueTeams.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-sm font-medium mb-2">Your offer</div>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {players.map(p => (
                      <label key={p.id} className={`flex items-center justify-between p-2 border rounded cursor-pointer ${offeringPlayers.includes(p.player_name) ? 'border-valorant-600 bg-valorant-50' : ''}`}>
                        <div>
                          <div className="font-medium text-sm">{p.player_name}</div>
                          <div className="text-xs text-gray-500">{p.team}</div>
                        </div>
                        <input type="checkbox" checked={offeringPlayers.includes(p.player_name)} onChange={(e) => {
                          setOfferingPlayers(prev => e.target.checked ? [...prev, p.player_name] : prev.filter(x => x !== p.player_name));
                        }} />
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium mb-2">Request from selected team</div>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {!receivingTeamId && (
                      <p className="text-sm text-gray-500">Select a team to view their players</p>
                    )}
                    {receivingTeamId && receivingTeamPlayers.length === 0 && (
                      <p className="text-sm text-gray-500">No players found for selected team.</p>
                    )}
                    {receivingTeamId && receivingTeamPlayers.map(p => (
                      <label key={p.id} className={`flex items-center justify-between p-2 border rounded cursor-pointer ${receivingPlayers.includes(p.player_name) ? 'border-valorant-600 bg-valorant-50' : ''}`}>
                        <div>
                          <div className="font-medium text-sm">{p.player_name}</div>
                          <div className="text-xs text-gray-500">{p.team}</div>
                        </div>
                        <input type="checkbox" checked={receivingPlayers.includes(p.player_name)} onChange={(e) => {
                          setReceivingPlayers(prev => e.target.checked ? [...prev, p.player_name] : prev.filter(x => x !== p.player_name));
                        }} />
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex justify-end">
                <button onClick={submitTrade} className="btn-primary">Send Trade Offer</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
