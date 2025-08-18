'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '../../../../contexts/AuthContext';
import { api } from '../../../../utils/api';
import type { LeagueSettings } from '../../../../types/api';
import { useToast } from '../../../../components/ToastProvider';

export default function LeagueSettingsPage() {
  const params = useParams<{ id: string }>();
  const leagueId = Number(params.id);
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { showToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [details, setDetails] = useState<any>(null);
  const [settings, setSettings] = useState<LeagueSettings | null>(null);

  const isCommissioner = useMemo(() => {
    if (!details || !user) return false;
    return (details.members || []).some((m: any) => m.user_id === user.id && m.is_commissioner);
  }, [details, user]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace('/signin');
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    let active = true;
    async function load() {
      if (!Number.isFinite(leagueId)) return;
      setLoading(true);
      try {
        const [d, s] = await Promise.all([
          api.getLeagueDetails(leagueId),
          api.getLeagueSettings(leagueId),
        ]);
        if (!active) return;
        setDetails(d);
        setSettings(s);
      } catch (e: any) {
        showToast(e?.message || 'Failed to load settings', { type: 'error' });
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => { active = false; };
  }, [leagueId, showToast]);

  const updateField = (key: keyof LeagueSettings, value: any) => {
    setSettings(prev => prev ? { ...prev, [key]: value } : prev);
  };

  const save = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const payload: any = {
        max_players: Number(settings.max_players),
        starting_players: Number(settings.starting_players),
        bench_players: Number(settings.bench_players),
        points_per_kill: Number(settings.points_per_kill),
        points_per_assist: Number(settings.points_per_assist),
        use_best_2_of_3: !!settings.use_best_2_of_3,
        draft_type: String(settings.draft_type || 'snake'),
        agent_exact_match_multiplier: Number(settings.agent_exact_match_multiplier),
        agent_class_match_multiplier: Number(settings.agent_class_match_multiplier),
        agent_miss_multiplier: Number(settings.agent_miss_multiplier),
      };
      if (payload.starting_players + payload.bench_players !== payload.max_players) {
        showToast('Starting + Bench must equal Max Players', { type: 'warning' });
        setSaving(false);
        return;
      }
      const updated = await api.updateLeagueSettings(leagueId, payload);
      setSettings(updated);
      showToast('Settings saved', { type: 'success' });
      // Redirect to league details
      if (typeof window !== 'undefined') {
        window.location.href = `/leagues/${leagueId}`;
      }
    } catch (e: any) {
      showToast(e?.message || 'Failed to save settings', { type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  if (loading || !details || !settings) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-valorant-600"></div>
      </div>
    );
  }

  if (!isCommissioner) {
    return (
      <div className="card">
        <h2 className="text-xl font-bold mb-2">Access denied</h2>
        <p className="text-gray-600">Only the league commissioner can edit settings.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">League Settings</h2>
            <p className="text-gray-600">{details.name}</p>
          </div>
          <button onClick={save} disabled={saving} className="btn-primary disabled:opacity-50">
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Roster</h3>
          <div className="space-y-3">
            <label className="block">
              <span className="text-sm text-gray-700">Max Players</span>
              <input type="number" min={1} value={settings.max_players}
                     onChange={e => updateField('max_players', Number(e.target.value))}
                     className="input-field mt-1" />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="text-sm text-gray-700">Starters</span>
                <input type="number" min={0} value={settings.starting_players}
                       onChange={e => updateField('starting_players', Number(e.target.value))}
                       className="input-field mt-1" />
              </label>
              <label className="block">
                <span className="text-sm text-gray-700">Bench</span>
                <input type="number" min={0} value={settings.bench_players}
                       onChange={e => updateField('bench_players', Number(e.target.value))}
                       className="input-field mt-1" />
              </label>
            </div>
            <p className="text-xs text-gray-500">Starters + Bench must equal Max Players.</p>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Scoring</h3>
          <div className="space-y-3">
            <label className="block">
              <span className="text-sm text-gray-700">Points per Kill</span>
              <input type="number" step="0.01" min={0} value={settings.points_per_kill}
                     onChange={e => updateField('points_per_kill', Number(e.target.value))}
                     className="input-field mt-1" />
            </label>
            <label className="block">
              <span className="text-sm text-gray-700">Points per Assist</span>
              <input type="number" step="0.01" min={0} value={settings.points_per_assist}
                     onChange={e => updateField('points_per_assist', Number(e.target.value))}
                     className="input-field mt-1" />
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={!!settings.use_best_2_of_3}
                     onChange={e => updateField('use_best_2_of_3', e.target.checked)} />
              <span className="text-sm text-gray-700">Use Best 2 of 3 scoring</span>
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <label className="block">
                <span className="block text-sm text-gray-700 leading-tight min-h-10" title="Exact Agent Match Multiplier">Exact Agent Match Multiplier</span>
                <input type="number" step="0.01" min={0} value={settings.agent_exact_match_multiplier ?? 1.0}
                       onChange={e => updateField('agent_exact_match_multiplier', Number(e.target.value))}
                       className="input-field mt-1" />
              </label>
              <label className="block">
                <span className="block text-sm text-gray-700 leading-tight min-h-10" title="Class Match Multiplier">Class Match Multiplier</span>
                <input type="number" step="0.01" min={0} value={settings.agent_class_match_multiplier ?? 0.5}
                       onChange={e => updateField('agent_class_match_multiplier', Number(e.target.value))}
                       className="input-field mt-1" />
              </label>
              <label className="block">
                <span className="block text-sm text-gray-700 leading-tight min-h-10" title="Miss Multiplier">Miss Multiplier</span>
                <input type="number" step="0.01" min={0} value={settings.agent_miss_multiplier ?? 0.25}
                       onChange={e => updateField('agent_miss_multiplier', Number(e.target.value))}
                       className="input-field mt-1" />
              </label>
            </div>
          </div>
        </div>

        <div className="md:col-span-2 card">
          <h3 className="text-lg font-semibold mb-4">Commissioners</h3>
          <div className="space-y-2">
            {(details.members || []).map((m: any) => (
              <div key={m.user_id} className="flex items-center justify-between text-sm">
                <div>{m.username}</div>
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!m.is_commissioner}
                    onChange={async (e) => {
                      const next = e.target.checked;
                      try {
                        await api.setCommissionerStatus(leagueId, m.user_id, next);
                        setDetails((prev: any) => ({
                          ...prev,
                          members: (prev.members || []).map((x: any) => x.user_id === m.user_id ? { ...x, is_commissioner: next } : x)
                        }));
                        showToast(`Updated ${m.username} commissioner status`, { type: 'success' });
                      } catch (err: any) {
                        showToast(err?.message || 'Failed to update commissioner', { type: 'error' });
                      }
                    }}
                  />
                  <span>Co-commissioner</span>
                </label>
              </div>
            ))}
            <p className="text-xs text-gray-500">At least one commissioner must remain.</p>
          </div>
        </div>
      </div>
    </div>
  );
}


