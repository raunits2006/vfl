# Admin Panel Setup Guide

This guide explains how to set up and use the admin panel for the Valorant Fantasy League.

## 🚀 Quick Start

### 1. Database Migration

First, run the database migration to create the admin table:

```bash
cd backend
source venv/bin/activate  # or activate your virtual environment
alembic upgrade head
```

### 2. Create Initial Admin Account

Run the admin creation script to create your first admin account:

```bash
cd backend
python create_admin.py
```

Follow the prompts to create your super admin account.

### 3. Access Admin Panel

Once your admin account is created, you can access the admin panel at:

```
http://localhost:3000/admin/login
```

## 🔒 Security Features

### Multi-Layer Security
- **Separate Authentication**: Admin auth is completely separate from user auth
- **Enhanced Password Hashing**: Uses bcrypt with 14 rounds (vs 12 for regular users)
- **Unique JWT Secrets**: Admin tokens use a different secret key
- **Shorter Token Expiry**: Admin tokens expire in 30 minutes (vs 1440 for users)
- **Permission-Based Access**: Granular permissions for different admin functions

### Permission System
- `can_manage_players`: Add, edit, delete players and view player analytics
- `can_manage_users`: View and manage user accounts
- `can_manage_leagues`: View and manage league information
- `can_manage_matches`: Manage match data and results
- `can_view_analytics`: Access system analytics and reports
- `is_super_admin`: Bypass all permission checks and manage other admins

## 📊 Admin Features

### Overview Dashboard
- System statistics (total users, active users, leagues, players)
- Top performing players leaderboard
- Recent user registrations
- Key performance metrics

### Player Management
- **View All Players**: Complete player database with statistics
- **Search & Filter**: Find players by name, team, or role (including new Flex role)
- **Add New Players**: Create new player entries with 5 role options
- **Edit Player Info**: Update team, role (Duelist/Controller/Initiator/Sentinel/Flex), image URLs
- **Delete Players**: Remove players from the system
- **Performance Analytics**: View total points, average scores, match history

### Agent Management (NEW)
- **View All Agents**: Complete Valorant agent database with classifications
- **Search & Filter**: Find agents by name or class
- **Add New Agents**: Create entries for new Valorant agents
- **Edit Agent Info**: Update class, status, release date, images, descriptions
- **Import Defaults**: One-click import of all current Valorant agents
- **Agent Status**: Activate/deactivate agents for agent predictions

### User Management (Super Admin/User Permission)
- View all registered users
- User activity metrics (leagues joined, teams created)
- Account status tracking
- Registration analytics

### League Management (Super Admin/League Permission)
- View all leagues and their status
- League participation statistics
- Member and team counts
- League creation analytics

### Advanced Analytics
- **System Overview**: Comprehensive system health metrics
- **Player Performance**: Top performers by various metrics
- **Team Distribution**: Player distribution across teams
- **Activity Trends**: User registration and engagement patterns

## 🛠 API Endpoints

### Authentication
- `POST /api/admin/auth/init` - Create first admin (only if no admins exist)
- `POST /api/admin/auth/login` - Admin login
- `GET /api/admin/auth/me` - Get current admin info
- `POST /api/admin/auth/register` - Create new admin (super admin only)

### Player Management
- `GET /api/admin/players` - List all players with analytics
- `POST /api/admin/players` - Create new player (now supports Flex role)
- `PUT /api/admin/players/{player_name}` - Update player
- `DELETE /api/admin/players/{player_name}` - Delete player

### Agent Management
- `GET /api/admin/agents` - List all agents with filtering
- `POST /api/admin/agents` - Create new agent
- `PUT /api/admin/agents/{agent_id}` - Update agent
- `DELETE /api/admin/agents/{agent_id}` - Delete agent
- `POST /api/admin/agents/import-defaults` - Import default Valorant agents

### Analytics
- `GET /api/admin/analytics/system` - System-wide analytics
- `GET /api/admin/analytics/players/top` - Top performing players
- `GET /api/admin/analytics/teams` - Team distribution analytics

### User & League Management
- `GET /api/admin/users` - List all users (requires permission)
- `GET /api/admin/leagues` - List all leagues (requires permission)

## 🎯 Usage Examples

### Creating Players
The admin panel allows you to easily add new players to the system:

1. Navigate to the "Players" tab
2. Click "Add Player"
3. Fill in player details:
   - **Player Name**: Unique identifier (cannot be changed after creation)
   - **Team**: Current team affiliation
   - **Primary Role**: Duelist, Controller, Initiator, Sentinel, or **Flex** (NEW)
   - **Image URL**: Optional player image

### Managing Agents (NEW)
The agent management system allows you to maintain the Valorant agent database:

1. Navigate to the "Agents" tab
2. **Import Default Agents**: Click to automatically import all current Valorant agents
3. **Add New Agent**: Create entries for newly released agents
   - **Agent Name**: Unique agent name (e.g., "Deadlock")
   - **Agent Class**: Duelist, Controller, Initiator, or Sentinel
   - **Release Date**: Optional release information
   - **Image URL**: Agent portrait or icon
   - **Description**: Brief agent description
4. **Filter & Search**: Find agents by name or class
5. **Edit/Delete**: Update agent information or remove outdated agents

### Managing Existing Players
- **Search**: Use the search bar to find specific players
- **Filter by Team**: Filter players by their current team
- **Edit**: Click the edit icon to modify player information
- **Delete**: Remove players (with confirmation dialog)

### Viewing Analytics
The Overview tab provides key insights:
- **User Growth**: Track new registrations and active users
- **Player Performance**: See who the top fantasy performers are
- **System Health**: Monitor overall system usage

## 🔐 Admin Account Management

### Creating Additional Admins
Only super admins can create new admin accounts:

1. Log in as a super admin
2. Use the `/api/admin/auth/register` endpoint or future admin management UI
3. Set appropriate permissions for the new admin

### Permission Levels
- **Player Manager**: Can only manage players and view basic analytics
- **User Manager**: Can manage players and users
- **League Manager**: Can manage players, users, and leagues
- **Super Admin**: Full access to all features and can manage other admins

## 🚨 Security Best Practices

1. **Strong Passwords**: Use complex passwords for admin accounts
2. **Limited Access**: Only create admin accounts for trusted personnel
3. **Regular Audits**: Monitor admin activity and access logs
4. **Principle of Least Privilege**: Grant only necessary permissions
5. **Secure Environment**: Ensure admin access is only available over HTTPS in production

## 🔧 Troubleshooting

### Common Issues

**"Admin accounts already exist" when running create_admin.py**
- This means admin accounts are already set up
- Use the admin panel to create additional accounts

**Permission Denied Errors**
- Check if your admin account has the required permissions
- Contact a super admin to update your permissions

**Database Connection Issues**
- Ensure your database is running and accessible
- Check DATABASE_URL in your environment configuration

**Token Expiration**
- Admin tokens expire after 30 minutes for security
- Simply log in again to get a new token

## 📝 Notes

- Admin authentication is completely separate from user authentication
- Admin sessions are shorter (30 minutes) for enhanced security
- All admin actions should be logged (future enhancement)
- The admin panel is designed to be responsive and work on all devices
