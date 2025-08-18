from sqlalchemy import select, text
from sqlmodel import Session
from app.database import engine
from app.models.player_pool_model import Players  # Adjust import if needed

# List of players to add
players = [
    # 100 Thieves
    {"team": "100 Thieves", "player_name": "Asuna", "primary_role": "Duelist", "image_url": None},
    {"team": "100 Thieves", "player_name": "Kess", "primary_role": "Flex", "image_url": None},
    {"team": "100 Thieves", "player_name": "eeiu", "primary_role": "Initiator", "image_url": None},
    {"team": "100 Thieves", "player_name": "Cryocells", "primary_role": "Duelist", "image_url": None},
    {"team": "100 Thieves", "player_name": "zander", "primary_role": "Initiator", "image_url": None},

    # Cloud9
    {"team": "Cloud9", "player_name": "mitch", "primary_role": "Initiator", "image_url": None},
    {"team": "Cloud9", "player_name": "neT",   "primary_role": "Controller", "image_url": None},
    {"team": "Cloud9", "player_name": "Xeppaa","primary_role": "Sentinel", "image_url": None},
    {"team": "Cloud9", "player_name": "v1c",   "primary_role": "Controller", "image_url": None},
    {"team": "Cloud9", "player_name": "OXY",   "primary_role": "Duelist", "image_url": None},

    # Evil Geniuses
    {"team": "Evil Geniuses", "player_name": "supamen", "primary_role": "Controller", "image_url": None},
    {"team": "Evil Geniuses", "player_name": "yay",     "primary_role": "Duelist", "image_url": None},
    {"team": "Evil Geniuses", "player_name": "Derrek",  "primary_role": "Initiator", "image_url": None},
    {"team": "Evil Geniuses", "player_name": "NaturE",  "primary_role": "Initiator", "image_url": None},
    {"team": "Evil Geniuses", "player_name": "icy",     "primary_role": "Flex", "image_url": None},

    # FURIA
    {"team": "FURIA", "player_name": "tuyz",   "primary_role": "Controller", "image_url": None},
    {"team": "FURIA", "player_name": "Urango", "primary_role": "Flex", "image_url": None},
    {"team": "FURIA", "player_name": "heat",   "primary_role": "Flex", "image_url": None},
    {"team": "FURIA", "player_name": "Palla",   "primary_role": "Duelist", "image_url": None},
    {"team": "FURIA", "player_name": "adverso", "primary_role": "Initiator", "image_url": None},

    # KRÜ Esports
    {"team": "KRÜ Esports", "player_name": "Melser",  "primary_role": "Flex", "image_url": None},
    {"team": "KRÜ Esports", "player_name": "keznit",  "primary_role": "Flex", "image_url": None},
    {"team": "KRÜ Esports", "player_name": "Mazino",  "primary_role": "Flex", "image_url": None},
    {"team": "KRÜ Esports", "player_name": "Shyy",    "primary_role": "Sentinel", "image_url": None},
    {"team": "KRÜ Esports", "player_name": "Dantedeu5",    "primary_role": "Duelist", "image_url": None},

    # LEVIATÁN
    {"team": "LEVIATÁN", "player_name": "C0M",     "primary_role": "Initiator", "image_url": None},
    {"team": "LEVIATÁN", "player_name": "tex",     "primary_role": "Sentinel", "image_url": None},
    {"team": "LEVIATÁN", "player_name": "Okeanos", "primary_role": "Flex", "image_url": None},
    {"team": "LEVIATÁN", "player_name": "kiNgg",   "primary_role": "Controller", "image_url": None},
    {"team": "LEVIATÁN", "player_name": "Sato",    "primary_role": "Duelist", "image_url": None},

    # LOUD
    {"team": "LOUD", "player_name": "pANcada",   "primary_role": "Controller", "image_url": None},
    {"team": "LOUD", "player_name": "Virtyy",    "primary_role": "Duelist", "image_url": None},
    {"team": "LOUD", "player_name": "RobbieBk",  "primary_role": "Initiator", "image_url": None},
    {"team": "LOUD", "player_name": "cauanzin",  "primary_role": "Flex", "image_url": None},
    {"team": "LOUD", "player_name": "lukxo",  "primary_role": "Flex", "image_url": None},


    # MIBR
    {"team": "MIBR", "player_name": "cortezia", "primary_role": "Sentinel", "image_url": None},
    {"team": "MIBR", "player_name": "artzin",   "primary_role": "Duelist", "image_url": None},
    {"team": "MIBR", "player_name": "aspas",    "primary_role": "Duelist", "image_url": None},
    {"team": "MIBR", "player_name": "xenom",    "primary_role": "Controller", "image_url": None},
    {"team": "MIBR", "player_name": "Verno",    "primary_role": "Initiator", "image_url": None},

    # NRG
    {"team": "NRG", "player_name": "brawk", "primary_role": "Initiator", "image_url": None},
    {"team": "NRG", "player_name": "s0m",   "primary_role": "Controller", "image_url": None},
    {"team": "NRG", "player_name": "mada",  "primary_role": "Duelist", "image_url": None},
    {"team": "NRG", "player_name": "skuba", "primary_role": "Flex", "image_url": None},
    {"team": "NRG", "player_name": "Ethan", "primary_role": "Flex", "image_url": None},

    # Sentinels
    {"team": "Sentinels", "player_name": "Zellsis",  "primary_role": "Sentinel", "image_url": None},
    {"team": "Sentinels", "player_name": "johnqt",   "primary_role": "Flex", "image_url": None},
    {"team": "Sentinels", "player_name": "bang",     "primary_role": "Controller", "image_url": None},
    {"team": "Sentinels", "player_name": "zekken",   "primary_role": "Duelist", "image_url": None},
    {"team": "Sentinels", "player_name": "N4RRATE",  "primary_role": "Initiator", "image_url": None},

    # G2 Esports
    {"team": "G2 Esports", "player_name": "valyn",    "primary_role": "Controller", "image_url": None},
    {"team": "G2 Esports", "player_name": "jawgemo",  "primary_role": "Duelist", "image_url": None},
    {"team": "G2 Esports", "player_name": "JonahP",   "primary_role": "Flex", "image_url": None},
    {"team": "G2 Esports", "player_name": "BABYBAY",     "primary_role": "Sentinel", "image_url": None},
    {"team": "G2 Esports", "player_name": "trent",    "primary_role": "Initiator", "image_url": None},

    # 2Game Esports
    {"team": "2Game Esports", "player_name": "lz",       "primary_role": "Controller", "image_url": None},
    {"team": "2Game Esports", "player_name": "silentzz","primary_role": "Duelist", "image_url": None},
    {"team": "2Game Esports", "player_name": "gobera",   "primary_role": "Sentinel", "image_url": None},
    {"team": "2Game Esports", "player_name": "spike",    "primary_role": "Flex", "image_url": None},
    {"team": "2Game Esports", "player_name": "pryze",    "primary_role": "Initiator", "image_url": None}
]

