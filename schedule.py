import requests
import pandas as pd
from datetime import date

def get_todays_games():
    today = date.today().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,lineScore,team"
    
    response = requests.get(url)
    data = response.json()
    
    games = []
    
    for date_entry in data.get("dates", []):
        for game in date_entry.get("games", []):
            away_team = game["teams"]["away"]["team"]["name"]
            home_team = game["teams"]["home"]["team"]["name"]
            
            away_pitcher = game["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")
            home_pitcher = game["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")
            
            away_pitcher_id = game["teams"]["away"].get("probablePitcher", {}).get("id", None)
            home_pitcher_id = game["teams"]["home"].get("probablePitcher", {}).get("id", None)
            
            games.append({
                "away_team": away_team,
                "home_team": home_team,
                "away_pitcher": away_pitcher,
                "away_pitcher_id": away_pitcher_id,
                "home_pitcher": home_pitcher,
                "home_pitcher_id": home_pitcher_id,
                "venue": game.get("venue", {}).get("name", "Unknown"),
                "game_time": game.get("gameDate", "")
            })
    
    return pd.DataFrame(games)

if __name__ == "__main__":
    df = get_todays_games()
    print(df.to_string())