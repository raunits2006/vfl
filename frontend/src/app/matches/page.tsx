'use client';

import { useEffect, useMemo, useState } from 'react';
import { api } from '../../utils/api';
import { LiveMatch, MatchStatus } from '../../types/api';

/**
 * Formats a time difference in seconds to a human-readable string.
 * Examples: "2d 5h", "3h 45m", "25m", "Live now"
 */
function formatTimeRemaining(seconds: number): string {
  if (seconds <= 0) {
    return 'Live now';
  }

  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) {
    return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
  }
  if (hours > 0) {
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  }
  return `${minutes}m`;
}

export default function MatchesPage() {
  const [live, setLive] = useState<LiveMatch[]>([]);
  const [all, setAll] = useState<MatchStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(() => Math.floor(Date.now() / 1000));

  // Update current time every minute for countdown display
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(Math.floor(Date.now() / 1000));
    }, 60000); // Update every minute
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let active = true;
    let isInitialLoad = true;

    async function load() {
      // Only show loading spinner on initial load, not on subsequent polls
      if (isInitialLoad) setLoading(true);

      try {
        const [liveMatches, allMatches] = await Promise.all([
          api.getLiveMatches(),
          api.getMatchesWithStatus(),
        ]);
        if (!active) return;
        setLive(liveMatches);
        setAll(allMatches);
      } catch {
        // Backend unreachable — keep empty states, no crash
      } finally {
        if (active) {
          setLoading(false);
          isInitialLoad = false;
        }
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
          <p className="text-gray-600">No upcoming VCT matches scheduled.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcoming.map(m => {
              const timeRemaining = m.scheduled_time - currentTime;
              return (
                <a
                  key={m.match_id}
                  href={m.match_page}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-4 rounded-lg bg-gradient-to-br from-valorant-800 to-valorant-900 border border-valorant-600/30 hover:border-valorant-500 hover:shadow-lg hover:shadow-valorant-600/20 transition-all duration-200 cursor-pointer group"
                >
                  {/* Time remaining badge in top-right */}
                  <div className="flex justify-between items-start mb-3">
                    <div className="text-xs text-gray-400 uppercase tracking-wide">
                      {m.match_event}
                    </div>
                    <div className="px-2 py-1 rounded-md bg-valorant-600 text-white text-sm font-semibold">
                      {formatTimeRemaining(timeRemaining)}
                    </div>
                  </div>

                  {/* Teams */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-lg group-hover:text-valorant-400 transition-colors">
                        {m.team1}
                      </span>
                    </div>
                    <div className="text-center text-gray-500 text-sm">vs</div>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-lg group-hover:text-valorant-400 transition-colors">
                        {m.team2}
                      </span>
                    </div>
                  </div>

                  {/* Scheduled time */}
                  <div className="mt-4 pt-3 border-t border-valorant-700/50 text-xs text-gray-500">
                    {new Date(m.scheduled_time * 1000).toLocaleString(undefined, {
                      weekday: 'short',
                      month: 'short',
                      day: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit',
                    })}
                  </div>
                </a>
              );
            })}
          </div>
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
