'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useParams, useRouter } from 'next/navigation';
import DraftPage from '../../../draft/page';
import { api } from '../../../../utils/api';
import { useAuth } from '../../../../contexts/AuthContext';

export default function LeagueDraftRoute() {
  const params = useParams<{ id: string }>();
  const leagueId = Number(params.id);
  const router = useRouter();
  const searchParams = useSearchParams();
  const draftIdFromQuery = searchParams.get('draftId');
  const [resolving, setResolving] = useState(() => !draftIdFromQuery && Number.isFinite(leagueId));
  const { user } = useAuth();

  useEffect(() => {
    if (draftIdFromQuery || !Number.isFinite(leagueId)) return;
    let active = true;
    setResolving(true);
    
    // First ensure user has a team, then fetch draft
    const ensureTeamAndFetchDraft = async () => {
      try {
        // Ensure user has a team for this league
        if (user) {
          try {
            await api.getUserTeamByLeague(leagueId, user.id);
          } catch {
            try {
              await api.createTeam(leagueId, user.id, `${user.username}'s Team`);
            } catch {}
          }
        }
        
        // Then fetch the draft
        const status = await api.getDraftByLeague(leagueId);
        if (!active) return;
        router.replace(`/leagues/${leagueId}/draft?draftId=${status.draft_id}`);
      } catch {
        // No draft yet; stay and let the page show empty state or user can start from league page
      } finally {
        setResolving(false);
      }
    };
    
    ensureTeamAndFetchDraft();
    
    return () => {
      active = false;
    };
  }, [draftIdFromQuery, leagueId, router, user]);

  if (!draftIdFromQuery && resolving) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-valorant-600"></div>
      </div>
    );
  }

  if (!draftIdFromQuery && !resolving) {
    return (
      <div className="card">
        <h2 className="text-xl font-bold mb-2">No draft found</h2>
        <p className="text-gray-600">This league has no active draft yet. Start the draft from the league page.</p>
      </div>
    );
  }

  return <DraftPage />;
}


