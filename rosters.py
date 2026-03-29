import requests
import pandas as pd

def get_team_roster(team_id):
    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=active"
    response = requests.get(url)
    data = response.json()
    
    players = []
    for player in data.get("roster", []):
        # Only grab position players (not pitchers)
        position = player.get("position", {}).get("code", "")
        if position != "1":  # 1 = pitcher
            players.append({
                "player_id": player["person"]["id"],
                "player_name": player["person"]["fullName"],
                "position": player.get("position", {}).get("abbreviation", "")
            })
    
    return players

def get_team_id_from_name(team_name):
    url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    response = requests.get(url)
    data = response.json()
    
    for team in data.get("teams", []):
        if team["name"] == team_name:
            return team["id"]
    return None

def get_rosters_for_games(games_df):
    all_rosters = []
    
    for _, game in games_df.iterrows():
        for side in ["away", "home"]:
            team_name = game[f"{side}_team"]
            pitcher_name = game[f"{side}_pitcher"]  # They bat against the OPPOSING pitcher
            opposing_pitcher = game["home_pitcher"] if side == "away" else game["away_pitcher"]
            opposing_pitcher_id = game["home_pitcher_id"] if side == "away" else game["away_pitcher_id"]
            
            team_id = get_team_id_from_name(team_name)
            if not team_id:
                continue
                
            players = get_team_roster(team_id)
            for player in players:
                player["team"] = team_name
                player["opposing_pitcher"] = opposing_pitcher
                player["opposing_pitcher_id"] = opposing_pitcher_id
                player["venue"] = game["venue"]
                all_rosters.append(player)
    
    return pd.DataFrame(all_rosters)

if __name__ == "__main__":
    from schedule import get_todays_games
    
    games_df = get_todays_games()
    print(f"Found {len(games_df)} games today\n")
    
    rosters_df = get_rosters_for_games(games_df)
    print(f"Found {len(rosters_df)} batters across all games\n")
    print(rosters_df.head(20).to_string())