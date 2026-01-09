'use client';

import { useState, useMemo } from 'react';
import SidePanel from './SidePanel';
import { api } from '../utils/api';

// Agent to class mapping
const AGENT_GROUPS: Record<string, string[]> = {
    'Duelist': ['Jett', 'Phoenix', 'Neon', 'Raze', 'Reyna', 'Yoru', 'Iso', 'Waylay'],
    'Controller': ['Astra', 'Brimstone', 'Omen', 'Viper', 'Harbor', 'Clove'],
    'Initiator': ['Breach', 'Gekko', 'KAY/O', 'Skye', 'Sova', 'Fade', 'Tejo'],
    'Sentinel': ['Chamber', 'Cypher', 'Deadlock', 'Killjoy', 'Sage', 'Vyse'],
};

const ALL_ROLES = Object.keys(AGENT_GROUPS);
const ALL_AGENTS = Object.values(AGENT_GROUPS).flat().sort();

interface AgentSelectionPanelProps {
    isOpen: boolean;
    onClose: () => void;
    playerName: string;
    teamId: number;
    existingAgents: string[];
    onSave: () => void;
}

export default function AgentSelectionPanel({
    isOpen,
    onClose,
    playerName,
    teamId,
    existingAgents,
    onSave,
}: AgentSelectionPanelProps) {
    // Each slot has optional role filter and selected agent
    const [slots, setSlots] = useState<Array<{ role: string; agent: string }>>(() =>
        existingAgents.length === 3
            ? existingAgents.map(agent => ({
                role: Object.entries(AGENT_GROUPS).find(([_, agents]) => agents.includes(agent))?.[0] || '',
                agent,
            }))
            : [{ role: '', agent: '' }, { role: '', agent: '' }, { role: '', agent: '' }]
    );
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Reset slots when panel opens with new data
    useMemo(() => {
        if (isOpen) {
            setSlots(
                existingAgents.length === 3
                    ? existingAgents.map(agent => ({
                        role: Object.entries(AGENT_GROUPS).find(([_, agents]) => agents.includes(agent))?.[0] || '',
                        agent,
                    }))
                    : [{ role: '', agent: '' }, { role: '', agent: '' }, { role: '', agent: '' }]
            );
            setError(null);
        }
    }, [isOpen, existingAgents]);

    const getAvailableAgents = (slotIndex: number) => {
        // Allow duplicate agents (player can pick same agent across multiple maps)
        const role = slots[slotIndex].role;
        return role ? AGENT_GROUPS[role] || [] : ALL_AGENTS;
    };

    const updateSlot = (index: number, field: 'role' | 'agent', value: string) => {
        setSlots(prev => {
            const newSlots = [...prev];
            if (field === 'role') {
                // When role changes, clear agent if it's not in the new role
                const newAgentPool = value ? AGENT_GROUPS[value] || [] : ALL_AGENTS;
                newSlots[index] = {
                    role: value,
                    agent: newAgentPool.includes(newSlots[index].agent) ? newSlots[index].agent : '',
                };
            } else {
                newSlots[index] = { ...newSlots[index], agent: value };
            }
            return newSlots;
        });
        setError(null);
    };

    const allSelected = slots.every(s => s.agent);

    const handleSave = async () => {
        if (!allSelected) return;

        setSaving(true);
        setError(null);

        try {
            await api.setAgentPrediction(teamId, playerName, slots.map(s => s.agent));
            onSave();
            onClose();
        } catch (e: any) {
            setError(e?.message || 'Failed to save agent predictions');
        } finally {
            setSaving(false);
        }
    };

    return (
        <SidePanel
            isOpen={isOpen}
            onClose={onClose}
            title={`Select Agents for ${playerName}`}
            footer={
                <div className="space-y-3">
                    {error && (
                        <div className="p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
                            {error}
                        </div>
                    )}
                    <button
                        onClick={handleSave}
                        disabled={!allSelected || saving}
                        className={`w-full py-3 px-4 font-medium rounded-lg transition-colors ${allSelected && !saving
                            ? 'bg-valorant-600 hover:bg-valorant-700 text-white'
                            : 'bg-gray-600 text-gray-400 cursor-not-allowed'
                            }`}
                    >
                        {saving ? 'Saving...' : 'Save Agents'}
                    </button>
                </div>
            }
        >
            <p className="text-gray-300 mb-6">
                Select 3 agents for <strong className="text-white">{playerName}</strong>.
                Optionally filter by role first, or select any agent directly.
            </p>

            <div className="space-y-6">
                {[0, 1, 2].map(index => (
                    <div key={index} className="space-y-2">
                        <label className="text-sm font-medium text-gray-400">Agent {index + 1}</label>

                        {/* Role dropdown (optional filter) */}
                        <select
                            value={slots[index].role}
                            onChange={e => updateSlot(index, 'role', e.target.value)}
                            className="w-full p-3 rounded-lg border border-gray-600 text-white transition-colors focus:border-valorant-500 focus:outline-none"
                            style={{ backgroundColor: 'rgb(30, 41, 52)' }}
                        >
                            <option value="">All Roles</option>
                            {ALL_ROLES.map(role => (
                                <option key={role} value={role}>{role}</option>
                            ))}
                        </select>

                        {/* Agent dropdown */}
                        <select
                            value={slots[index].agent}
                            onChange={e => updateSlot(index, 'agent', e.target.value)}
                            className="w-full p-3 rounded-lg border border-gray-600 text-white transition-colors focus:border-valorant-500 focus:outline-none"
                            style={{ backgroundColor: 'rgb(30, 41, 52)' }}
                        >
                            <option value="">Select Agent</option>
                            {getAvailableAgents(index).map(agent => (
                                <option key={agent} value={agent}>{agent}</option>
                            ))}
                        </select>
                    </div>
                ))}
            </div>
        </SidePanel>
    );
}
