import sqlite3
import pandas as pd

con = sqlite3.connect('fpl_engine.db')

print("=== TEAMS IN DATABASE ===")
df_teams = pd.read_sql("SELECT * FROM teams", con)
print(df_teams[['id', 'name', 'short_name']])

print("\n=== AWONIYI & REISS NELSON IN DATABASE ===")
df_players = pd.read_sql("SELECT p.id, p.web_name, p.first_name, p.second_name, p.team_id, t.name as team_name, p.now_cost, p.status FROM players p JOIN teams t ON p.team_id = t.id WHERE p.web_name LIKE '%Awoniyi%' OR p.web_name LIKE '%Nelson%' OR p.second_name LIKE '%Awoniyi%'", con)
print(df_players)

print("\n=== FIXTURES GW1 IN DATABASE ===")
df_fix = pd.read_sql("SELECT f.id, f.event_id, f.team_h_id, th.name as home_team, f.team_a_id, ta.name as away_team FROM fixtures f JOIN teams th ON f.team_h_id = th.id JOIN teams ta ON f.team_a_id = ta.id WHERE f.event_id = 1", con)
print(df_fix)
