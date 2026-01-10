'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import SidePanel from './SidePanel';
import { api } from '../utils/api';
import { TeamPlayer } from '../types/api';

interface TradePanelProps {
    isOpen: boolean;
    onClose: () => void;
    leagueId: number;
    teamId: number;
    teamPlayers: TeamPlayer[];
    leagueTeams: Array<{ id: number; name: string; user_id: number }>;
    currentUserId: number;
    onSuccess: () => void;
    showToast: (msg: string, opts?: { type: 'success' | 'error' | 'warning' }) => void;
}

export default function TradePanel({
    isOpen,
    onClose,
    leagueId,
    teamId,
    teamPlayers,
    leagueTeams,
    currentUserId,
    onSuccess,
    showToast,
}: TradePanelProps) {
    const [step, setStep] = useState(1);
    const [receivingTeamId, setReceivingTeamId] = useState<number | null>(null);
    const [receivingTeamPlayers, setReceivingTeamPlayers] = useState<TeamPlayer[]>([]);
    const [offeringPlayers, setOfferingPlayers] = useState<string[]>([]);
    const [requestingPlayers, setRequestingPlayers] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [loadingPlayers, setLoadingPlayers] = useState(false);

    // Get teams other than current user's
    const otherTeams = leagueTeams.filter(t => t.user_id !== currentUserId);

    // Load receiving team players when selected
    useEffect(() => {
        if (!receivingTeamId) {
            setReceivingTeamPlayers([]);
            return;
        }
        setLoadingPlayers(true);
        api.getTeamPlayers(receivingTeamId)
            .then(players => setReceivingTeamPlayers(players))
            .catch(() => setReceivingTeamPlayers([]))
            .finally(() => setLoadingPlayers(false));
    }, [receivingTeamId]);

    // Reset on close
    useEffect(() => {
        if (!isOpen) {
            setStep(1);
            setReceivingTeamId(null);
            setOfferingPlayers([]);
            setRequestingPlayers([]);
        }
    }, [isOpen]);

    const handleSubmitTrade = async () => {
        if (!receivingTeamId || offeringPlayers.length === 0 || requestingPlayers.length === 0) {
            showToast('Please complete all trade selections', { type: 'warning' });
            return;
        }
        setLoading(true);
        try {
            await api.proposeTrade(
                leagueId,
                teamId,
                receivingTeamId,
                offeringPlayers,
                requestingPlayers
            );
            showToast('Trade proposal sent!', { type: 'success' });
            onSuccess();
            onClose();
        } catch (e: any) {
            showToast(e?.message || 'Failed to send trade', { type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const togglePlayer = (list: string[], setList: (l: string[]) => void, name: string) => {
        if (list.includes(name)) {
            setList(list.filter(x => x !== name));
        } else {
            setList([...list, name]);
        }
    };

    const renderFooter = () => {
        if (step === 1) {
            return (
                <button
                    onClick={() => setStep(2)}
                    disabled={!receivingTeamId}
                    className="w-full py-3 px-4 font-medium rounded-lg bg-valorant-600 hover:bg-valorant-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                    Next <ChevronRight className="w-4 h-4" />
                </button>
            );
        }
        if (step === 2) {
            return (
                <div className="flex gap-2">
                    <button
                        onClick={() => setStep(1)}
                        className="flex-1 py-3 px-4 font-medium rounded-lg border border-gray-600 text-white hover:bg-gray-700 transition-colors flex items-center justify-center gap-2"
                    >
                        <ChevronLeft className="w-4 h-4" /> Back
                    </button>
                    <button
                        onClick={() => setStep(3)}
                        disabled={offeringPlayers.length === 0}
                        className="flex-1 py-3 px-4 font-medium rounded-lg bg-valorant-600 hover:bg-valorant-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                    >
                        Next <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            );
        }
        if (step === 3) {
            return (
                <div className="flex gap-2">
                    <button
                        onClick={() => setStep(2)}
                        className="flex-1 py-3 px-4 font-medium rounded-lg border border-gray-600 text-white hover:bg-gray-700 transition-colors flex items-center justify-center gap-2"
                    >
                        <ChevronLeft className="w-4 h-4" /> Back
                    </button>
                    <button
                        onClick={() => setStep(4)}
                        disabled={requestingPlayers.length === 0}
                        className="flex-1 py-3 px-4 font-medium rounded-lg bg-valorant-600 hover:bg-valorant-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                    >
                        Review <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            );
        }
        // Step 4: Review
        return (
            <div className="flex gap-2">
                <button
                    onClick={() => setStep(3)}
                    className="flex-1 py-3 px-4 font-medium rounded-lg border border-gray-600 text-white hover:bg-gray-700 transition-colors flex items-center justify-center gap-2"
                >
                    <ChevronLeft className="w-4 h-4" /> Back
                </button>
                <button
                    onClick={handleSubmitTrade}
                    disabled={loading}
                    className="flex-1 py-3 px-4 font-medium rounded-lg bg-green-600 hover:bg-green-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {loading ? 'Sending...' : 'Send Trade'}
                </button>
            </div>
        );
    };

    const selectedTeamName = otherTeams.find(t => t.id === receivingTeamId)?.name || '';

    return (
        <SidePanel
            isOpen={isOpen}
            onClose={onClose}
            title="Propose Trade"
            footer={renderFooter()}
        >
            {/* Step Indicator */}
            <div className="flex items-center justify-between mb-6">
                {[1, 2, 3, 4].map(s => (
                    <div
                        key={s}
                        className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-colors ${step >= s
                            ? 'bg-valorant-600 text-white'
                            : 'bg-gray-700 text-gray-400'
                            }`}
                    >
                        {s}
                    </div>
                ))}
            </div>

            {/* Step 1: Select Team */}
            {step === 1 && (
                <div>
                    <label className="text-sm font-medium text-gray-400 mb-3 block">
                        Select team to trade with
                    </label>
                    <div className="space-y-2">
                        {otherTeams.map(t => (
                            <button
                                key={t.id}
                                onClick={() => setReceivingTeamId(t.id)}
                                className={`w-full p-4 rounded-lg border transition-colors text-left ${receivingTeamId === t.id
                                    ? 'border-valorant-500 bg-valorant-900/20'
                                    : 'border-gray-600 hover:border-gray-500'
                                    }`}
                                style={{ backgroundColor: 'rgb(30, 41, 52)' }}
                            >
                                <div className="font-medium text-white">{t.name}</div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Step 2: Select Players to Offer */}
            {step === 2 && (
                <div>
                    <label className="text-sm font-medium text-gray-400 mb-3 block">
                        Select players to offer
                    </label>
                    <div className="space-y-2 max-h-80 overflow-y-auto">
                        {teamPlayers.map(p => (
                            <button
                                key={p.id}
                                onClick={() => togglePlayer(offeringPlayers, setOfferingPlayers, p.player_name)}
                                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-colors text-left ${offeringPlayers.includes(p.player_name)
                                    ? 'border-valorant-500 bg-valorant-900/20'
                                    : 'border-gray-600 hover:border-gray-500'
                                    }`}
                                style={{ backgroundColor: 'rgb(30, 41, 52)' }}
                            >
                                <div>
                                    <div className="font-medium text-white text-sm">{p.player_name}</div>
                                    <div className="text-xs text-gray-400">{p.team}</div>
                                </div>
                                {offeringPlayers.includes(p.player_name) && (
                                    <span className="text-xs text-valorant-400 font-medium">Offering</span>
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Step 3: Select Players to Request */}
            {step === 3 && (
                <div>
                    <label className="text-sm font-medium text-gray-400 mb-3 block">
                        Select players to request from {selectedTeamName}
                    </label>
                    {loadingPlayers ? (
                        <div className="text-center text-gray-400 py-4">Loading players...</div>
                    ) : receivingTeamPlayers.length === 0 ? (
                        <div className="text-center text-gray-400 py-4">No players found</div>
                    ) : (
                        <div className="space-y-2 max-h-80 overflow-y-auto">
                            {receivingTeamPlayers.map(p => (
                                <button
                                    key={p.id}
                                    onClick={() => togglePlayer(requestingPlayers, setRequestingPlayers, p.player_name)}
                                    className={`w-full flex items-center justify-between p-3 rounded-lg border transition-colors text-left ${requestingPlayers.includes(p.player_name)
                                        ? 'border-green-500 bg-green-900/20'
                                        : 'border-gray-600 hover:border-gray-500'
                                        }`}
                                    style={{ backgroundColor: 'rgb(30, 41, 52)' }}
                                >
                                    <div>
                                        <div className="font-medium text-white text-sm">{p.player_name}</div>
                                        <div className="text-xs text-gray-400">{p.team}</div>
                                    </div>
                                    {requestingPlayers.includes(p.player_name) && (
                                        <span className="text-xs text-green-400 font-medium">Requesting</span>
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Step 4: Review */}
            {step === 4 && (
                <div className="space-y-6">
                    <div>
                        <label className="text-sm font-medium text-gray-400 mb-2 block">
                            Trading with
                        </label>
                        <div className="p-3 rounded-lg border border-gray-600 text-white" style={{ backgroundColor: 'rgb(30, 41, 52)' }}>
                            {selectedTeamName}
                        </div>
                    </div>

                    <div>
                        <label className="text-sm font-medium text-gray-400 mb-2 block">
                            You are offering ({offeringPlayers.length})
                        </label>
                        <div className="space-y-1">
                            {offeringPlayers.map(name => (
                                <div key={name} className="p-2 rounded bg-red-900/20 text-red-200 text-sm">
                                    {name}
                                </div>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="text-sm font-medium text-gray-400 mb-2 block">
                            You are requesting ({requestingPlayers.length})
                        </label>
                        <div className="space-y-1">
                            {requestingPlayers.map(name => (
                                <div key={name} className="p-2 rounded bg-green-900/20 text-green-200 text-sm">
                                    {name}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </SidePanel>
    );
}
