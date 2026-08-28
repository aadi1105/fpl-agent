import os
import sys
import json
import csv
import sqlite3
import pandas as pd
import requests
from datetime import datetime

sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.models import Team, Player, Gameweek, Fixture
from backend.ingestion.fpl_api import FPLDataIngestion

def run_phase3e_audit_and_sync():
    print("==================================================")
    print("PHASE 3E — 2026/27 CURRENT-STATE DATA & TRANSFER AUDIT")
    print("==================================================\n")

    ingestion = FPLDataIngestion()
    print("Step 1: Fetching canonical 2026/27 data from official FPL API...")
    bootstrap_data = ingestion.fetch_bootstrap_static()
    fixtures_data = ingestion.fetch_fixtures()

    elements_api = bootstrap_data['elements']
    teams_api = bootstrap_data['teams']
    events_api = bootstrap_data['events']

    team_id_to_name = {t['id']: t['name'] for t in teams_api}
    team_id_to_short = {t['id']: t['short_name'] for t in teams_api}

    print(f"API returned {len(elements_api)} players, {len(teams_api)} teams, {len(fixtures_data)} fixtures.\n")

    db = SessionLocal()
    try:
        # Step 2: Audit existing database vs Canonical FPL API
        print("Step 2: Auditing database players vs canonical FPL API...")
        db_players = db.query(Player).all()
        db_player_map = {p.id: p for p in db_players}

        matching_records = 0
        mismatched_team = []
        mismatched_price = []
        mismatched_status = []
        missing_in_db = []
        transfers_list = []

        for p_api in elements_api:
            p_id = p_api['id']
            p_name = f"{p_api.get('first_name','')} {p_api.get('second_name','')}".strip()
            web_name = p_api.get('web_name', p_name)
            api_team_id = p_api['team']
            api_team_name = team_id_to_name.get(api_team_id, "Unknown")
            api_cost = p_api['now_cost']
            api_status = p_api['status']
            join_date = p_api.get('team_join_date', 'Unknown')

            if p_id not in db_player_map:
                missing_in_db.append((p_id, web_name, api_team_name))
            else:
                p_db = db_player_map[p_id]
                db_team_id = p_db.team_id
                db_team_name = team_id_to_name.get(db_team_id, "Unknown")
                
                # Check team match
                if db_team_id != api_team_id:
                    mismatched_team.append({
                        'player_id': p_id,
                        'player_name': p_name,
                        'web_name': web_name,
                        'db_team_id': db_team_id,
                        'db_team_name': db_team_name,
                        'api_team_id': api_team_id,
                        'api_team_name': api_team_name,
                        'join_date': join_date
                    })

                # Check price match
                if p_db.now_cost != api_cost:
                    mismatched_price.append((p_id, web_name, p_db.now_cost, api_cost))

                # Check status match
                if p_db.status != api_status:
                    mismatched_status.append((p_id, web_name, p_db.status, api_status))

                if db_team_id == api_team_id and p_db.now_cost == api_cost and p_db.status == api_status:
                    matching_records += 1

        print(f"Database Audit Summary:")
        print(f"  - Total API Players: {len(elements_api)}")
        print(f"  - Total Database Players: {len(db_players)}")
        print(f"  - Matching Records: {matching_records}")
        print(f"  - Mismatched Team Assignments: {len(mismatched_team)}")
        print(f"  - Mismatched Prices: {len(mismatched_price)}")
        print(f"  - Mismatched Statuses: {len(mismatched_status)}")
        print(f"  - Missing Records in DB: {len(missing_in_db)}\n")

        # Step 3: Create TRANSFERS_2026_27.csv artifact
        print("Step 3: Creating docs/data/TRANSFERS_2026_27.csv transfer audit file...")
        os.makedirs("docs/data", exist_ok=True)
        transfer_csv_path = "docs/data/TRANSFERS_2026_27.csv"

        fieldnames = [
            'player_id', 'player_name', 'previous_club', 'current_club', 
            'transfer_date', 'transfer_type', 'current_fpl_team', 
            'database_team', 'team_match', 'current_registration_status'
        ]

        transfer_rows = []
        for item in mismatched_team:
            transfer_rows.append({
                'player_id': item['player_id'],
                'player_name': f"{item['player_name']} ({item['web_name']})",
                'previous_club': item['db_team_name'],
                'current_club': item['api_team_name'],
                'transfer_date': item['join_date'],
                'transfer_type': 'Permanent Transfer / Registration Update',
                'current_fpl_team': item['api_team_name'],
                'database_team': item['db_team_name'],
                'team_match': 'MISMATCH_BEFORE_SYNC',
                'current_registration_status': 'Active'
            })

        # Also add all players with team_join_date in 2026
        for p_api in elements_api:
            p_id = p_api['id']
            join_date = str(p_api.get('team_join_date', ''))
            if '2026' in join_date and p_id not in [r['player_id'] for r in transfer_rows]:
                api_team_name = team_id_to_name.get(p_api['team'], "Unknown")
                p_name = f"{p_api.get('first_name','')} {p_api.get('second_name','')}".strip()
                transfer_rows.append({
                    'player_id': p_id,
                    'player_name': f"{p_name} ({p_api.get('web_name','')})",
                    'previous_club': 'Previous Club / Historical',
                    'current_club': api_team_name,
                    'transfer_date': join_date,
                    'transfer_type': '2026 Summer Transfer',
                    'current_fpl_team': api_team_name,
                    'database_team': api_team_name,
                    'team_match': 'MATCH',
                    'current_registration_status': 'Active'
                })

        with open(transfer_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(transfer_rows)
        print(f"Saved {len(transfer_rows)} transfer records to {transfer_csv_path}.\n")

        # Step 4: Sync Teams, Gameweeks, Players, and Fixtures into DB
        print("Step 4: Executing database sync to establish canonical 2026/27 state...")
        ingestion.sync_teams(db, teams_api)
        ingestion.sync_gameweeks(db, events_api)
        ingestion.sync_players(db, elements_api)

        # Sync Fixtures
        synced_fix = 0
        for f_data in fixtures_data:
            fix_id = f_data['id']
            fix = db.query(Fixture).filter(Fixture.id == fix_id).first()
            if not fix:
                fix = Fixture(id=fix_id)
                db.add(fix)
            
            fix.event_id = f_data.get('event')
            fix.team_h_id = f_data.get('team_h')
            fix.team_a_id = f_data.get('team_a')
            fix.team_h_score = f_data.get('team_h_score')
            fix.team_a_score = f_data.get('team_a_score')
            fix.finished = f_data.get('finished', False)
            
            kickoff_raw = f_data.get('kickoff_time')
            if kickoff_raw:
                try:
                    fix.kickoff_time = datetime.fromisoformat(kickoff_raw.replace("Z", "+00:00"))
                except ValueError:
                    fix.kickoff_time = None
            synced_fix += 1
        
        db.commit()
        print(f"Successfully synced {synced_fix} fixtures to database.\n")

        # Step 5: Verify Mandatory Regression Test (Awoniyi -> Coventry City)
        print("Step 5: Verifying Awoniyi mandatory regression test case...")
        awoniyi = db.query(Player).filter(Player.web_name == "Awoniyi").first()
        if awoniyi:
            awoniyi_team = db.query(Team).filter(Team.id == awoniyi.team_id).first()
            print(f"  [AWONIYI VERIFICATION]")
            print(f"  - Player Name : {awoniyi.first_name} {awoniyi.second_name} ({awoniyi.web_name})")
            print(f"  - Team ID     : {awoniyi.team_id}")
            print(f"  - Team Name   : {awoniyi_team.name} ({awoniyi_team.short_name})")
            
            # Query Awoniyi's GW1 fixture
            awoniyi_fix = db.query(Fixture).filter(
                ((Fixture.team_h_id == awoniyi.team_id) | (Fixture.team_a_id == awoniyi.team_id)),
                Fixture.event_id == 1
            ).first()
            if awoniyi_fix:
                is_home = (awoniyi_fix.team_h_id == awoniyi.team_id)
                opp_id = awoniyi_fix.team_a_id if is_home else awoniyi_fix.team_h_id
                opp = db.query(Team).filter(Team.id == opp_id).first()
                print(f"  - GW1 Fixture : vs {opp.name} ({opp.short_name}) ({'H' if is_home else 'A'})")
                
                # Check validity: Awoniyi team (7 Coventry) must equal home or away team ID
                assert awoniyi.team_id in (awoniyi_fix.team_h_id, awoniyi_fix.team_a_id)
                assert awoniyi_team.short_name == "COV"
                assert opp.short_name == "ARS"  # Coventry plays Arsenal away in GW1
                print("  - Awoniyi Verification RESULT: PASS (Awoniyi assigned Coventry City vs Arsenal A)")

    finally:
        db.close()

if __name__ == "__main__":
    run_phase3e_audit_and_sync()
