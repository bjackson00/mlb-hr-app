import requests
import pandas as pd

def get_batter_stats(player_id):
    """Get career batting stats for a hitter"""
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=career&group=hitting&sportId=1"
    response = requests.get(url)
    data = response.json()
    
    for split in data.get("stats", []):
        for s in split.get("splits", []):
            stat = s.get("stat", {})
            ab = int(stat.get("atBats", 0))
            hr = int(stat.get("homeRuns", 0))
            if ab > 0:
                return {
                    "hr": hr,
                    "at_bats": ab,
                    "hr_per_ab": hr / ab,
                    "slg": float(stat.get("slugging", 0)),
                    "iso": float(stat.get("slugging", 0)) - float(stat.get("avg", 0))
                }
    return {"hr": 0, "at_bats": 0, "hr_per_ab": 0.0, "slg": 0.0, "iso": 0.0}

def get_pitcher_stats(player_id):
    """Get career pitching stats — specifically HR allowed"""
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=career&group=pitching&sportId=1"
    response = requests.get(url)
    data = response.json()
    
    for split in data.get("stats", []):
        for s in split.get("splits", []):
            stat = s.get("stat", {})
            ip = float(stat.get("inningsPitched", 0) or 0)
            hr = int(stat.get("homeRuns", 0))
            bf = int(stat.get("battersFaced", 0))
            if bf > 0:
                return {
                    "hr_allowed": hr,
                    "batters_faced": bf,
                    "hr_per_bf": hr / bf,
                    "innings_pitched": ip
                }
    return {"hr_allowed": 0, "batters_faced": 0, "hr_per_bf": 0.0, "innings_pitched": 0.0}

# League average HR/AB (roughly 2024 MLB average)
LEAGUE_AVG_HR_PER_AB = 0.034
LEAGUE_AVG_HR_PER_BF = 0.031

def calculate_hr_probability(batter_stats, pitcher_stats, park_factor=1.0):
    """
    Simple log5-inspired formula:
    Combines batter HR rate, pitcher HR allowed rate, and league average
    """
    b = batter_stats["hr_per_ab"]
    p = pitcher_stats["hr_per_bf"]
    l = LEAGUE_AVG_HR_PER_AB
    
    if l == 0:
        return 0.0
    
    # Log5 formula
    if (b + p - 2 * l) == 0:
        prob = l
    else:
        prob = (b * p) / (b + p - 2 * l + l) if (b + p - l) > 0 else l
    
    # Apply park factor
    prob *= park_factor
    
    return round(prob * 100, 2)  # Return as percentage

if __name__ == "__main__":
    from schedule import get_todays_games
    from rosters import get_rosters_for_games

    print("Fetching today's games...")
    games_df = get_todays_games()
    
    print("Fetching rosters...")
    rosters_df = get_rosters_for_games(games_df)
    
    print(f"Pulling stats for {len(rosters_df)} batters (this may take a minute)...\n")
    
    results = []
    for _, row in rosters_df.iterrows():
        batter_stats = get_batter_stats(row["player_id"])
        pitcher_stats = get_pitcher_stats(row["opposing_pitcher_id"]) if row["opposing_pitcher_id"] else {"hr_per_bf": LEAGUE_AVG_HR_PER_BF}
        
        hr_prob = calculate_hr_probability(batter_stats, pitcher_stats)
        
        results.append({
            "batter": row["player_name"],
            "team": row["team"],
            "opposing_pitcher": row["opposing_pitcher"],
            "venue": row["venue"],
            "batter_hr_per_ab": round(batter_stats["hr_per_ab"] * 100, 2),
            "pitcher_hr_per_bf": round(pitcher_stats.get("hr_per_bf", 0) * 100, 2),
            "hr_probability": hr_prob
        })
    
    df = pd.DataFrame(results).sort_values("hr_probability", ascending=False)
    print(df.head(25).to_string())