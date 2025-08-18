'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Plus, Users, Calendar, Play } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../utils/api';
import { League, DraftStatus } from '../../types/api';
import JoinLeagueModal from '../../components/JoinLeagueModal';
import CreateLeagueModal from '../../components/CreateLeagueModal';

export default function LeaguesPage() {
  const { user, loading: authLoading } = useAuth();
  const [leagues, setLeagues] = useState<League[]>([]);
  const [loading, setLoading] = useState(true);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [draftMap, setDraftMap] = useState<Record<number, DraftStatus | null>>({});

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLeagues([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    fetchLeagues();
  }, [user, authLoading]);

  const fetchLeagues = async () => {
    try {
      const data = user ? await api.getUserLeagues(user.id) : [];
      setLeagues(data);
      // Fetch draft status for each league in parallel
      if (user && data.length > 0) {
        const entries = await Promise.all(
          data.map(async (lg) => {
            try {
              const status = await api.getDraftByLeague(lg.id);
              return [lg.id, status] as const;
            } catch {
              return [lg.id, null] as const;
            }
          })
        );
        const map: Record<number, DraftStatus | null> = {};
        for (const [id, status] of entries) map[id] = status;
        setDraftMap(map);
      } else {
        setDraftMap({});
      }
    } catch (error) {
      console.error('Error fetching leagues:', error);
    } finally {
      setLoading(false);
    }
  };

  const joinByPin = async (pin: string) => {
    if (!user) {
      throw new Error('Please sign in to join a league');
    }
    await api.joinByPin(user.id, pin);
    await fetchLeagues();
  };

  const createLeague = async (data: { name: string; description?: string; max_teams: number }) => {
    const payload = user ? { ...data, creator_user_id: user.id } : data;
    await api.createLeague(payload);
    await fetchLeagues();
  };

  if (authLoading || loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-valorant-600"></div>
      </div>
    );
  }

  const renderActionForLeague = (league: League) => {
    const draft = draftMap[league.id];
    const hasStartedDraft = !!draft && draft.status !== 'COMPLETED';
    return (
      <div className="flex gap-2">
        {hasStartedDraft && (
          <Link href={`/leagues/${league.id}/draft`} className="btn-primary flex-1 flex items-center justify-center">
            <Play className="h-4 w-4 mr-2" /> Go To Draft
          </Link>
        )}
        <Link href={`/leagues/${league.id}`} className="btn-secondary flex-1 text-center">
          View Details
        </Link>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">My Leagues</h1>
        <div className="flex gap-2">
          <button onClick={() => setShowJoinModal(true)} className="btn-secondary flex items-center">
            <Users className="h-5 w-5 mr-2" />
            Join League
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary flex items-center">
            <Plus className="h-5 w-5 mr-2" />
            Create League
          </button>
        </div>
      </div>

      {leagues.length === 0 ? (
        <div className="text-center py-16">
          <Users className="h-24 w-24 text-gray-300 mx-auto mb-6" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">You are not in any leagues yet</h3>
          <p className="text-gray-600 mb-6">Create a league or join one using a 6-digit PIN from the commissioner</p>
          <div className="flex gap-3 justify-center">
            <button onClick={() => setShowJoinModal(true)} className="btn-secondary">Join with PIN</button>
            <button onClick={() => setShowCreateModal(true)} className="btn-primary">Create League</button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {leagues.map((league) => (
            <div key={league.id} className="team-card">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-xl font-semibold text-gray-900">{league.name}</h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  draftMap[league.id]?.status === 'IN_PROGRESS' 
                    ? 'bg-yellow-100 text-yellow-800'
                    : league.status === 'ACTIVE' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-800'
                }`}>
                  {draftMap[league.id]?.status === 'IN_PROGRESS' 
                    ? 'DRAFTING' 
                    : String(league.status).toUpperCase()
                  }
                </span>
              </div>
              <p className="text-gray-600 mb-4">{league.description}</p>
              <div className="space-y-2 mb-4">
                <div className="flex items-center text-sm text-gray-500">
                  <Users className="h-4 w-4 mr-2" />
                  {league.member_count || 0} / {league.max_teams} teams
                </div>
                <div className="flex items-center text-sm text-gray-500">
                  <Calendar className="h-4 w-4 mr-2" />
                  Created {new Date(league.created_at).toLocaleDateString()}
                </div>
              </div>
              {renderActionForLeague(league)}
            </div>
          ))}
        </div>
      )}

      <JoinLeagueModal
        isOpen={showJoinModal}
        onClose={() => setShowJoinModal(false)}
        onSubmit={joinByPin}
      />

      <CreateLeagueModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={createLeague}
      />
    </div>
  );
} 