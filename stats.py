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
            games = int(stat.get("gamesPlayed", 0))
            if ab > 0:
                return {
                    "hr": hr,
                    "at_bats": ab,
                    "games_played": games,
                    "hr_per_ab": hr / ab,
                    "slg": float(stat.get("slugging", 0)),
                    "iso": float(stat.get("slugging", 0)) - float(stat.get("avg", 0))
                }
    return {"hr": 0, "at_bats": 0, "games_played": 0, "hr_per_ab": 0.0, "slg": 0.0, "iso": 0.0}

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

LEAGUE_AVG_HR_PER_AB = 0.034
LEAGUE_AVG_HR_PER_BF = 0.031

# A player is considered a "regular" if they average this many ABs per season
AVG_AB_PER_SEASON = 400

def get_confidence_tier(at_bats, games_played):
    """
    Classify a batter by how much we trust their sample size.
    Returns a tier label and a weight multiplier.
    
    - Bench/pinch hitters with low career ABs get filtered or penalized
    - Rookies with few ABs but decent games get a small boost vs true bench guys
    - Regulars with 1+ seasons of ABs are trusted fully
    """
    # Estimate seasons played (rough: 162 games/season, ~3.5 AB/game)
    estimated_seasons = games_played / 162 if games_played > 0 else 0

    # Full-time regular: 400+ ABs per season on average
    if at_bats >= max(400, estimated_seasons * 350):
        return "starter", 1.0

    # Young player / rookie with limited time but showing up regularly
    elif games_played >= 40 and at_bats >= 80:
        return "rookie/emerging", 0.85

    # Fringe player — some MLB time but clearly not a regular
    elif at_bats >= 50:
        return "fringe", 0.6

    # True bench/pinch hitter — very few ABs, not reliable
    else:
        return "bench", None  # None = filter out entirely

def calculate_hr_probability(batter_stats, pitcher_stats, park_factor=1.0):
    at_bats = batter_stats.get("at_bats", 0)
    games_played = batter_stats.get("games_played", 0)

    tier, weight = get_confidence_tier(at_bats, games_played) if get_confidence_tier(at_bats, games_played)[1] is not None else ("bench", None)
    
    # Unpack properly
    tier, weight = get_confidence_tier(at_bats, games_played)
    
    if weight is None:
        return None  # Signal to filter this player out

    b = batter_stats["hr_per_ab"]
    p = pitcher_stats.get("hr_per_bf", LEAGUE_AVG_HR_PER_BF)
    l = LEAGUE_AVG_HR_PER_AB

    # For low sample sizes, blend toward league average
    if at_bats < 200:
        blend = at_bats / 200
        b = (b * blend) + (l * (1 - blend))

    if l == 0:
        return 0.0

    prob = (b * p) / (b + p - 2 * l + l) if (b + p - l) > 0 else l
    prob *= park_factor
    prob *= weight  # Apply confidence penalty for non-starters

    return round(prob * 100, 2)

if __name__ == "__main__":
    from schedule import get_todays_games
    from rosters import get_rosters_for_games

    print("Fetching today's games...")
    games_df = get_todays_games()
    
    print("Fetching rosters...")
    rosters_df = get_rosters_for_games(games_df)
    
    print(f"Pulling stats for {len(rosters_df)} batters...\n")
    
    results = []
    skipped = 0
    for _, row in rosters_df.iterrows():
        batter_stats = get_batter_stats(row["player_id"])
        pitcher_stats = get_pitcher_stats(row["opposing_pitcher_id"]) if row["opposing_pitcher_id"] else {"hr_per_bf": LEAGUE_AVG_HR_PER_BF}
        
        hr_prob = calculate_hr_probability(batter_stats, pitcher_stats)
        
        if hr_prob is None:
            skipped += 1
            continue

        tier, _ = get_confidence_tier(batter_stats["at_bats"], batter_stats["games_played"])

        results.append({
            "batter": row["player_name"],
            "team": row["team"],
            "opposing_pitcher": row["opposing_pitcher"],
            "venue": row["venue"],
            "career_ab": batter_stats["at_bats"],
            "tier": tier,
            "batter_hr_per_ab": round(batter_stats["hr_per_ab"] * 100, 2),
            "pitcher_hr_per_bf": round(pitcher_stats.get("hr_per_bf", 0) * 100, 2),
            "hr_probability": hr_prob
        })
    
    df = pd.DataFrame(results).sort_values("hr_probability", ascending=False)
    print(f"Showing {len(df)} batters, filtered out {skipped} bench/pinch hitters\n")
    print(df.head(25).to_string())