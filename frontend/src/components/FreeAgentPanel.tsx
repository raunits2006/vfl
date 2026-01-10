'use client';

import { useState, useMemo } from 'react';
import { Search } from 'lucide-react';
import SidePanel from './SidePanel';
import { api } from '../utils/api';
import { TeamPlayer, FreeAgent } from '../types/api';

interface FreeAgentPanelProps {
    isOpen: boolean;
    onClose: () => void;
    leagueId: number;
    teamId: number;
    teamPlayers: TeamPlayer[];
    freeAgents: FreeAgent[];
    isLocked: boolean;
    onSuccess: () => void;
    showToast: (msg: string, opts?: { type: 'success' | 'error' | 'warning' }) => void;
}

export default function FreeAgentPanel({
    isOpen,
    onClose,
    leagueId,
    teamId,
    teamPlayers,
    freeAgents,
    isLocked,
    onSuccess,
    showToast,
}: FreeAgentPanelProps) {
    const [mode, setMode] = useState<'drop' | 'add' | 'swap'>('swap');
    const [dropSelection, setDropSelection] = useState<string | null>(null);
    const [addSelection, setAddSelection] = useState<string | null>(null);
    const [searchDrop, setSearchDrop] = useState('');
    const [searchAdd, setSearchAdd] = useState('');
    const [loading, setLoading] = useState(false);

    // Filter players based on search
    const filteredTeamPlayers = useMemo(() => {
        if (!searchDrop) return teamPlayers;
        const q = searchDrop.toLowerCase();
        return teamPlayers.filter(p =>
            p.player_name.toLowerCase().includes(q) ||
            p.team.toLowerCase().includes(q)
        );
    }, [teamPlayers, searchDrop]);

    const filteredFreeAgents = useMemo(() => {
        if (!searchAdd) return freeAgents;
        const q = searchAdd.toLowerCase();
        return freeAgents.filter(p =>
            p.player_name.toLowerCase().includes(q) ||
            p.team.toLowerCase().includes(q)
        );
    }, [freeAgents, searchAdd]);

    const handleDrop = async () => {
        if (!dropSelection) {
            showToast('Select a player to drop', { type: 'warning' });
            return;
        }
        setLoading(true);
        try {
            const res = await api.dropPlayer(leagueId, teamId, dropSelection);
            showToast(res.message, { type: 'success' });
            onSuccess();
            setDropSelection(null);
            onClose();
        } catch (e: any) {
            showToast(e?.message || 'Drop failed', { type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async () => {
        if (!addSelection) {
            showToast('Select a player to add', { type: 'warning' });
            return;
        }
        setLoading(true);
        try {
            const res = await api.addFreeAgent(leagueId, teamId, addSelection);
            showToast(res.message, { type: 'success' });
            onSuccess();
            setAddSelection(null);
            onClose();
        } catch (e: any) {
            showToast(e?.message || 'Add failed', { type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleSwap = async () => {
        if (!dropSelection || !addSelection) {
            showToast('Select both a player to drop and a player to add', { type: 'warning' });
            return;
        }
        setLoading(true);
        try {
            const res = await api.swapFreeAgent(leagueId, teamId, dropSelection, addSelection);
            showToast(res.message, { type: 'success' });
            onSuccess();
            setDropSelection(null);
            setAddSelection(null);
            onClose();
        } catch (e: any) {
            showToast(e?.message || 'Swap failed', { type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const renderFooter = () => {
        if (isLocked) {
            return <div className="text-center text-gray-400">Team changes are locked</div>;
        }

        return (
            <div className="flex gap-2">
                {mode === 'drop' && (
                    <button
                        onClick={handleDrop}
                        disabled={!dropSelection || loading}
                        className="flex-1 py-3 px-4 font-medium rounded-lg bg-red-600 hover:bg-red-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {loading ? 'Dropping...' : 'Drop Player'}
                    </button>
                )}
                {mode === 'add' && (
                    <button
                        onClick={handleAdd}
                        disabled={!addSelection || loading}
                        className="flex-1 py-3 px-4 font-medium rounded-lg bg-green-600 hover:bg-green-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {loading ? 'Adding...' : 'Add Player'}
                    </button>
                )}
                {mode === 'swap' && (
                    <button
                        onClick={handleSwap}
                        disabled={!dropSelection || !addSelection || loading}
                        className="flex-1 py-3 px-4 font-medium rounded-lg bg-valorant-600 hover:bg-valorant-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {loading ? 'Swapping...' : 'Swap Players'}
                    </button>
                )}
            </div>
        );
    };

    return (
        <SidePanel
            isOpen={isOpen}
            onClose={onClose}
            title="Free Agents"
            footer={renderFooter()}
        >
            {/* Mode Tabs */}
            <div className="flex border-b border-gray-600 mb-4">
                {(['drop', 'add', 'swap'] as const).map(m => (
                    <button
                        key={m}
                        onClick={() => setMode(m)}
                        className={`flex-1 py-2 text-sm font-medium capitalize transition-colors ${mode === m
                            ? 'text-valorant-400 border-b-2 border-valorant-400'
                            : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        {m}
                    </button>
                ))}
            </div>

            {/* Drop Player Section */}
            {(mode === 'drop' || mode === 'swap') && (
                <div className="mb-4">
                    <label className="text-sm font-medium text-gray-400 mb-2 block">
                        {mode === 'swap' ? 'Select player to drop' : 'Select player to drop'}
                    </label>
                    <div className="relative mb-2">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search your players..."
                            value={searchDrop}
                            onChange={e => setSearchDrop(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-600 text-white text-sm focus:border-valorant-500 focus:outline-none"
                            style={{ backgroundColor: 'rgb(30, 41, 52)' }}
                        />
                    </div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                        {filteredTeamPlayers.map(p => (
                            <button
                                key={p.id}
                                onClick={() => setDropSelection(dropSelection === p.player_name ? null : p.player_name)}
                                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-colors text-left ${dropSelection === p.player_name
                                    ? 'border-red-500 bg-red-900/20'
                                    : 'border-gray-600 hover:border-gray-500'
                                    }`}
                                style={{ backgroundColor: 'rgb(30, 41, 52)' }}
                            >
                                <div>
                                    <div className="font-medium text-white text-sm">{p.player_name}</div>
                                    <div className="text-xs text-gray-400">{p.team}</div>
                                </div>
                                {dropSelection === p.player_name && (
                                    <span className="text-xs text-red-400 font-medium">Drop</span>
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Add Player Section */}
            {(mode === 'add' || mode === 'swap') && (
                <div>
                    <label className="text-sm font-medium text-gray-400 mb-2 block">
                        {mode === 'swap' ? 'Select free agent to add' : 'Select free agent to add'}
                    </label>
                    <div className="relative mb-2">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search free agents..."
                            value={searchAdd}
                            onChange={e => setSearchAdd(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-600 text-white text-sm focus:border-valorant-500 focus:outline-none"
                            style={{ backgroundColor: 'rgb(30, 41, 52)' }}
                        />
                    </div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                        {filteredFreeAgents.map(fa => (
                            <button
                                key={fa.player_name}
                                onClick={() => setAddSelection(addSelection === fa.player_name ? null : fa.player_name)}
                                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-colors text-left ${addSelection === fa.player_name
                                    ? 'border-green-500 bg-green-900/20'
                                    : 'border-gray-600 hover:border-gray-500'
                                    }`}
                                style={{ backgroundColor: 'rgb(30, 41, 52)' }}
                            >
                                <div>
                                    <div className="font-medium text-white text-sm">{fa.player_name}</div>
                                    <div className="text-xs text-gray-400">{fa.team}</div>
                                </div>
                                {addSelection === fa.player_name && (
                                    <span className="text-xs text-green-400 font-medium">Add</span>
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </SidePanel>
    );
}
