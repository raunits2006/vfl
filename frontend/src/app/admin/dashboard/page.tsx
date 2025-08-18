'use client';

import { useEffect, useState } from 'react';
import { useToast } from '../../../components/ToastProvider';
import { useRouter } from 'next/navigation';
import { 
  Users, 
  Trophy, 
  UserCheck, 
  Activity, 
  Settings,
  LogOut,
  Shield,
  Plus,
  Edit,
  Trash2,
  Search,
  Filter,
  BarChart3,
  TrendingUp,
  Crown
} from 'lucide-react';
import { useAdminAuth } from '../../../contexts/AdminAuthContext';
import { 
  adminPlayerApi, 
  adminUserApi, 
  adminLeagueApi, 
  adminAnalyticsApi,
  adminAgentApi,
  PlayerResponse,
  UserAnalytics,
  LeagueAnalytics,
  SystemAnalytics,
  PlayerCreate,
  PlayerUpdate,
  AgentResponse,
  AgentCreate,
  AgentUpdate
} from '../../../utils/adminApi';

export default function AdminDashboard() {
  const router = useRouter();
  const { admin, logout, loading: authLoading } = useAdminAuth();
  const { showToast } = useToast();
  
  // State management
  const [activeTab, setActiveTab] = useState<'overview' | 'players' | 'agents' | 'users' | 'leagues'>('overview');
  const [players, setPlayers] = useState<PlayerResponse[]>([]);
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [users, setUsers] = useState<UserAnalytics[]>([]);
  const [leagues, setLeagues] = useState<LeagueAnalytics[]>([]);
  const [systemAnalytics, setSystemAnalytics] = useState<SystemAnalytics | null>(null);
  const [topPlayers, setTopPlayers] = useState<PlayerResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Player management state
  const [showPlayerModal, setShowPlayerModal] = useState(false);
  const [editingPlayer, setEditingPlayer] = useState<PlayerResponse | null>(null);
  const [playerSearch, setPlayerSearch] = useState('');
  const [playerTeamFilter, setPlayerTeamFilter] = useState('');
  
  // Agent management state
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<AgentResponse | null>(null);
  const [agentSearch, setAgentSearch] = useState('');
  const [agentClassFilter, setAgentClassFilter] = useState('');
  
  // Form state for player creation/editing
  const [playerForm, setPlayerForm] = useState<PlayerCreate>({
    player_name: '',
    team: '',
    primary_role: '',
    image_url: ''
  });

  // Form state for agent creation/editing
  const [agentForm, setAgentForm] = useState<AgentCreate>({
    name: '',
    agent_class: '',
    release_date: '',
    image_url: '',
    description: ''
  });

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !admin) {
      router.push('/admin/login');
    }
  }, [admin, authLoading, router]);

  // Load initial data
  useEffect(() => {
    if (admin) {
      loadData();
    }
  }, [admin, activeTab]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      switch (activeTab) {
        case 'overview':
          const [analytics, topPlayersData] = await Promise.all([
            adminAnalyticsApi.getSystemAnalytics(),
            adminPlayerApi.getTopPlayers(5, 'total_points')
          ]);
          setSystemAnalytics(analytics);
          setTopPlayers(topPlayersData);
          break;
          
        case 'players':
          const playersData = await adminPlayerApi.getAll(100, 0, playerTeamFilter || undefined);
          setPlayers(playersData);
          break;
          
        case 'agents':
          if (admin && (admin.can_manage_players || admin.is_super_admin)) {
            const agentsData = await adminAgentApi.getAll(100, 0, agentClassFilter || undefined);
            setAgents(agentsData);
          }
          break;
          
        case 'users':
          if (admin && (admin.can_manage_users || admin.is_super_admin)) {
            const usersData = await adminUserApi.getAll();
            setUsers(usersData);
          }
          break;
          
        case 'leagues':
          if (admin && (admin.can_manage_leagues || admin.is_super_admin)) {
            const leaguesData = await adminLeagueApi.getAll();
            setLeagues(leaguesData);
          }
          break;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handlePlayerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      if (editingPlayer) {
        await adminPlayerApi.update(editingPlayer.player_name, playerForm);
      } else {
        await adminPlayerApi.create(playerForm);
      }
      
      setShowPlayerModal(false);
      setEditingPlayer(null);
      setPlayerForm({ player_name: '', team: '', primary_role: '', image_url: '' });
      loadData(); // Reload players
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save player');
    }
  };

  const handlePlayerDelete = async (playerName: string) => {
    if (!confirm(`Are you sure you want to delete player "${playerName}"?`)) {
      return;
    }
    
    try {
      await adminPlayerApi.delete(playerName);
      loadData(); // Reload players
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete player');
    }
  };

  const openPlayerModal = (player?: PlayerResponse) => {
    if (player) {
      setEditingPlayer(player);
      setPlayerForm({
        player_name: player.player_name,
        team: player.team,
        primary_role: player.primary_role || '',
        image_url: player.image_url || ''
      });
    } else {
      setEditingPlayer(null);
      setPlayerForm({ player_name: '', team: '', primary_role: '', image_url: '' });
    }
    setShowPlayerModal(true);
  };

  const handleAgentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      if (editingAgent) {
        await adminAgentApi.update(editingAgent.id, agentForm);
      } else {
        await adminAgentApi.create(agentForm);
      }
      
      setShowAgentModal(false);
      setEditingAgent(null);
      setAgentForm({ name: '', agent_class: '', release_date: '', image_url: '', description: '' });
      loadData(); // Reload agents
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save agent');
    }
  };

  const handleAgentDelete = async (agentId: number) => {
    if (!confirm(`Are you sure you want to delete this agent?`)) {
      return;
    }
    
    try {
      await adminAgentApi.delete(agentId);
      loadData(); // Reload agents
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete agent');
    }
  };

  const openAgentModal = (agent?: AgentResponse) => {
    if (agent) {
      setEditingAgent(agent);
      setAgentForm({
        name: agent.name,
        agent_class: agent.agent_class,
        release_date: agent.release_date || '',
        image_url: agent.image_url || '',
        description: agent.description || ''
      });
    } else {
      setEditingAgent(null);
      setAgentForm({ name: '', agent_class: '', release_date: '', image_url: '', description: '' });
    }
    setShowAgentModal(true);
  };

  const handleImportDefaultAgents = async () => {
    try {
      const result = await adminAgentApi.importDefaults();
      setError(null);
      showToast(`Successfully imported ${result.imported_count} default agents`, { type: 'success' });
      loadData(); // Reload agents
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import default agents');
    }
  };

  const filteredPlayers = players.filter(player =>
    player.player_name.toLowerCase().includes(playerSearch.toLowerCase()) ||
    player.team.toLowerCase().includes(playerSearch.toLowerCase())
  );

  const filteredAgents = agents.filter(agent =>
    agent.name.toLowerCase().includes(agentSearch.toLowerCase()) ||
    agent.agent_class.toLowerCase().includes(agentSearch.toLowerCase())
  );

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
      </div>
    );
  }

  if (!admin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-red-600 mr-3" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
                <p className="text-sm text-gray-600">Welcome back, {admin.username}</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                {admin.is_super_admin && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 mr-2">
                    <Crown className="h-3 w-3 mr-1" />
                    Super Admin
                  </span>
                )}
                Last login: {admin.last_login ? new Date(admin.last_login).toLocaleDateString() : 'Never'}
              </div>
              <button
                onClick={logout}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
              >
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation */}
        <nav className="mb-8">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('overview')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'overview'
                    ? 'border-red-500 text-red-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <BarChart3 className="h-4 w-4 mr-2 inline" />
                Overview
              </button>
              
              {(admin.can_manage_players || admin.is_super_admin) && (
                <button
                  onClick={() => setActiveTab('players')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'players'
                      ? 'border-red-500 text-red-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Users className="h-4 w-4 mr-2 inline" />
                  Players
                </button>
              )}
              
              {(admin.can_manage_players || admin.is_super_admin) && (
                <button
                  onClick={() => setActiveTab('agents')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'agents'
                      ? 'border-red-500 text-red-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Settings className="h-4 w-4 mr-2 inline" />
                  Agents
                </button>
              )}
              
              {(admin.can_manage_users || admin.is_super_admin) && (
                <button
                  onClick={() => setActiveTab('users')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'users'
                      ? 'border-red-500 text-red-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <UserCheck className="h-4 w-4 mr-2 inline" />
                  Users
                </button>
              )}
              
              {(admin.can_manage_leagues || admin.is_super_admin) && (
                <button
                  onClick={() => setActiveTab('leagues')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'leagues'
                      ? 'border-red-500 text-red-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Trophy className="h-4 w-4 mr-2 inline" />
                  Leagues
                </button>
              )}
            </nav>
          </div>
        </nav>

        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
            {error}
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
          </div>
        ) : (
          <>
            {/* Overview Tab */}
            {activeTab === 'overview' && systemAnalytics && (
              <div className="space-y-6">
                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <Users className="h-8 w-8 text-blue-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-500">Total Users</p>
                        <p className="text-2xl font-semibold text-gray-900">{systemAnalytics.total_users}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <Activity className="h-8 w-8 text-green-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-500">Active Users (30d)</p>
                        <p className="text-2xl font-semibold text-gray-900">{systemAnalytics.active_users_last_30_days}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <Trophy className="h-8 w-8 text-yellow-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-500">Active Leagues</p>
                        <p className="text-2xl font-semibold text-gray-900">{systemAnalytics.active_leagues}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <TrendingUp className="h-8 w-8 text-purple-600" />
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-500">Total Players</p>
                        <p className="text-2xl font-semibold text-gray-900">{systemAnalytics.total_players}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Top Players */}
                <div className="bg-white rounded-lg shadow">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <h3 className="text-lg font-medium text-gray-900">Top Performing Players</h3>
                  </div>
                  <div className="p-6">
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Player
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Team
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Total Points
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Avg Points
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Matches
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {topPlayers.map((player, index) => (
                            <tr key={player.player_name}>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="flex items-center">
                                  <div className="flex-shrink-0 h-8 w-8">
                                    <div className="h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center">
                                      <span className="text-sm font-medium text-gray-700">#{index + 1}</span>
                                    </div>
                                  </div>
                                  <div className="ml-4">
                                    <div className="text-sm font-medium text-gray-900">{player.player_name}</div>
                                    <div className="text-sm text-gray-500">{player.primary_role}</div>
                                  </div>
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {player.team}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {player.total_points.toFixed(1)}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {player.average_points.toFixed(1)}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {player.total_matches}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                {/* Recent Registrations */}
                {systemAnalytics.recent_registrations.length > 0 && (
                  <div className="bg-white rounded-lg shadow">
                    <div className="px-6 py-4 border-b border-gray-200">
                      <h3 className="text-lg font-medium text-gray-900">Recent Registrations</h3>
                    </div>
                    <div className="p-6">
                      <div className="space-y-3">
                        {systemAnalytics.recent_registrations.map((registration, index) => (
                          <div key={index} className="flex items-center justify-between py-2">
                            <span className="text-sm font-medium text-gray-900">{registration.username}</span>
                            <span className="text-sm text-gray-500">
                              {new Date(registration.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Players Tab */}
            {activeTab === 'players' && (admin.can_manage_players || admin.is_super_admin) && (
              <div className="space-y-6">
                {/* Players Header */}
                <div className="flex justify-between items-center">
                  <h2 className="text-2xl font-bold text-gray-900">Player Management</h2>
                  <button
                    onClick={() => openPlayerModal()}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Player
                  </button>
                </div>

                {/* Search and Filters */}
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
                      <div className="relative">
                        <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                        <input
                          type="text"
                          value={playerSearch}
                          onChange={(e) => setPlayerSearch(e.target.value)}
                          placeholder="Search players..."
                          className="pl-10 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                        />
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Team Filter</label>
                      <select
                        value={playerTeamFilter}
                        onChange={(e) => setPlayerTeamFilter(e.target.value)}
                        className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                      >
                        <option value="">All Teams</option>
                        {Array.from(new Set(players.map(p => p.team))).sort().map(team => (
                          <option key={team} value={team}>{team}</option>
                        ))}
                      </select>
                    </div>
                    
                    <div className="flex items-end">
                      <button
                        onClick={loadData}
                        className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                      >
                        <Filter className="h-4 w-4 mr-2" />
                        Apply Filters
                      </button>
                    </div>
                  </div>
                </div>

                {/* Players Table */}
                <div className="bg-white rounded-lg shadow overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Player
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Team
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Role
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Performance
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {filteredPlayers.map((player) => (
                          <tr key={player.player_name}>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center">
                                <div className="flex-shrink-0 h-10 w-10">
                                  {player.image_url ? (
                                    <img className="h-10 w-10 rounded-full" src={player.image_url} alt={player.player_name} />
                                  ) : (
                                    <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                                      <span className="text-sm font-medium text-gray-700">
                                        {player.player_name.charAt(0).toUpperCase()}
                                      </span>
                                    </div>
                                  )}
                                </div>
                                <div className="ml-4">
                                  <div className="text-sm font-medium text-gray-900">{player.player_name}</div>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {player.team}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {player.primary_role || 'N/A'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-gray-900">
                                <div>{player.total_points.toFixed(1)} pts ({player.average_points.toFixed(1)} avg)</div>
                                <div className="text-gray-500">{player.total_matches} matches</div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                              <div className="flex space-x-2">
                                <button
                                  onClick={() => openPlayerModal(player)}
                                  className="text-red-600 hover:text-red-900"
                                >
                                  <Edit className="h-4 w-4" />
                                </button>
                                <button
                                  onClick={() => handlePlayerDelete(player.player_name)}
                                  className="text-red-600 hover:text-red-900"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Agents Tab */}
            {activeTab === 'agents' && (admin.can_manage_players || admin.is_super_admin) && (
              <div className="space-y-6">
                {/* Agents Header */}
                <div className="flex justify-between items-center">
                  <h2 className="text-2xl font-bold text-gray-900">Agent Management</h2>
                  <div className="flex space-x-3">
                    <button
                      onClick={handleImportDefaultAgents}
                      className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                    >
                      <TrendingUp className="h-4 w-4 mr-2" />
                      Import Defaults
                    </button>
                    <button
                      onClick={() => openAgentModal()}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add Agent
                    </button>
                  </div>
                </div>

                {/* Search and Filters */}
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
                      <div className="relative">
                        <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                        <input
                          type="text"
                          value={agentSearch}
                          onChange={(e) => setAgentSearch(e.target.value)}
                          placeholder="Search agents..."
                          className="pl-10 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                        />
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Class Filter</label>
                      <select
                        value={agentClassFilter}
                        onChange={(e) => setAgentClassFilter(e.target.value)}
                        className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                      >
                        <option value="">All Classes</option>
                        <option value="Duelist">Duelist</option>
                        <option value="Controller">Controller</option>
                        <option value="Initiator">Initiator</option>
                        <option value="Sentinel">Sentinel</option>
                      </select>
                    </div>
                    
                    <div className="flex items-end">
                      <button
                        onClick={loadData}
                        className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                      >
                        <Filter className="h-4 w-4 mr-2" />
                        Apply Filters
                      </button>
                    </div>
                  </div>
                </div>

                {/* Agents Table */}
                <div className="bg-white rounded-lg shadow overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Agent
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Class
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Release Date
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {filteredAgents.map((agent) => (
                          <tr key={agent.id}>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center">
                                <div className="flex-shrink-0 h-10 w-10">
                                  {agent.image_url ? (
                                    <img className="h-10 w-10 rounded-full" src={agent.image_url} alt={agent.name} />
                                  ) : (
                                    <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                                      <span className="text-sm font-medium text-gray-700">
                                        {agent.name.charAt(0).toUpperCase()}
                                      </span>
                                    </div>
                                  )}
                                </div>
                                <div className="ml-4">
                                  <div className="text-sm font-medium text-gray-900">{agent.name}</div>
                                  <div className="text-sm text-gray-500">{agent.description}</div>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                agent.agent_class === 'Duelist' ? 'bg-red-100 text-red-800' :
                                agent.agent_class === 'Controller' ? 'bg-blue-100 text-blue-800' :
                                agent.agent_class === 'Initiator' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-green-100 text-green-800'
                              }`}>
                                {agent.agent_class}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                agent.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                              }`}>
                                {agent.is_active ? 'Active' : 'Inactive'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {agent.release_date || 'N/A'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                              <div className="flex space-x-2">
                                <button
                                  onClick={() => openAgentModal(agent)}
                                  className="text-red-600 hover:text-red-900"
                                >
                                  <Edit className="h-4 w-4" />
                                </button>
                                <button
                                  onClick={() => handleAgentDelete(agent.id)}
                                  className="text-red-600 hover:text-red-900"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Users Tab */}
            {activeTab === 'users' && (admin.can_manage_users || admin.is_super_admin) && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-900">User Management</h2>
                
                <div className="bg-white rounded-lg shadow overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            User
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Email
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Activity
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Joined
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {users.map((user) => (
                          <tr key={user.id}>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-gray-900">{user.username}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {user.email}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                              }`}>
                                {user.is_active ? 'Active' : 'Inactive'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              <div>{user.leagues_count} leagues</div>
                              <div className="text-gray-500">{user.teams_count} teams</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {new Date(user.created_at).toLocaleDateString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Leagues Tab */}
            {activeTab === 'leagues' && (admin.can_manage_leagues || admin.is_super_admin) && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-900">League Management</h2>
                
                <div className="bg-white rounded-lg shadow overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            League
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Teams
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Members
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Created
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {leagues.map((league) => (
                          <tr key={league.id}>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-gray-900">{league.name}</div>
                              <div className="text-sm text-gray-500">{league.description}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                league.status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
                                league.status === 'DRAFTING' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {league.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {league.current_teams} / {league.max_teams}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {league.members_count}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {new Date(league.created_at).toLocaleDateString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Player Modal */}
      {showPlayerModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-bold text-gray-900 mb-4">
              {editingPlayer ? 'Edit Player' : 'Add New Player'}
            </h3>
            
            <form onSubmit={handlePlayerSubmit}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Player Name</label>
                  <input
                    type="text"
                    required
                    disabled={!!editingPlayer} // Can't change name when editing
                    value={playerForm.player_name}
                    onChange={(e) => setPlayerForm({...playerForm, player_name: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500 disabled:bg-gray-100"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Team</label>
                  <input
                    type="text"
                    required
                    value={playerForm.team}
                    onChange={(e) => setPlayerForm({...playerForm, team: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Primary Role</label>
                  <select
                    value={playerForm.primary_role}
                    onChange={(e) => setPlayerForm({...playerForm, primary_role: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                  >
                    <option value="">Select Role</option>
                    <option value="Duelist">Duelist</option>
                    <option value="Controller">Controller</option>
                    <option value="Initiator">Initiator</option>
                    <option value="Sentinel">Sentinel</option>
                    <option value="Flex">Flex</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Image URL</label>
                  <input
                    type="url"
                    value={playerForm.image_url}
                    onChange={(e) => setPlayerForm({...playerForm, image_url: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                  />
                </div>
              </div>
              
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowPlayerModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700"
                >
                  {editingPlayer ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Agent Modal */}
      {showAgentModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-bold text-gray-900 mb-4">
              {editingAgent ? 'Edit Agent' : 'Add New Agent'}
            </h3>
            
            <form onSubmit={handleAgentSubmit}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Agent Name</label>
                  <input
                    type="text"
                    required
                    disabled={!!editingAgent} // Can't change name when editing
                    value={agentForm.name}
                    onChange={(e) => setAgentForm({...agentForm, name: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500 disabled:bg-gray-100"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Agent Class</label>
                  <select
                    required
                    value={agentForm.agent_class}
                    onChange={(e) => setAgentForm({...agentForm, agent_class: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                  >
                    <option value="">Select Class</option>
                    <option value="Duelist">Duelist</option>
                    <option value="Controller">Controller</option>
                    <option value="Initiator">Initiator</option>
                    <option value="Sentinel">Sentinel</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Release Date</label>
                  <input
                    type="text"
                    placeholder="e.g., Episode 1 Act 1"
                    value={agentForm.release_date}
                    onChange={(e) => setAgentForm({...agentForm, release_date: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Image URL</label>
                  <input
                    type="url"
                    value={agentForm.image_url}
                    onChange={(e) => setAgentForm({...agentForm, image_url: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Description</label>
                  <textarea
                    rows={3}
                    value={agentForm.description}
                    onChange={(e) => setAgentForm({...agentForm, description: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                  />
                </div>
              </div>
              
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowAgentModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700"
                >
                  {editingAgent ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
