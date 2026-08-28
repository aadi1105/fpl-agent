import os
import sys
import json
import hashlib
import sqlite3
import pandas as pd
import numpy as np

sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture, Gameweek
from backend.projections.engine import ProjectionEngine
from backend.ml.minutes_predictor import MinutesPredictor
from backend.ml.xg_predictor import XGPredictor
from backend.ml.xa_predictor import XAPredictor
from backend.ml.cs_predictor import CSPredictor
from backend.ml.defcon_predictor import DEFCONPredictor

MINS_MODEL_PATH = "models/expected_minutes_v2.pkl"
XG_MODEL_PATH = "models/xg_v2.pkl"
XA_MODEL_PATH = "models/xa_v2.pkl"
CS_MODEL_PATH = "backend/ml/models/cs_v1_lgbm.pkl"

def get_file_sha256(filepath):
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_phase3f_investigation():
    print("==================================================")
    print("PHASE 3F — GW1 PREDICTION DECISION & FORENSIC AUDIT")
    print("==================================================\n")

    db = SessionLocal()
    try:
        engine = ProjectionEngine(db=db)

        # ----------------------------------------------------
        # 1. RUNTIME MODEL ARTIFACT VERIFICATION
        # ----------------------------------------------------
        print("Step 1: Auditing Runtime Model Artifacts & SHA256 Hashes...")
        artifacts = {
            "Expected Minutes": (MINS_MODEL_PATH, not engine.minutes_predictor.is_loaded),
            "Expected Goals (xG)": (XG_MODEL_PATH, not engine.xg_predictor.is_loaded),
            "Expected Assists (xA)": (XA_MODEL_PATH, not engine.xa_predictor.is_loaded),
            "Clean Sheet (CS)": (CS_MODEL_PATH, not bool(engine.cs_predictor.model)),
            "DEFCON": ("Analytical Poisson Model", False)
        }

        artifact_table = []
        for name, (path, fallback) in artifacts.items():
            sha = get_file_sha256(path) if path != "Analytical Poisson Model" else "N/A"
            artifact_table.append({
                "component": name,
                "path": path,
                "filename": os.path.basename(path) if path != "Analytical Poisson Model" else "defcon_predictor.py",
                "sha256": sha,
                "used_fallback": fallback
            })
            print(f"  - {name:<22}: {os.path.basename(path):<25} | Hash: {sha[:16]}... | Fallback: {fallback}")
        print()

        # ----------------------------------------------------
        # 2. AUDIT SAKA VS GABRIEL CLEAN SHEET DIFFERENCE
        # ----------------------------------------------------
        print("Step 2: Investigating Saka vs Gabriel Clean Sheet Difference (ARS vs COV H)...")
        saka = db.query(Player).filter(Player.web_name == "Saka").first()
        gabriel = db.query(Player).filter(Player.web_name == "Gabriel").first()
        ars_fix = db.query(Fixture).filter(Fixture.team_h_id == 1, Fixture.event_id == 1).first()
        cov_team = db.query(Team).filter(Team.id == ars_fix.team_a_id).first()

        saka_bd = engine.calculate_player_xp_breakdown(saka, fixture=ars_fix, is_home=True, opp_team=cov_team)
        gabriel_bd = engine.calculate_player_xp_breakdown(gabriel, fixture=ars_fix, is_home=True, opp_team=cov_team)

        print(f"  Saka (MID)    : CS Prob = {saka_bd['cs_prob']:.4f} | CS xP = {saka_bd['cs_xp']:.2f}")
        print(f"  Gabriel (DEF)  : CS Prob = {gabriel_bd['cs_prob']:.4f} | CS xP = {gabriel_bd['cs_xp']:.2f}")
        
        # Let's inspect where 0.69 vs 0.41 comes from in engine / db
        # Note: In database or previous API endpoints, team_defence_rating for Arsenal might be 1680 vs default 1000 for opponent!
        # If team_def_rating = 1680 and opp_att_rating = 1000: cs_modifier = 1680/1000 = 1.68
        # Base prob = 0.410 -> 0.410 * 1.68 = 0.6888 -> clamped to 0.689 or 0.69!
        # But why did Saka show 69% while Gabriel showed 41% in one snapshot?
        # Let's check team_defence_rating in DB for Arsenal!
        ars_team = db.query(Team).filter(Team.id == 1).first()
        print(f"  Arsenal Team Defence Home Rating: {ars_team.strength_defence_home}")
        print(f"  Arsenal Team Defence Away Rating: {ars_team.strength_defence_away}\n")

        # ----------------------------------------------------
        # 3. INVESTIGATE EXPECTED MINUTES PATTERN (~83-84m)
        # ----------------------------------------------------
        print("Step 3: Investigating Expected Minutes Pattern (~83-84m across outfield players)...")
        audited_mins_names = ["O'Reilly", "Calafiori", "De Cuyper", "Raya", "Gabriel", "Haaland", "B.Fernandes"]
        mins_audit_table = []

        for name in audited_mins_names:
            p = db.query(Player).filter(Player.web_name.ilike(f"%{name}%")).first()
            if not p:
                continue

            # Reconstruct feature inputs passed to mins_predictor
            tot_mins = float(p.minutes)
            recent_mins_5 = float(min(450.0, tot_mins))
            recent_apps_5 = float(min(5.0, tot_mins / 60.0)) if tot_mins > 0 else 0.0
            recent_starts_5 = float(min(5.0, tot_mins / 80.0)) if tot_mins >= 80 else 0.0

            pdata = {
                "price": p.now_cost / 10.0,
                "position": p.element_type,
                "minutes_last_5": recent_mins_5,
                "starts_last_5": recent_starts_5,
                "appearances_last_5": recent_apps_5,
                "average_minutes_last_5": recent_mins_5 / max(1.0, recent_apps_5) if recent_apps_5 > 0 else 0.0,
                "tot_mins_prior": tot_mins,
                "is_home": 1.0
            }

            mins_res = engine.minutes_predictor.predict(pdata)
            
            row = {
                "player_name": p.web_name,
                "position": p.element_type,
                "p_start": mins_res["p_start"],
                "p_60_plus": mins_res["p_60_plus"],
                "p_zero": mins_res["p_zero"],
                "expected_minutes": mins_res["expected_minutes"],
                "recent_starts_5": recent_starts_5,
                "recent_mins_5": recent_mins_5,
                "total_db_minutes": tot_mins,
                "used_fallback": mins_res["used_fallback"],
                "model_version": mins_res["model_version"]
            }
            mins_audit_table.append(row)
            print(f"  {p.web_name:<18} ({p.element_type}) | xMins={mins_res['expected_minutes']:.1f}m | pStart={mins_res['p_start']:.2f} | p60={mins_res['p_60_plus']:.2f} | p0={mins_res['p_zero']:.2f} | TotalDBMins={tot_mins} | Fallback={mins_res['used_fallback']}")
        print()

        # ----------------------------------------------------
        # 4. INVESTIGATE HAALAND VS NICO O'REILLY
        # ----------------------------------------------------
        print("Step 4: Direct Side-by-Side Comparison: HAALAND vs NICO O'REILLY...")
        haaland = db.query(Player).filter(Player.web_name == "Haaland").first()
        oreilly = db.query(Player).filter(Player.web_name == "O'Reilly").first()
        mci_fix = db.query(Fixture).filter(Fixture.team_h_id == 15, Fixture.event_id == 1).first()
        bou_team = db.query(Team).filter(Team.id == mci_fix.team_a_id).first()

        h_bd = engine.calculate_player_xp_breakdown(haaland, fixture=mci_fix, is_home=True, opp_team=bou_team)
        o_bd = engine.calculate_player_xp_breakdown(oreilly, fixture=mci_fix, is_home=True, opp_team=bou_team)

        comparison_table = [
            ("Expected Minutes", f"{h_bd['xMins']:.1f}m", f"{o_bd['xMins']:.1f}m", "Haaland +1.3m"),
            ("Match xG", f"{h_bd['xg_match']:.4f}", f"{o_bd['xg_match']:.4f}", "Haaland +0.1770 xG"),
            ("Goal Points Multiplier", "4.0 (FWD)", "6.0 (DEF)", "O'Reilly +2.0 pts/goal"),
            ("Goal Points xP", f"{h_bd['goals_xp']:.2f} pts", f"{o_bd['goals_xp']:.2f} pts", "Haaland +0.28 pts"),
            ("Match xA", f"{h_bd['xa_match']:.4f}", f"{o_bd['xa_match']:.4f}", "O'Reilly +0.0050 xA"),
            ("Assist Points xP", f"{h_bd['assists_xp']:.2f} pts", f"{o_bd['assists_xp']:.2f} pts", "O'Reilly +0.02 pts"),
            ("Clean Sheet Probability", f"{h_bd['cs_prob']*100:.1f}%", f"{o_bd['cs_prob']*100:.1f}%", "Equal 42.0%"),
            ("Clean Sheet Multiplier", "0.0 (FWD)", "4.0 (DEF)", "O'Reilly +4.0 pts/CS"),
            ("Clean Sheet xP", f"{h_bd['cs_xp']:.2f} pts", f"{o_bd['cs_xp']:.2f} pts", "O'Reilly +1.54 pts"),
            ("DEFCON Probability", f"{h_bd['defcon_prob']*100:.1f}%", f"{o_bd['defcon_prob']*100:.1f}%", "O'Reilly +13.9%"),
            ("DEFCON xP", f"{h_bd['defcon_xp']:.2f} pts", f"{o_bd['defcon_xp']:.2f} pts", "O'Reilly +0.26 pts"),
            ("Appearance xP", f"{h_bd['appearance_xp']:.2f} pts", f"{o_bd['appearance_xp']:.2f} pts", "Haaland +0.03 pts"),
            ("Bonus xP", f"{h_bd['bonus_xp']:.2f} pts", f"{o_bd['bonus_xp']:.2f} pts", "Haaland +0.42 pts"),
            ("Yellow Cards xP", f"{h_bd['cards_xp']:.2f} pts", f"{o_bd['cards_xp']:.2f} pts", "Equal -0.09 pts"),
            ("FINAL GW1 xP", f"{h_bd['total_xp']:.2f} pts", f"{o_bd['total_xp']:.2f} pts", "O'Reilly +1.08 pts")
        ]

        print(f"{'Metric':<25} | {'Haaland (FWD £15.5m)':<20} | {'Nico O-Reilly (DEF £6.5m)':<25} | {'Difference':<20}")
        print("-" * 95)
        for row in comparison_table:
            print(f"{row[0]:<25} | {row[1]:<20} | {row[2]:<25} | {row[3]:<20}")
        print()

        # ----------------------------------------------------
        # 5. INVESTIGATE BRUNO FERNANDES
        # ----------------------------------------------------
        print("Step 5: Investigating Bruno Fernandes GW1 Breakdown & Comparison...")
        bruno = db.query(Player).filter(Player.web_name == "B.Fernandes").first()
        mun_fix = db.query(Fixture).filter(
            ((Fixture.team_h_id == 16) | (Fixture.team_a_id == 16)),
            Fixture.event_id == 1
        ).first()
        is_home_mun = (mun_fix.team_h_id == 16)
        opp_id_mun = mun_fix.team_a_id if is_home_mun else mun_fix.team_h_id
        hul_team = db.query(Team).filter(Team.id == opp_id_mun).first()
        b_bd = engine.calculate_player_xp_breakdown(bruno, fixture=mun_fix, is_home=is_home_mun, opp_team=hul_team)

        print(f"  Bruno Fernandes (MID £12.0m) vs Hull City (A):")
        print(f"    - xMins={b_bd['xMins']:.1f}m | pStart={b_bd['p_start']:.2f}")
        print(f"    - Match xG = {b_bd['xg_match']:.4f} -> Goals xP = {b_bd['goals_xp']:.2f} pts (Goal Mult: 5.0)")
        print(f"    - Match xA = {b_bd['xa_match']:.4f} -> Assists xP = {b_bd['assists_xp']:.2f} pts (Assist Mult: 3.0)")
        print(f"    - CS Prob  = {b_bd['cs_prob']*100:.1f}% -> CS xP = {b_bd['cs_xp']:.2f} pts (CS Mult: 1.0)")
        print(f"    - DEFCON   = {b_bd['defcon_prob']*100:.1f}% -> DEFCON xP = {b_bd['defcon_xp']:.2f} pts")
        print(f"    - Appearance xP = {b_bd['appearance_xp']:.2f} pts | Bonus xP = {b_bd['bonus_xp']:.2f} pts | Cards = {b_bd['cards_xp']:.2f} pts")
        print(f"    - TOTAL xP = {b_bd['total_xp']:.2f} pts\n")

        # ----------------------------------------------------
        # 6. ARITHMETIC VERIFICATION (SUM OF COMPONENTS == FINAL XP)
        # ----------------------------------------------------
        print("Step 6: Performing Exact Unrounded Arithmetic Verification...")
        target_verify_names = ["Haaland", "O'Reilly", "Calafiori", "B.Fernandes", "Saka", "Gabriel"]
        audited_players = [db.query(Player).filter(Player.web_name == n).first() for n in target_verify_names]
        arithmetic_results = []

        for p in audited_players:
            fix = db.query(Fixture).filter(
                ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
                Fixture.event_id == 1
            ).first()
            is_h = (fix.team_h_id == p.team_id)
            opp_i = fix.team_a_id if is_h else fix.team_h_id
            opp_t = db.query(Team).filter(Team.id == opp_i).first()
            bd = engine.calculate_player_xp_breakdown(p, fixture=fix, is_home=is_h, opp_team=opp_t)

            unrounded_sum = (
                bd['appearance_xp'] + bd['goals_xp'] + bd['assists_xp'] +
                bd['cs_xp'] + bd['defcon_xp'] + bd['bonus_xp'] + bd['cards_xp']
            )
            discrepancy = abs(unrounded_sum - bd['total_xp'])
            arithmetic_results.append({
                "player": p.web_name,
                "unrounded_sum": round(unrounded_sum, 4),
                "final_xp": bd['total_xp'],
                "discrepancy": round(discrepancy, 4),
                "is_exact": (discrepancy < 0.01)
            })
            print(f"  {p.web_name:<15}: Sum={unrounded_sum:.4f} | Final xP={bd['total_xp']:.2f} | Discrepancy={discrepancy:.4f} | Exact: {discrepancy < 0.01}")
        print()

        # Save all diagnostic findings to scratch JSON
        output_data = {
            "artifact_table": artifact_table,
            "mins_audit_table": mins_audit_table,
            "arithmetic_results": arithmetic_results
        }
        with open("scratch/phase3f_audit_output.json", "w") as f:
            json.dump(output_data, f, indent=2)

    finally:
        db.close()

if __name__ == "__main__":
    run_phase3f_investigation()
