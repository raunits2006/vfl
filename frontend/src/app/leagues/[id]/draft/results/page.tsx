'use client';

import { useEffect, useState, useMemo } from 'react';
import { useSearchParams, useParams, useRouter } from 'next/navigation';
import { api, ApiError } from '../../../../../utils/api';
import { useAuth } from '../../../../../contexts/AuthContext';
import { useToast } from '../../../../../components/ToastProvider';
import { Trophy, Users, ArrowLeft } from 'lucide-react';
import type { DraftPickDetailed, DraftStatus } from '../../../../../types/api';

export default function DraftResultsPage() {
    const params = useParams<{ id: string }>();
    const leagueId = Number(params.id);
    const searchParams = useSearchParams();
    const draftId = Number(searchParams.get('draftId'));
    const router = useRouter();
    const { user, loading: authLoading } = useAuth();
    const { showToast } = useToast();

    const [loading, setLoading] = useState(true);
    const [picks, setPicks] = useState<DraftPickDetailed[]>([]);
    const [draftStatus, setDraftStatus] = useState<DraftStatus | null>(null);
    const [leagueName, setLeagueName] = useState('');
    const [viewMode, setViewMode] = useState<'player' | 'round'>('player');

    // Calculate draft order from picks (unique team_ids in pick order)
    const draftOrder = useMemo(() => {
        if (picks.length === 0) return [];
        const numTeams = new Set(picks.map(p => p.team_id)).size;
        // First round picks give us the draft order
        return picks.slice(0, numTeams);
    }, [picks]);

    const numTeams = useMemo(() => new Set(picks.map(p => p.team_id)).size, [picks]);

    // Group picks by player (fantasy team owner)
    const picksByPlayer = useMemo(() => {
        const grouped: Record<number, { team_name: string; username: string; picks: DraftPickDetailed[] }> = {};
        for (const pick of picks) {
            if (!grouped[pick.team_id]) {
                grouped[pick.team_id] = {
                    team_name: pick.team_name,
                    username: pick.username,
                    picks: [],
                };
            }
            grouped[pick.team_id].picks.push(pick);
        }
        // Sort by first pick number (draft order)
        return Object.values(grouped).sort((a, b) =>
            (a.picks[0]?.pick_number || 0) - (b.picks[0]?.pick_number || 0)
        );
    }, [picks]);

    // Group picks by round
    const picksByRound = useMemo(() => {
        if (numTeams === 0) return [];
        const rounds: DraftPickDetailed[][] = [];
        for (let i = 0; i < picks.length; i += numTeams) {
            rounds.push(picks.slice(i, i + numTeams));
        }
        return rounds;
    }, [picks, numTeams]);

    // Calculate round and pick-in-round for a given pick number
    const getPickLabel = (pickNumber: number): string => {
        if (numTeams === 0) return String(pickNumber);
        const round = Math.ceil(pickNumber / numTeams);
        const pickInRound = ((pickNumber - 1) % numTeams) + 1;
        return `${round}.${String(pickInRound).padStart(2, '0')}`;
    };

    // Get round number for a pick
    const getRound = (pickNumber: number): number => {
        if (numTeams === 0) return 1;
        return Math.ceil(pickNumber / numTeams);
    };

    useEffect(() => {
        if (!authLoading && !user) {
            router.replace('/signin');
            return;
        }

        if (!draftId || !Number.isFinite(leagueId)) {
            setLoading(false);
            return;
        }

        const fetchData = async () => {
            try {
                // Fetch draft results
                const results = await api.getDraftResults(draftId);
                setPicks(results);

                // Fetch draft status
                const status = await api.getDraftStatus(draftId);
                setDraftStatus(status);

                // Fetch league details for name
                const leagueDetails = await api.getLeagueDetails(leagueId);
                setLeagueName(leagueDetails.name);
            } catch (e) {
                if (e instanceof ApiError) {
                    if (e.status === 403) {
                        showToast('You do not have access to view this draft.', { type: 'error' });
                        router.push(`/leagues/${leagueId}`);
                        return;
                    }
                }
                showToast('Failed to load draft results', { type: 'error' });
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [draftId, leagueId, authLoading, user, router, showToast]);

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-valorant-600"></div>
            </div>
        );
    }

    if (!draftId) {
        return (
            <div className="card text-center py-12">
                <h2 className="text-xl font-bold mb-2">No draft found</h2>
                <p className="text-gray-600 mb-4">Could not find draft results to display.</p>
                <button onClick={() => router.push(`/leagues/${leagueId}`)} className="btn-secondary">
                    <ArrowLeft className="h-4 w-4 mr-2 inline" /> Back to League
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="card">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => router.push(`/leagues/${leagueId}`)}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            <ArrowLeft className="h-5 w-5" />
                        </button>
                        <div>
                            <h1 className="text-2xl font-bold flex items-center gap-2">
                                <Trophy className="h-6 w-6 text-yellow-500" />
                                Draft Results
                            </h1>
                            <p className="text-gray-600">{leagueName}</p>
                        </div>
                    </div>
                    <div className="text-sm text-gray-500">
                        {picks.length} picks • {numTeams} teams
                    </div>
                </div>
            </div>

            {/* View Toggle */}
            <div className="flex justify-center">
                <div className="bg-gray-100 p-1 rounded-lg inline-flex">
                    <button
                        onClick={() => setViewMode('player')}
                        className={`px-4 py-2 rounded-md font-medium transition-colors ${viewMode === 'player'
                                ? 'bg-valorant-600 text-white'
                                : 'text-gray-600 hover:text-gray-900'
                            }`}
                    >
                        <Users className="h-4 w-4 inline mr-2" />
                        By Player
                    </button>
                    <button
                        onClick={() => setViewMode('round')}
                        className={`px-4 py-2 rounded-md font-medium transition-colors ${viewMode === 'round'
                                ? 'bg-valorant-600 text-white'
                                : 'text-gray-600 hover:text-gray-900'
                            }`}
                    >
                        <Trophy className="h-4 w-4 inline mr-2" />
                        By Round
                    </button>
                </div>
            </div>

            {/* By Player View */}
            {viewMode === 'player' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {picksByPlayer.map((player, idx) => (
                        <div key={player.team_name} className="card">
                            <div className="flex items-center gap-2 mb-4 pb-3 border-b">
                                <Trophy className="h-5 w-5 text-valorant-600" />
                                <div>
                                    <h3 className="font-semibold">{player.team_name}</h3>
                                    <p className="text-sm text-gray-500">{player.username}</p>
                                </div>
                            </div>
                            <table className="w-full">
                                <thead>
                                    <tr className="text-left text-xs text-gray-500 uppercase">
                                        <th className="pb-2 w-12">No.</th>
                                        <th className="pb-2">Player</th>
                                        <th className="pb-2 w-16 text-right">Round</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {player.picks.map((pick, pickIdx) => (
                                        <tr key={pick.id} className="border-t border-gray-100">
                                            <td className="py-2 text-sm font-medium">{pickIdx + 1}</td>
                                            <td className="py-2">
                                                <div className="font-medium">{pick.player_name}</div>
                                                <div className="text-xs text-gray-500">{pick.player_team}</div>
                                            </td>
                                            <td className="py-2 text-right text-sm">{getRound(pick.pick_number)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ))}
                </div>
            )}

            {/* By Round View */}
            {viewMode === 'round' && (
                <div className="space-y-6">
                    {picksByRound.map((roundPicks, roundIdx) => (
                        <div key={roundIdx} className="card">
                            <h3 className="text-lg font-semibold mb-4 pb-2 border-b">
                                Round {roundIdx + 1}
                            </h3>
                            <table className="w-full">
                                <thead>
                                    <tr className="text-left text-xs text-gray-500 uppercase">
                                        <th className="pb-2 w-12">No.</th>
                                        <th className="pb-2">Player</th>
                                        <th className="pb-2 text-right">Team</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {roundPicks.map((pick, pickIdx) => (
                                        <tr key={pick.id} className="border-t border-gray-100">
                                            <td className="py-2 text-sm font-medium">{pickIdx + 1}</td>
                                            <td className="py-2">
                                                <div className="font-medium">{pick.player_name}</div>
                                                <div className="text-xs text-gray-500">{pick.player_team}</div>
                                            </td>
                                            <td className="py-2 text-right">
                                                <div className="text-sm font-medium">{pick.team_name}</div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
