'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, ApiError } from '../../../utils/api';
import { useAuth } from '../../../contexts/AuthContext';
import { Users, RefreshCcw, Shield, Calendar, Crown, ListOrdered, Play, User, Settings, Eye, X } from 'lucide-react';
import SetDraftOrderModal from '../../../components/SetDraftOrderModal';
import { useToast } from '../../../components/ToastProvider';
import type { LeagueLeaderboardEnvelope, TeamPlayer } from '../../../types/api';

export default function LeagueDetailsPage() {
  const params = useParams<{ id: string }>();
  const leagueId = Number(params.id);
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { showToast } = useToast();

  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [pinLoading, setPinLoading] = useState(false);
  const [draftStatus, setDraftStatus] = useState<any>(null);
  const [weeklyBoard, setWeeklyBoard] = useState<LeagueLeaderboardEnvelope | null>(null);
  const [seasonBoard, setSeasonBoard] = useState<LeagueLeaderboardEnvelope | null>(null);
  const [activity, setActivity] = useState<Array<{ type: 'swap' | 'trade'; message: string; timestamp: string }>>([]);
  const [myActivity, setMyActivity] = useState<Array<any>>([]);
  const [myTeamId, setMyTeamId] = useState<number | null>(null);
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);

  // View Team Modal state
  const [viewTeamModalOpen, setViewTeamModalOpen] = useState(false);
  const [viewingTeam, setViewingTeam] = useState<{ name: string; ownerUsername: string; userId: number } | null>(null);
  const [viewingTeamPlayers, setViewingTeamPlayers] = useState<TeamPlayer[]>([]);
  const [viewTeamLoading, setViewTeamLoading] = useState(false);

  // Auth guard: redirect unauthenticated users
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace('/signin');
    }
  }, [authLoading, user, router]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-valorant-600 mx-auto" />
        </div>
      </div>
    );
  }

  if (!user) return null;

  const fetchDetails = async () => {
    try {
      const data = await api.getLeagueDetails(leagueId);
      setDetails((prev: any) => ({ ...(prev || {}), ...(data || {}) }));
      setAccessDenied(false);
      try {
        const draft = await api.getDraftByLeague(leagueId);
        setDraftStatus(draft);
      } catch {
        setDraftStatus(null);
      }
      try {
        const [weekly, season] = await Promise.all([
          api.getLeagueLeaderboardWeekly(leagueId, 7),
          api.getLeagueLeaderboardSeason(leagueId),
        ]);
        setWeeklyBoard(weekly);
        setSeasonBoard(season);
      } catch { }
      try {
        const [trades, transactions] = await Promise.all([
          api.getLeagueTrades(leagueId),
          api.getLeagueTransactions(leagueId),
        ]);
        const feed: Array<{ type: 'swap' | 'trade'; message: string; timestamp: string }> = [];
        for (const t of trades) {
          if (t.status !== 'accepted') continue;
          const offered = t.trade_items.filter((i: any) => i.team_id === t.team1_id).map((i: any) => i.player_name).join(', ');
          const requested = t.trade_items.filter((i: any) => i.team_id === t.team2_id).map((i: any) => i.player_name).join(', ');
          feed.push({
            type: 'trade',
            message: `${t.team1_name} traded [${offered}] with ${t.team2_name} for [${requested}]`,
            timestamp: t.responded_at || t.proposed_at,
          });
        }
        for (const tx of transactions) {
          feed.push({
            type: 'swap',
            message: `Team #${tx.team_id} ${tx.transaction_type === 'add' ? 'added' : 'dropped'} ${tx.player_name}`,
            timestamp: tx.transaction_date,
          });
        }
        feed.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        setActivity(feed);
      } catch { }

      try {
        if (user) {
          const myTeam = await api.getUserTeamByLeague(leagueId, user.id);
          setMyTeamId(myTeam.id);
          const myTrades = await api.getTeamTrades(myTeam.id);
          setMyActivity(myTrades);
        } else {
          setMyActivity([]);
          setMyTeamId(null);
        }
      } catch { }
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setAccessDenied(true);
        return;
      }
      // For other errors, just log them
      console.error('Error fetching league details:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!Number.isFinite(leagueId)) return;
    fetchDetails();
  }, [leagueId, user?.id]);

  // Auto-refresh league details periodically so UI updates without manual refresh
  useEffect(() => {
    if (!Number.isFinite(leagueId)) return;
    const interval = setInterval(() => {
      fetchDetails();
    }, 7000);
    return () => clearInterval(interval);
  }, [leagueId, user?.id]);

  // Refresh when tab becomes visible again without flicker
  useEffect(() => {
    let rafId: number | null = null;
    let scheduled = false;
    const onVisibility = () => {
      if (!document.hidden && !scheduled) {
        scheduled = true;
        rafId = requestAnimationFrame(() => {
          scheduled = false;
          fetchDetails();
        });
      }
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [leagueId, user?.id]);

  const regeneratePin = async () => {
    try {
      setPinLoading(true);
      const res = await api.regenerateLeaguePin(leagueId);
      setDetails((prev: any) => ({ ...prev, join_pin: res.join_pin }));
      showToast('Join PIN regenerated', { type: 'success' });
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 403) {
        showToast(e.message || 'Only commissioners can regenerate PINs', { type: 'error' });
      } else {
        showToast(e?.message || 'Failed to regenerate PIN', { type: 'error' });
      }
    } finally {
      setPinLoading(false);
    }
  };

  const startDraft = async () => {
    try {
      const status = await api.startDraft(leagueId);
      // After starting, do not redirect; allow commissioner to set order
      setDraftStatus(status);
      showToast('Draft created. Set the draft order to begin.', { type: 'success' });
    } catch (e: any) {
      if (e?.message?.includes('already started')) {
        try {
          const existing = await api.getDraftByLeague(leagueId);
          if (user) {
            try { await api.getUserTeamByLeague(leagueId, user.id); } catch {
              try { await api.createTeam(leagueId, user.id, `${user.username}'s Team`); } catch { }
            }
          }
          // Keep user on page; they can go to draft once IN_PROGRESS
          setDraftStatus(existing);
          return;
        } catch { }
      }

      // Handle specific error cases with user-friendly messages
      if (e?.message?.includes('Cannot start draft: no league members found')) {
        showToast('Cannot start draft: No league members found. Please ensure at least one member has joined the league.', {
          type: 'error',
          title: 'Draft Error'
        });
      } else if (e?.message?.includes('League not found')) {
        showToast('League not found. Please check the URL or contact support.', {
          type: 'error',
          title: 'League Error'
        });
      } else {
        showToast(e?.message || 'Failed to start draft', { type: 'error' });
      }
    }
  };

  const setDraftOrder = async () => {
    try {
      if (!draftStatus) {
        showToast('No draft found. Please start a draft first.', { type: 'warning' });
        return;
      }

      // Get league members for draft order
      const memberIds = (details?.members || []).map((m: any) => m.user_id);
      if (memberIds.length === 0) {
        showToast('No league members found. Cannot set draft order.', { type: 'error' });
        return;
      }

      // Set draft order using current display order (no randomize). This is kept as a fallback action.
      const result = await api.setDraftOrder(draftStatus.draft_id, memberIds, false);
      showToast('Draft order set successfully!', { type: 'success' });

      router.push(`/leagues/${leagueId}/draft?draftId=${draftStatus.draft_id}`);
    } catch (e: any) {
      // Handle specific error cases with user-friendly messages
      if (e?.message?.includes('Only the league commissioner can set draft order')) {
        showToast('Only the league commissioner can set draft order. Please contact your commissioner.', {
          type: 'error',
          title: 'Authorization Error'
        });
      } else if (e?.message?.includes('Draft not found')) {
        showToast('Draft not found. Please check the URL or contact support.', {
          type: 'error',
          title: 'Draft Error'
        });
      } else if (e?.message?.includes('Draft already started')) {
        showToast('Draft has already started. Cannot modify draft order.', {
          type: 'error',
          title: 'Draft Error'
        });
      } else if (e?.message?.includes('Draft order cannot be empty')) {
        showToast('Cannot set empty draft order. Please ensure there are league members.', {
          type: 'error',
          title: 'Draft Error'
        });
      } else {
        showToast(e?.message || 'Failed to set draft order', { type: 'error' });
      }
    }
  };

  const handleSaveOrder = async (orderedUserIds: number[]) => {
    if (!draftStatus) return;
    try {
      await api.setDraftOrder(draftStatus.draft_id, orderedUserIds, false);
      setShowOrderModal(false);
      showToast('Draft order set successfully!', { type: 'success' });
      router.push(`/leagues/${leagueId}/draft?draftId=${draftStatus.draft_id}`);
    } catch (e: any) {
      showToast(e?.message || 'Failed to set draft order', { type: 'error' });
    }
  };

  const goToDraft = async () => {
    try {
      const status = await api.getDraftByLeague(leagueId);
      if (user) {
        try {
          await api.getUserTeamByLeague(leagueId, user.id);
        } catch {
          try {
            await api.createTeam(leagueId, user.id, `${user.username}'s Team`);
          } catch { }
        }
      }
      router.push(`/leagues/${leagueId}/draft?draftId=${status.draft_id}`);
    } catch (e: any) {
      showToast('No draft found for this league. Start one first.', { type: 'warning' });
    }
  };

  {/* Modal for setting draft order */ }

  const goToMyTeam = async () => {
    if (!user || !Number.isFinite(leagueId)) return;
    try {
      await api.getUserTeamByLeague(leagueId, user.id);
      router.push(`/leagues/${leagueId}/team`);
    } catch (e: any) {
      showToast('You do not have a team in this league yet. Join and draft first.', { type: 'info' });
    }
  };

  const goToSettings = () => {
    router.push(`/leagues/${leagueId}/settings`);
  };

  if (accessDenied) {
    return (
      <div className="card text-center py-16">
        <div className="mx-auto w-16 h-16 mb-4 rounded-full bg-red-100 flex items-center justify-center">
          <Shield className="h-8 w-8 text-red-600" />
        </div>
        <h2 className="text-xl font-bold text-red-600 mb-2">Access Denied</h2>
        <p className="text-gray-600 mb-6">You are not a member of this league.</p>
        <Link href="/leagues" className="btn-primary">
          Go to My Leagues
        </Link>
      </div>
    );
  }

  if (loading || !details) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-valorant-600"></div>
      </div>
    );
  }

  const usernameById: Record<number, string> = (details?.members || []).reduce((acc: Record<number, string>, m: any) => {
    acc[m.user_id] = m.username;
    return acc;
  }, {});

  const renderBoard = (board: LeagueLeaderboardEnvelope | null) => {
    if (!board) return <div className="text-sm text-gray-500">No scores yet.</div>;
    return (
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="py-2 pr-4">Rank</th>
              <th className="py-2 pr-4">Team</th>
              <th className="py-2 pr-4">Manager</th>
              <th className="py-2 pr-4 text-right">Score</th>
            </tr>
          </thead>
          <tbody>
            {board.teams.map((t, idx) => (
              <tr key={t.team_id} className="border-t border-gray-100">
                <td className="py-2 pr-4">{idx + 1}</td>
                <td className="py-2 pr-4">{t.team_name}</td>
                <td className="py-2 pr-4">{t.username || usernameById[t.user_id] || `User #${t.user_id}`}</td>
                <td className="py-2 pr-4 text-right font-semibold">{t.total_score.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{details.name}</h1>
            <p className="text-gray-600">{details.description}</p>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${draftStatus?.status === 'IN_PROGRESS'
              ? 'bg-yellow-100 text-yellow-800'
              : details.status === 'ACTIVE'
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
              }`}>
              {draftStatus?.status === 'IN_PROGRESS'
                ? 'DRAFTING'
                : String(details.status).toUpperCase()
              }
            </span>
            <div className="flex space-x-2">
              <button onClick={goToMyTeam} className="btn-secondary flex items-center">
                <User className="h-4 w-4 mr-2" />
                My Team
              </button>
              {details.members?.some((m: any) => user && m.user_id === user.id && m.is_commissioner) && (
                <button onClick={goToSettings} className="btn-secondary flex items-center">
                  <Settings className="h-4 w-4 mr-2" />
                  Settings
                </button>
              )}
              {draftStatus?.status === 'IN_PROGRESS' && (
                <button onClick={goToDraft} className="btn-secondary flex items-center">
                  <Play className="h-4 w-4 mr-2" />
                  Go To Draft
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center">
            <Users className="h-5 w-5 mr-2 text-valorant-600" /> Members ({details.member_count})
          </h2>
          <div className="space-y-2">
            {details.members.map((m: any) => (
              <div key={m.user_id} className="flex justify-between items-center text-sm">
                <div className="flex items-center">
                  <span className="font-medium">{m.username}</span>
                  {m.is_commissioner && (
                    <span className="ml-2 inline-flex items-center text-xs text-valorant-600"><Crown className="h-3 w-3 mr-1" /> Commissioner</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={async () => {
                      setViewTeamLoading(true);
                      setViewTeamModalOpen(true);
                      setViewingTeam({ name: '', ownerUsername: m.username, userId: m.user_id });
                      try {
                        const team = await api.getUserTeamByLeague(leagueId, m.user_id);
                        setViewingTeam({ name: team.name, ownerUsername: m.username, userId: m.user_id });
                        const players = await api.getTeamPlayers(team.id);
                        setViewingTeamPlayers(players);
                      } catch (e) {
                        showToast('Could not load team', { type: 'error' });
                        setViewTeamModalOpen(false);
                      } finally {
                        setViewTeamLoading(false);
                      }
                    }}
                    className="p-1 text-gray-400 hover:text-valorant-600 hover:bg-gray-100 rounded transition-colors"
                    title="View Team"
                  >
                    <Eye className="h-4 w-4" />
                  </button>
                  <span className="text-gray-500">{new Date(m.joined_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center">
            <Shield className="h-5 w-5 mr-2 text-valorant-600" /> Join Code
          </h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold tracking-widest">{details.join_pin || '------'}</div>
              <p className="text-xs text-gray-500">Share this PIN to invite others</p>
            </div>
            <button onClick={regeneratePin} disabled={pinLoading} className="btn-secondary">
              <RefreshCcw className={`h-4 w-4 inline mr-2 ${pinLoading ? 'animate-spin' : ''}`} />
              Regenerate
            </button>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center">
            <Calendar className="h-5 w-5 mr-2 text-valorant-600" /> Draft
          </h2>
          <div className="space-y-3">
            {/* Show different buttons based on draft status */}
            {draftStatus?.status === 'COMPLETED' ? (
              <>
                <button
                  onClick={() => router.push(`/leagues/${leagueId}/draft/results?draftId=${draftStatus.draft_id}`)}
                  className="btn-primary w-full flex items-center justify-center"
                >
                  <Eye className="h-4 w-4 mr-2" /> View Draft
                </button>
                {details.members?.some((m: any) => user && m.user_id === user.id && m.is_commissioner) && (
                  <button
                    onClick={async () => {
                      try {
                        await api.resetDraft(draftStatus.draft_id);
                        showToast('Draft reset successfully. You can now start a new draft.', { type: 'success' });
                        setDraftStatus(null);
                      } catch (e: any) {
                        showToast(e?.message || 'Failed to reset draft', { type: 'error' });
                      }
                    }}
                    className="btn-secondary w-full flex items-center justify-center"
                  >
                    <RefreshCcw className="h-4 w-4 mr-2" /> Start New Draft
                  </button>
                )}
              </>
            ) : (
              <>
                <button
                  onClick={startDraft}
                  className="btn-primary w-full flex items-center justify-center"
                  disabled={!!draftStatus && draftStatus.status !== 'PENDING'}
                >
                  <Play className="h-4 w-4 mr-2" /> Start Draft
                </button>
                {draftStatus?.status === 'PENDING' && (
                  <button
                    onClick={() => setShowOrderModal(true)}
                    className="btn-secondary w-full flex items-center justify-center"
                  >
                    <ListOrdered className="h-4 w-4 mr-2" /> Set Draft Order
                  </button>
                )}
              </>
            )}
          </div>
        </div>
        <div className="md:col-span-3 card">
          <h2 className="text-lg font-semibold mb-4">My Activity</h2>
          {!user || myActivity.length === 0 ? (
            <p className="text-sm text-gray-600">No pending trades.</p>
          ) : (
            <div className="space-y-4">
              {myActivity.map((t: any) => {
                const iAmSender = myTeamId && t.team1_id === myTeamId;
                const iAmRecipient = myTeamId && t.team2_id === myTeamId;


                // Organize trade items by team
                const team1Items = t.trade_items.filter((i: any) => i.team_id === t.team1_id);
                const team2Items = t.trade_items.filter((i: any) => i.team_id === t.team2_id);

                return (
                  <div key={t.id} className={`border-2 rounded-lg p-4 ${t.status === 'pending'
                    ? 'border-yellow-300 bg-yellow-50'
                    : t.status === 'accepted'
                      ? 'border-green-300 bg-green-50'
                      : 'border-gray-300 bg-gray-50'
                    }`}>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-medium text-gray-900">
                            Trade: {t.team1_name} ↔ {t.team2_name}
                          </h3>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${t.status === 'pending'
                            ? 'bg-yellow-200 text-yellow-800'
                            : t.status === 'accepted'
                              ? 'bg-green-200 text-green-800'
                              : t.status === 'rejected'
                                ? 'bg-red-200 text-red-800'
                                : 'bg-gray-200 text-gray-800'
                            }`}>
                            {t.status}
                          </span>

                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                          <div className="bg-white p-3 rounded border">
                            <div className="font-medium text-gray-700 mb-1">{t.team1_name} offers:</div>
                            <div className="text-gray-600">
                              {team1Items.map((i: any) => i.player_name).join(', ')}
                            </div>
                          </div>
                          <div className="bg-white p-3 rounded border">
                            <div className="font-medium text-gray-700 mb-1">{t.team2_name} offers:</div>
                            <div className="text-gray-600">
                              {team2Items.map((i: any) => i.player_name).join(', ')}
                            </div>
                          </div>
                        </div>

                        <div className="mt-2 text-xs text-gray-500">
                          Proposed: {new Date(t.proposed_at).toLocaleDateString()} at {new Date(t.proposed_at).toLocaleTimeString()}
                          {t.responded_at && (
                            <span> • Responded: {new Date(t.responded_at).toLocaleDateString()} at {new Date(t.responded_at).toLocaleTimeString()}</span>
                          )}
                        </div>
                      </div>

                      {t.status === 'pending' && (
                        <div className="ml-4 flex flex-col gap-2 min-w-max">
                          {/* Show for recipients */}
                          {(iAmRecipient || (!iAmSender && !iAmRecipient)) && (
                            <>
                              <button
                                onClick={async () => {
                                  try {
                                    await api.acceptTrade(t.id);
                                    showToast('Trade accepted successfully!', { type: 'success' });
                                    fetchDetails();
                                  } catch (e: any) {
                                    showToast(e?.message || 'Failed to accept trade', { type: 'error' });
                                  }
                                }}
                                className="btn-primary btn-sm hover:scale-105 transition-transform"
                              >
                                ✓ Accept Trade
                              </button>
                              <button
                                onClick={async () => {
                                  try {
                                    await api.rejectTrade(t.id);
                                    showToast('Trade rejected', { type: 'success' });
                                    fetchDetails();
                                  } catch (e: any) {
                                    showToast(e?.message || 'Failed to reject trade', { type: 'error' });
                                  }
                                }}
                                className="btn-secondary btn-sm hover:scale-105 transition-transform"
                              >
                                ✗ Reject Trade
                              </button>
                            </>
                          )}
                          {/* Show for senders */}
                          {iAmSender && (
                            <button
                              onClick={async () => {
                                try {
                                  await api.cancelTrade(t.id);
                                  showToast('Trade cancelled', { type: 'success' });
                                  fetchDetails();
                                } catch (e: any) {
                                  showToast(e?.message || 'Failed to cancel trade', { type: 'error' });
                                }
                              }}
                              className="btn-secondary btn-sm hover:scale-105 transition-transform"
                            >
                              🚫 Cancel Trade
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        <div className="md:col-span-3 card">
          <h2 className="text-lg font-semibold mb-4">League Activity</h2>
          {activity.length === 0 ? (
            <p className="text-sm text-gray-600">No recent activity.</p>
          ) : (
            <ul className="space-y-2 max-h-64 overflow-y-auto">
              {activity.map((a, idx) => (
                <li key={idx} className="text-sm flex items-start justify-between">
                  <span>{a.message}</span>
                  <span className="text-xs text-gray-500 ml-2">{new Date(a.timestamp).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Weekly Leaderboard</h2>
            <span className="text-xs text-gray-500">Last updated {weeklyBoard?.last_updated ? new Date(weeklyBoard.last_updated).toLocaleString() : '—'}</span>
          </div>
          {renderBoard(weeklyBoard)}
        </div>
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Season Leaderboard</h2>
            <span className="text-xs text-gray-500">Last updated {seasonBoard?.last_updated ? new Date(seasonBoard.last_updated).toLocaleString() : '—'}</span>
          </div>
          {renderBoard(seasonBoard)}
        </div>
      </div>

      {/* Modal: Set Draft Order */}
      <SetDraftOrderModal
        isOpen={showOrderModal}
        onClose={() => setShowOrderModal(false)}
        members={(details?.members || []).map((m: any) => ({ user_id: m.user_id, username: m.username }))}
        onSubmit={handleSaveOrder}
      />

      {/* Modal: View Team */}
      {viewTeamModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setViewTeamModalOpen(false)}>
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b">
              <div>
                <h3 className="text-lg font-semibold">{viewingTeam?.name || 'Loading...'}</h3>
                <p className="text-sm text-gray-500">Owner: {viewingTeam?.ownerUsername}</p>
              </div>
              <button
                onClick={() => setViewTeamModalOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {viewTeamLoading ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-valorant-600"></div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium text-green-600 mb-2 flex items-center">
                      <Users className="h-4 w-4 mr-1" /> Starters
                    </h4>
                    {viewingTeamPlayers.filter(p => p.is_starting).length === 0 ? (
                      <p className="text-sm text-gray-500">No starters</p>
                    ) : (
                      <ul className="space-y-1">
                        {viewingTeamPlayers.filter(p => p.is_starting).map(p => (
                          <li key={p.id} className="text-sm flex justify-between py-1 px-2 bg-green-50 rounded">
                            <span className="font-medium">{p.player_name}</span>
                            <span className="text-gray-500">{p.team}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div>
                    <h4 className="font-medium text-blue-600 mb-2 flex items-center">
                      <Users className="h-4 w-4 mr-1" /> Bench
                    </h4>
                    {viewingTeamPlayers.filter(p => !p.is_starting).length === 0 ? (
                      <p className="text-sm text-gray-500">No bench players</p>
                    ) : (
                      <ul className="space-y-1">
                        {viewingTeamPlayers.filter(p => !p.is_starting).map(p => (
                          <li key={p.id} className="text-sm flex justify-between py-1 px-2 bg-blue-50 rounded">
                            <span className="font-medium">{p.player_name}</span>
                            <span className="text-gray-500">{p.team}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


