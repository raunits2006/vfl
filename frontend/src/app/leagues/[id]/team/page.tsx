'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ChevronUp, ChevronDown, Users, X } from 'lucide-react';
import { api, apiRequest } from '../../../../utils/api';
import { useToast } from '../../../../components/ToastProvider';
import { useAuth } from '../../../../contexts/AuthContext';
import { TeamSummary, TeamPlayer, FreeAgent } from '../../../../types/api';

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
  const [loading, setLoading] = useState(true);
  const [isLocked, setIsLocked] = useState<boolean>(false);
  const [lockMessage, setLockMessage] = useState<string>('');
  const [predictions, setPredictions] = useState<Record<string, string[]>>({});
  const AGENT_GROUPS: Record<string, string[]> = {
    Duelists: ['Jett','Phoenix','Neon','Raze','Reyna','Yoru','Iso','Waylay'],
    Controllers: ['Astra','Brimstone','Omen','Viper','Harbor','Clove'],
    Initiators: ['Breach','Gekko','KAY/O','Skye','Sova','Fade','Tejo'],
    Sentinels: ['Chamber','Cypher','Deadlock','Killjoy','Sage','Vyse'],
  };

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
        const t = await api.getUserTeamByLeague(leagueId, user.id);
        if (!active) return;
        setTeam(t);
        const list = await api.getTeamPlayers(t.id);
        if (!active) return;
        setPlayers(list);
        try {
          const preds = await api.getAgentPredictions(t.id);
          if (!active) return;
          const map: Record<string, string[]> = {};
          for (const p of preds) map[p.player_name] = p.picks;
          setPredictions(map);
        } catch {}
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
      } catch {}
      try {
        // Reuse league details to list member teams
        const details = await api.getLeagueDetails(leagueId);
        // Each member may have a team; fetch teams by user to list
        // Simplify: build team list from current roster owners we have locally
        // Better: dedicated endpoint. For now, fetch each user's team.
        const teams: Array<{ id: number; name: string; user_id: number }> = [];
        for (const m of details.members || []) {
          try {
            const t = await api.getUserTeamByLeague(leagueId, m.user_id);
            teams.push({ id: t.id, name: t.name, user_id: t.user_id });
          } catch {}
        }
        setLeagueTeams(teams.filter(t => t.id !== team?.id));
      } catch {}
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
      } catch {}
    }
    loadReceivingTeamPlayers();
  }, [receivingTeamId]);

  const starters = useMemo(() => players.filter(p => p.is_starting), [players]);
  const bench = useMemo(() => players.filter(p => !p.is_starting), [players]);

  const savePrediction = async (playerName: string) => {
    if (!team || isLocked) return;
    const picks = predictions[playerName] || [];
    if (picks.length !== 3) {
      showToast('Pick exactly 3 agents', { type: 'warning' });
      return;
    }
    try {
      await api.setAgentPrediction(team.id, playerName, picks);
      showToast('Picks saved', { type: 'success' });
    } catch (e: any) {
      showToast(e?.message || 'Failed to save', { type: 'error' });
    }
  };

  const togglePick = (playerName: string, agent: string) => {
    setPredictions(prev => {
      const current = prev[playerName] ? [...prev[playerName]] : [];
      const idx = current.indexOf(agent);
      if (idx >= 0) {
        current.splice(idx, 1);
      } else {
        if (current.length >= 3) return prev; // enforce max 3
        current.push(agent);
      }
      return { ...prev, [playerName]: current };
    });
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
      // Refresh players and pool
      const list = await api.getTeamPlayers(team.id);
      setPlayers(list);
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

  const handleTogglePlayer = async (player: TeamPlayer) => {
    if (!team || isLocked) return;
    
    try {
      const updatedPlayer = await api.togglePlayerStartingStatus(team.id, player.player_name);
      // Update the local players array with the new status
      setPlayers(prevPlayers =>
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
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">My Team</h2>
            <p className="text-gray-600">{team.name}</p>
          </div>
          {isLocked && (
            <div className="text-sm text-red-500">{lockMessage || 'Team changes are currently locked.'}</div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-xl font-semibold mb-4 flex items-center">
            <Users className="h-5 w-5 mr-2 text-green-600" />
            Starters ({starters.length})
          </h3>
          {starters.length === 0 ? (
            <p className="text-gray-600">No starters set.</p>
          ) : (
            <ul className="divide-y divide-gray-800/50">
              {starters.map(p => (
                <li key={p.id} className="py-3 flex items-center justify-between">
                  <div>
                    <div className="font-medium">{p.player_name}</div>
                    <div className="text-sm text-gray-500">{p.team}</div>
                  </div>
                  {!isLocked && (
                    <button
                      onClick={() => handleTogglePlayer(p)}
                      className="flex items-center px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                      title="Move to bench"
                    >
                      <ChevronDown className="h-4 w-4 mr-1" />
                      Bench
                    </button>
                  )}
                  <div className="mt-3">
                    <div className="text-xs text-gray-600 mb-1">Pick 3 agents (full points if 2 of 3 correct):</div>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {(predictions[p.player_name] || []).map(a => (
                        <span key={a} className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-valorant-600 text-white">
                          {a}
                          {!isLocked && (
                            <button onClick={() => togglePick(p.player_name, a)} className="opacity-80 hover:opacity-100">
                              <X className="h-3 w-3" />
                            </button>
                          )}
                        </span>
                      ))}
                      {Array.from({ length: Math.max(0, 3 - (predictions[p.player_name]?.length || 0)) }).map((_, idx) => (
                        <span key={idx} className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-500">Pick agent</span>
                      ))}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                      {Object.entries(AGENT_GROUPS).map(([group, agents]) => {
                        const picks = predictions[p.player_name] || [];
                        const canAdd = picks.length < 3;
                        return (
                          <div key={group} className="border border-gray-100 rounded-md p-2">
                            <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1">{group}</div>
                            <div className="flex flex-wrap gap-2">
                              {agents.map(a => {
                                const selected = picks.includes(a);
                                const disabled = isLocked || (!selected && !canAdd);
                                return (
                                  <button
                                    key={a}
                                    onClick={() => togglePick(p.player_name, a)}
                                    disabled={disabled}
                                    className={`px-2 py-1 text-xs rounded-full border transition-colors ${
                                      selected
                                        ? 'bg-valorant-600 text-white border-valorant-600'
                                        : disabled
                                          ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed'
                                          : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                                    }`}
                                  >
                                    {a}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                      <span>Half points on class match; otherwise 0.25x.</span>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setPredictions(prev => ({ ...prev, [p.player_name]: [] }))}
                          disabled={isLocked}
                          className="px-3 py-1 rounded border border-gray-200 text-gray-700 hover:bg-gray-50"
                        >
                          Clear
                        </button>
                        <button
                          onClick={() => savePrediction(p.player_name)}
                          disabled={isLocked}
                          className="px-3 py-1 rounded bg-gray-900 text-white hover:bg-black"
                        >
                          Save Picks
                        </button>
                      </div>
                    </div>
                  </div>
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
                  {!isLocked && (
                    <button
                      onClick={() => handleTogglePlayer(p)}
                      className="flex items-center px-2 py-1 text-sm bg-green-100 hover:bg-green-200 text-green-700 rounded transition-colors"
                      title="Promote to starter"
                    >
                      <ChevronUp className="h-4 w-4 mr-1" />
                      Start
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Free Agent Swap */}
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
                    <div className="text-xs text-gray-500">{fa.team} • {fa.primary_role}</div>
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
                const list = await api.getTeamPlayers(team.id);
                setPlayers(list);
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
                const list = await api.getTeamPlayers(team.id);
                setPlayers(list);
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

      {/* Trade Proposal */}
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
    </div>
  );
}


