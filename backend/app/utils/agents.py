from typing import Dict, Set, Optional
from sqlmodel import Session, select

# Fallback agent to class mapping (for backwards compatibility)
FALLBACK_AGENT_TO_CLASS: Dict[str, str] = {
    # Duelists
    "Jett": "Duelist",
    "Phoenix": "Duelist",
    "Neon": "Duelist",
    "Raze": "Duelist",
    "Reyna": "Duelist",
    "Yoru": "Duelist",
    "Iso": "Duelist",
    "Waylay": "Duelist",
    # Controllers
    "Astra": "Controller",
    "Brimstone": "Controller",
    "Omen": "Controller",
    "Viper": "Controller",
    "Harbor": "Controller",
    "Clove": "Controller",
    # Initiators
    "Breach": "Initiator",
    "Gekko": "Initiator",
    "KAY/O": "Initiator",
    "Skye": "Initiator",
    "Sova": "Initiator",
    "Fade": "Initiator",
    "Tejo": "Initiator",
    # Sentinels
    "Chamber": "Sentinel",
    "Cypher": "Sentinel",
    "Deadlock": "Sentinel",
    "Killjoy": "Sentinel",
    "Sage": "Sentinel",
    "Vyse": "Sentinel",
}

VALID_CLASSES: Set[str] = {"Duelist", "Controller", "Initiator", "Sentinel"}
VALID_PLAYER_ROLES: Set[str] = {"Duelist", "Controller", "Initiator", "Sentinel", "Flex"}

def get_agent_to_class_mapping(session: Optional[Session] = None) -> Dict[str, str]:
    """Get agent to class mapping, preferring database over fallback."""
    if session is None:
        return FALLBACK_AGENT_TO_CLASS.copy()
    
    try:
        from app.models.agent_model import Agent
        agents = session.exec(select(Agent).where(Agent.is_active == True)).all()
        
        if agents:
            # Use database agents
            agent_mapping = {agent.name: agent.agent_class for agent in agents}
            # Merge with fallback for any missing agents
            merged_mapping = FALLBACK_AGENT_TO_CLASS.copy()
            merged_mapping.update(agent_mapping)
            return merged_mapping
        else:
            # No agents in database, use fallback
            return FALLBACK_AGENT_TO_CLASS.copy()
    except Exception:
        # Database error, use fallback
        return FALLBACK_AGENT_TO_CLASS.copy()

def get_valid_agents(session: Optional[Session] = None) -> Set[str]:
    """Get set of valid agent names."""
    return set(get_agent_to_class_mapping(session).keys())

def get_agent_class(agent_name: str, session: Optional[Session] = None) -> Optional[str]:
    """Get the class for a specific agent."""
    mapping = get_agent_to_class_mapping(session)
    return mapping.get(agent_name)

# For backwards compatibility
AGENT_TO_CLASS = FALLBACK_AGENT_TO_CLASS
VALID_AGENTS = set(FALLBACK_AGENT_TO_CLASS.keys())


