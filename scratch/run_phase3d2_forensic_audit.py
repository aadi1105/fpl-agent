import sys
import os
import hashlib
import json
import math

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

from backend.database import SessionLocal
from backend.models import Player, Team, Fixture, Gameweek, PlayerProjection, ElementType
from backend.projections.engine import ProjectionEngine
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.ml.minutes_predictor import MinutesPredictor
from backend.ml.xg_predictor import XGPredictor
from backend.ml.xa_predictor import XAPredictor
from backend.ml.cs_predictor import CSPredictor
from backend.ml.defcon_predictor import DEFCONPredictor

def get_sha256(filepath):
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def run_audit():
    db = SessionLocal()
    print("=" * 80)
    print("PHASE 3D.2 — PRODUCTION PROJECTION & FIXTURE PIPELINE FORENSIC AUDIT")
    print("=" * 80)

    # ---------------------------------------------------------
    # PART 2 — RUNTIME MODEL ARTIFACT VERIFICATION
    # ---------------------------------------------------------
    print("\n--- PART 2: RUNTIME MODEL ARTIFACT VERIFICATION ---")
    mins_pred = MinutesPredictor()
    xg_pred = XGPredictor()
    xa_pred = XAPredictor()
    cs_pred = CSPredictor()
    defcon_pred = DEFCONPredictor()

    predictors_info = [
        ("MinutesPredictor (v2)", os.path.join(mins_pred.model_dir, "expected_minutes_v2.pkl"), getattr(mins_pred, "model_version", "unknown"), mins_pred.is_loaded),
        ("MinutesPredictor (p_start)", os.path.join(mins_pred.model_dir, "minutes_start_v1.pkl"), "v1", mins_pred.m_start is not None),
        ("MinutesPredictor (p_mins)", os.path.join(mins_pred.model_dir, "minutes_regression_v1.pkl"), "v1", mins_pred.m_mins is not None),
        ("XGPredictor", os.path.join(xg_pred.model_dir, getattr(xg_pred, "model_version", "xg_v2") + ".pkl"), getattr(xg_pred, "model_version", "unknown"), xg_pred.is_loaded),
        ("XAPredictor", os.path.join(xa_pred.model_dir, getattr(xa_pred, "model_version", "xa_v2") + ".pkl"), getattr(xa_pred, "model_version", "unknown"), xa_pred.is_loaded),
        ("CSPredictor", getattr(cs_pred, "MODEL_PATH", os.path.join("backend", "ml", "models", "cs_v1_lgbm.pkl")), getattr(cs_pred, "version", "unknown"), cs_pred.model is not None),
        ("DEFCONPredictor", "Builtin Poisson", getattr(defcon_pred, "model_version", "defcon_v1_poisson"), True),
    ]

    for name, path, ver, loaded in predictors_info:
        sha = get_sha256(path) if os.path.exists(str(path)) else "N/A (Builtin/Missing)"
        print(f"[{name}] Version: {ver} | Path: {path} | SHA256: {sha[:16]}... | Loaded: {loaded}")

    # ---------------------------------------------------------
    # PART 1, 4, 5, 6, 7, 8, 9 — TRACE 12 AUDITED PLAYERS END-TO-END
    # ---------------------------------------------------------
    print("\n--- PART 1 & 4-9: TRACING 12 AUDITED PLAYERS END-TO-END ---")
    target_ids = [
        (411, "Erling Haaland"),
        (426, "Bruno Fernandes"),
        (328, "Mohamed Salah"),
        (154, "Cole Palmer"),
        (12, "Bukayo Saka"),
        (4, "Gabriel Magalhães"),
        (165, "João Pedro"),
        (346, "Dominic Calvert-Lewin"),
        (492, "Taiwo Awoniyi"),
        (465, "William Osula"),
        (15, "Riccardo Calafiori"),
        (397, "Antoine Semenyo")
    ]

    engine = ProjectionEngine(db)

    audited_records = {}

    for p_id, name in target_ids:
        p = db.query(Player).filter(Player.id == p_id).first()
        if not p:
            print(f"WARNING: Player ID {p_id} ({name}) not found in DB!")
            continue
        
        team = db.query(Team).filter(Team.id == p.team_id).first()
        t_name = team.name if team else "Unknown"
        t_short = team.short_name if team else "UNK"

        print("\n" + "=" * 60)
        print(f"PLAYER TRACE: {p.web_name} (ID: {p.id}, Pos: {p.element_type}, Team: {t_name} [{t_short}])")
        print(f"  Price: now_cost={p.now_cost} (£{p.now_cost/10.0:.1f}m) | Ownership: {p.selected_by_percent}% | Status: {p.status}")
        print(f"  Raw DB Stats: mins={p.minutes}, goals={p.goals_scored}, assists={p.assists}, xG={p.expected_goals}, xA={p.expected_assists}, BPS={p.bps}")

        gw_breakdowns = []
        for gw in range(1, 5):
            fixtures = db.query(Fixture).filter(Fixture.event_id == gw).all()
            p_fix = None
            is_home = True
            opp_t = None
            for f in fixtures:
                if f.team_h_id == p.team_id:
                    p_fix = f
                    is_home = True
                    opp_t = db.query(Team).filter(Team.id == f.team_a_id).first()
                    break
                elif f.team_a_id == p.team_id:
                    p_fix = f
                    is_home = False
                    opp_t = db.query(Team).filter(Team.id == f.team_h_id).first()
                    break
            
            if p_fix:
                b = engine.calculate_player_xp_breakdown(p, p_fix, is_home, opp_t)
                gw_breakdowns.append((gw, p_fix, is_home, opp_t, b))
                print(f"  GW{gw} Fixture: ID {p_fix.id} | vs {opp_t.name if opp_t else 'OPP'} ({'H' if is_home else 'A'}) | Diff: {b['fixture_difficulty']}")
                print(f"       Team Att/Def: {b['team_attack_rating']}/{b['team_defence_rating']} | Opp Att/Def: {b['opp_attack_rating']}/{b['opp_defence_rating']} | Att Mod: {b['fixture_attack_modifier']}")
                print(f"       xMins Baseline: {b['expected_minutes_baseline']} | xMins ML: {b['expected_minutes_ml']} (p_start: {b['p_start']}, fallback: {b['used_fallback']}) -> Final xMins: {b['xMins']}")
                print(f"       xG Base/ML/Match: {b['xg_baseline']}/{b['xg_ml']}/{b['xg_match']} (ver: {b['xg_model_version']}, fallback: {b['used_xg_fallback']})")
                print(f"       xA Base/ML/Match: {b['xa_baseline']}/{b['xa_ml']}/{b['xa_match']} (ver: {b['xa_model_version']}, fallback: {b['used_xa_fallback']})")
                print(f"       CS Prob: {b['cs_prob']} | DEFCON Prob: {b['defcon_prob']}")
                print(f"       Scoring Breakdown: App: {b['appearance_xp']} | Goals: {b['goals_xp']} | Assists: {b['assists_xp']} | CS: {b['cs_xp']} | DEFCON: {b['defcon_xp']} | Saves: {b['saves_xp']} | Bonus: {b['bonus_xp']} | Cards: {b['cards_xp']} => TOTAL xP: {b['total_xp']}")
            else:
                print(f"  GW{gw}: NO FIXTURE FOR TEAM ID {p.team_id}!")

        audited_records[p.id] = (p, gw_breakdowns)

    # ---------------------------------------------------------
    # PART 3 & 15 — RECONCILIATION OF HAALAND PROJECTION DISCREPANCY
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("PART 3 & 15: FORENSIC INVESTIGATION OF HAALAND PROJECTION DISCREPANCY")
    print("=" * 80)
    
    haaland = db.query(Player).filter(Player.id == 411).first()
    h_gw1_b = engine.calculate_player_xp_breakdown(haaland, db.query(Fixture).filter(Fixture.event_id == 1, (Fixture.team_h_id == haaland.team_id) | (Fixture.team_a_id == haaland.team_id)).first(), True, None)

    print("\n[HAALAND GW1 PROJECTION BREAKDOWN CURRENT PRODUCTION]")
    print(f"  - Database minutes: {haaland.minutes}")
    print(f"  - Baseline Deterministic xMins: {h_gw1_b['expected_minutes_baseline']}")
    print(f"  - ML Expected Minutes (expected_minutes_v2): {h_gw1_b['expected_minutes_ml']}")
    print(f"  - ML p_start: {h_gw1_b['p_start']}")
    print(f"  - Engine use_ml_minutes: {engine.use_ml_minutes}")
    print(f"  - Engine ML Fallback Used: {h_gw1_b['used_fallback']}")
    print(f"  - Final Engine xMins: {h_gw1_b['xMins']}")
    print(f"  - ML xG Prediction: {h_gw1_b['xg_ml']} (baseline: {h_gw1_b['xg_baseline']}, match: {h_gw1_b['xg_match']})")
    print(f"  - Total GW1 xP: {h_gw1_b['total_xp']}")

    # Let's test what Haaland's projection would be IF baseline xMins (84.0) was used vs ML xMins (16.2)!
    print("\n[HYPOTHETICAL RECONSTRUCTION: IF DETERMINISTIC BASELINE xMINS IS USED]")
    engine_no_ml_mins = ProjectionEngine(db, use_ml_minutes=False, use_ml_xg=False, use_ml_xa=False)
    h_gw1_base = engine_no_ml_mins.calculate_player_xp_breakdown(haaland, db.query(Fixture).filter(Fixture.event_id == 1, (Fixture.team_h_id == haaland.team_id) | (Fixture.team_a_id == haaland.team_id)).first(), True, None)
    print(f"  - Deterministic Baseline GW1 xMins: {h_gw1_base['xMins']}")
    print(f"  - Deterministic Baseline GW1 xG: {h_gw1_base['xg_match']}")
    print(f"  - Deterministic Baseline GW1 xA: {h_gw1_base['xa_match']}")
    print(f"  - Deterministic Baseline Total GW1 xP: {h_gw1_base['total_xp']}")

    # Let's test with ML xG/xA but deterministic xMins (84.0 mins)!
    engine_ml_xg_only = ProjectionEngine(db, use_ml_minutes=False, use_ml_xg=True, use_ml_xa=True)
    h_gw1_ml_xg = engine_ml_xg_only.calculate_player_xp_breakdown(haaland, db.query(Fixture).filter(Fixture.event_id == 1, (Fixture.team_h_id == haaland.team_id) | (Fixture.team_a_id == haaland.team_id)).first(), True, None)
    print(f"\n[HYPOTHETICAL RECONSTRUCTION: IF DETERMINISTIC xMINS (84.0) + ML xG/xA IS USED]")
    print(f"  - GW1 xMins: {h_gw1_ml_xg['xMins']}")
    print(f"  - ML xG (with 84m): {h_gw1_ml_xg['xg_match']}")
    print(f"  - ML xA (with 84m): {h_gw1_ml_xg['xa_match']}")
    print(f"  - Total GW1 xP: {h_gw1_ml_xg['total_xp']}")

    # ---------------------------------------------------------
    # PART 10, 11 & 13 — OPTIMIZER & RANKINGS SANITY CHECK
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("PART 10, 11 & 13: OPTIMIZER INPUT & RANKINGS SANITY CHECK")
    print("=" * 80)
    
    # Run projections into DB first to be 100% sure PlayerProjection table has exact engine outputs
    engine.run_projections(1, 4, "internal")

    all_players = db.query(Player).all()
    player_scores = []
    for p in all_players:
        projs = db.query(PlayerProjection).filter(
            PlayerProjection.player_id == p.id,
            PlayerProjection.source == "internal"
        ).all()
        p_map = {pr.gameweek_id: pr.expected_points for pr in projs}
        gw1_xp = p_map.get(1, 0.0)
        gw2_xp = p_map.get(2, 0.0)
        gw3_xp = p_map.get(3, 0.0)
        gw4_xp = p_map.get(4, 0.0)
        weighted_xp = round(0.55 * gw1_xp + 0.20 * gw2_xp + 0.15 * gw3_xp + 0.10 * gw4_xp, 2)
        player_scores.append({
            "id": p.id,
            "web_name": p.web_name,
            "pos": p.element_type,
            "team_id": p.team_id,
            "price": p.now_cost / 10.0,
            "gw1_xp": gw1_xp,
            "gw2_xp": gw2_xp,
            "gw3_xp": gw3_xp,
            "gw4_xp": gw4_xp,
            "weighted_xp": weighted_xp
        })

    # Sort Top 20 by GW1 xP
    top_gw1 = sorted(player_scores, key=lambda x: x["gw1_xp"], reverse=True)[:20]
    print("\n--- TOP 20 PLAYERS BY GW1 xP ---")
    for rank, p in enumerate(top_gw1, 1):
        print(f"  #{rank:2d} | {p['web_name']:20s} ({p['pos']}) - £{p['price']:.1f}m | GW1 xP: {p['gw1_xp']:.2f} | Weighted: {p['weighted_xp']:.2f}")

    # Sort Top 20 by Weighted 4-GW Score
    top_weighted = sorted(player_scores, key=lambda x: x["weighted_xp"], reverse=True)[:20]
    print("\n--- TOP 20 PLAYERS BY WEIGHTED GW1-GW4 SCORE ---")
    for rank, p in enumerate(top_weighted, 1):
        print(f"  #{rank:2d} | {p['web_name']:20s} ({p['pos']}) - £{p['price']:.1f}m | Weighted: {p['weighted_xp']:.2f} | GW1 xP: {p['gw1_xp']:.2f}")

    # Run Squad Optimizer
    opt = SquadOptimizer(db)
    opt_res = opt.solve_squad_selection(mode="CURRENT_GW_PLUS_3")

    print("\n--- OPTIMIZER SOLVED SQUAD (CURRENT_GW_PLUS_3) ---")
    print(f"Total Budget Spent: £{opt_res['total_cost']:.1f}m / £100.0m")
    print(f"Captain: {opt_res['captain']['web_name']} | Vice: {opt_res['vice_captain']['web_name']}")
    print("\nStarting XI:")
    for p in opt_res['starting_11']:
        print(f"  [{p['element_type']:3s}] {p['web_name']:20s} ({p['team_name']:12s}) - £{p['now_cost']/10.0:.1f}m | GW1 xP: {p['gw0_xp']:.2f} | Weighted: {p['weighted_xp']:.2f}")
    print("\nBench:")
    for p in opt_res['bench']:
        print(f"  [{p['element_type']:3s}] {p['web_name']:20s} ({p['team_name']:12s}) - £{p['now_cost']/10.0:.1f}m | GW1 xP: {p['gw0_xp']:.2f} | Weighted: {p['weighted_xp']:.2f}")

    # ---------------------------------------------------------
    # PART 19 — GW0 TERMINOLOGY AUDIT
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("PART 19: GW0 TERMINOLOGY SEARCH IN PROJECT CODE")
    print("=" * 80)
    
    gw0_matches = []
    # Search python and text files for 'gw0' or 'GW0'
    for root, dirs, files in os.walk("."):
        if ".git" in root or "__pycache__" in root or ".venv" in root or "node_modules" in root:
            continue
        for file in files:
            if file.endswith((".py", ".ts", ".tsx", ".md", ".json")):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        for idx, line in enumerate(lines, 1):
                            if "gw0" in line.lower() and "phase" not in filepath.lower() and "prompts" not in filepath.lower():
                                gw0_matches.append((filepath, idx, line.strip()))
                except Exception:
                    pass

    print(f"Found {len(gw0_matches)} code/doc occurrences of 'gw0' / 'GW0':")
    for path, line_no, content in gw0_matches[:20]:
        print(f"  {path}:{line_no} -> {content}")

    db.close()

if __name__ == "__main__":
    run_audit()
