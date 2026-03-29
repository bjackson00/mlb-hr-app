import streamlit as st
import pandas as pd
from schedule import get_todays_games
from rosters import get_rosters_for_games
from stats import get_batter_stats, get_pitcher_stats, calculate_hr_probability, LEAGUE_AVG_HR_PER_BF
from datetime import date

st.set_page_config(
    page_title="MLB HR Predictor",
    page_icon="⚾",
    layout="wide"
)

st.title("⚾ MLB Home Run Predictor")
st.subheader(f"Today's matchups — {date.today().strftime('%B %d, %Y')}")

@st.cache_data(ttl=3600)
def load_all_data():
    status = st.status("Loading today's data...", expanded=True)

    with status:
        st.write("📅 Fetching today's schedule...")
        games_df = get_todays_games()

        if games_df.empty:
            status.update(label="No games found today.", state="error")
            return pd.DataFrame()

        st.write(f"✅ Found {len(games_df)} games!")

        st.write("👥 Fetching team rosters...")
        rosters_df = get_rosters_for_games(games_df)
        st.write(f"✅ Found {len(rosters_df)} batters across all teams!")

        st.write(f"📊 Pulling stats for {len(rosters_df)} batters — this takes 1-2 minutes...")

        results = []
        progress = st.progress(0)

        for i, (_, row) in enumerate(rosters_df.iterrows()):
            batter_stats = get_batter_stats(row["player_id"])
            pitcher_stats = get_pitcher_stats(row["opposing_pitcher_id"]) if row["opposing_pitcher_id"] else {"hr_per_bf": LEAGUE_AVG_HR_PER_BF}
            hr_prob = calculate_hr_probability(batter_stats, pitcher_stats)

            results.append({
                "Batter": row["player_name"],
                "Team": row["team"],
                "Opposing Pitcher": row["opposing_pitcher"],
                "Venue": row["venue"],
                "Batter HR% (career)": round(batter_stats["hr_per_ab"] * 100, 2),
                "Pitcher HR Allowed%": round(pitcher_stats.get("hr_per_bf", 0) * 100, 2),
                "HR Probability": hr_prob
            })

            progress.progress((i + 1) / len(rosters_df))

        status.update(label="✅ Data loaded!", state="complete")

    return pd.DataFrame(results).sort_values("HR Probability", ascending=False)

df = load_all_data()

if df.empty:
    st.warning("No games found for today. Check back later!")
else:
    st.sidebar.header("🔍 Filters")
    teams = ["All Teams"] + sorted(df["Team"].unique().tolist())
    selected_team = st.sidebar.selectbox("Filter by Team", teams)

    venues = ["All Venues"] + sorted(df["Venue"].unique().tolist())
    selected_venue = st.sidebar.selectbox("Filter by Venue", venues)

    min_prob = st.sidebar.slider("Min HR Probability (%)", 0.0, 10.0, 0.0, 0.1)

    filtered_df = df.copy()
    if selected_team != "All Teams":
        filtered_df = filtered_df[filtered_df["Team"] == selected_team]
    if selected_venue != "All Venues":
        filtered_df = filtered_df[filtered_df["Venue"] == selected_venue]
    filtered_df = filtered_df[filtered_df["HR Probability"] >= min_prob]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Batters", len(filtered_df))
    col2.metric("Games Today", df["Venue"].nunique())
    col3.metric("Top HR Probability", f"{filtered_df['HR Probability'].max():.2f}%")

    st.divider()

    st.subheader("🔥 Top 10 Most Likely to Homer Today")
    top10 = filtered_df.head(10).reset_index(drop=True)
    top10.index += 1
    st.dataframe(top10, use_container_width=True)

    st.divider()

    st.subheader("📋 All Batters")
    full = filtered_df.reset_index(drop=True)
    full.index += 1
    st.dataframe(full, use_container_width=True)

    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv,
        file_name=f"mlb_hr_predictions_{date.today()}.csv",
        mime="text/csv"
    )