'use client';

import { useEffect, useMemo, useState } from 'react';
import { api } from '../../utils/api';
import { LiveMatch, MatchStatus } from '../../types/api';

export default function MatchesPage() {
  const [live, setLive] = useState<LiveMatch[]>([]);
  const [all, setAll] = useState<MatchStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const [liveMatches, allMatches] = await Promise.all([
          api.getLiveMatches(),
          api.getMatchesWithStatus(),
        ]);
        if (!active) return;
        setLive(liveMatches);
        setAll(allMatches);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const upcoming = useMemo(() => all.filter(m => m.status === 'upcoming'), [all]);
  const completed = useMemo(() => all.filter(m => m.status === 'completed'), [all]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-valorant-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="card">
        <h2 className="text-2xl font-bold mb-4">Live Matches</h2>
        {live.length === 0 ? (
          <p className="text-gray-600">No live matches right now.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {live.map(m => (
              <div key={m.match_id} className="p-4 rounded-lg bg-valorant-700">
                <div className="flex items-center justify-between">
                  <div className="font-semibold">{m.team1} vs {m.team2}</div>
                  <div className="text-sm text-gray-300">{m.current_map}</div>
                </div>
                <div className="mt-1 text-xl font-bold">{m.team1_score} - {m.team2_score}</div>
                <div className="mt-2 text-sm text-gray-400">Top players by score:</div>
                <ul className="mt-1 text-sm text-gray-300 list-disc pl-5">
                  {m.live_player_scores.slice(0, 5).map((p, idx) => (
                    <li key={idx}>{p.player_name} ({p.map_name}) - {p.score}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="text-2xl font-bold mb-4">Upcoming Matches</h2>
        {upcoming.length === 0 ? (
          <p className="text-gray-600">No upcoming matches in the next 24 hours.</p>
        ) : (
          <ul className="divide-y divide-gray-800/50">
            {upcoming.map(m => (
              <li key={m.match_id} className="py-3 flex items-center justify-between">
                <div>
                  <div className="font-medium">{m.team1} vs {m.team2}</div>
                  <div className="text-sm text-gray-500">{m.match_event}</div>
                </div>
                <div className="text-sm text-gray-400">
                  {new Date(m.scheduled_time * 1000).toLocaleString()}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2 className="text-2xl font-bold mb-4">Recently Completed</h2>
        {completed.length === 0 ? (
          <p className="text-gray-600">No recent completed matches.</p>
        ) : (
          <ul className="divide-y divide-gray-800/50">
            {completed.slice(0, 10).map(m => (
              <li key={m.match_id} className="py-3 flex items-center justify-between">
                <div>
                  <div className="font-medium">{m.team1} vs {m.team2}</div>
                  <div className="text-sm text-gray-500">{m.match_event}</div>
                </div>
                <div className="text-sm text-gray-400">
                  {new Date(m.scheduled_time * 1000).toLocaleString()}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}