# def add_players():
#     with Session(engine) as session:
#         current_players = set(p["player_name"] for p in players)
#         session.exec(
#             text("DELETE FROM players WHERE player_name IN :player_names"),
#             {"player_names": tuple(current_players)}
#         )
#         session.commit()
#         for p in players:
#             player = Players(**p)
#             if not session.exec(select(Players).where(Players.player_name == player.player_name)).first():
#                 session.add(player)
#         session.commit()
#     print(f"Added {len(players)} players to the database.")

def add_players():
    with Session(engine) as session:
        current_players = set(p["player_name"] for p in players)
        # Remove all players not in the current list
        if current_players:
            session.exec(
                text("DELETE FROM players WHERE player_name NOT IN :player_names").bindparams(player_names=tuple(current_players))
            )
        else:
            session.exec(text("DELETE FROM players"))
        session.commit()
        for p in players:
            player = Players(**p)
            if not session.exec(select(Players).where(Players.player_name == player.player_name)).first():
                session.add(player)
        session.commit()
    print(f"Added {len(players)} players to the database.")


# def remove_duplicate_players():
#     with Session(engine) as session:
#         # Find all player_names with more than one entry
#         result = session.exec(
#             text("SELECT player_name FROM players GROUP BY player_name HAVING COUNT(*) > 1")
#         )
#         duplicates = [row[0] for row in result.fetchall()]
#         for name in duplicates:
#             players = session.exec(
#                 select(Players).where(Players.player_name == name).order_by(Players.id)
#             ).all()
#             # Keep the first, delete the rest
#             for player in players[1:]:
#                 session.delete(player)
#         session.commit()
#     print("Removed duplicate players.")

if __name__ == "__main__":
    # remove_duplicate_players()
    add_players()




# if __name__ == "__main__":
#     add_players()