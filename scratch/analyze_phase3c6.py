import json
import math
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture
from backend.projections.engine import ProjectionEngine, PRICE_TIER_DEFAULTS

def analyze():
    db: Session = SessionLocal()
    engine = ProjectionEngine(db)
    
    with open("scratch/phase3c6_audit_output.json", "r") as f:
        data = json.load(f)
        
    # Get all players and calculate ranks
    teams_map = {t.id: t for t in db.query(Team).all()}
    all_players = db.query(Player).all()
    
    # Calculate diagnostics for all players
    all_diag = []
    for p in all_players:
        fix = db.query(Fixture).filter(
            Fixture.event_id == 1,
            (Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)
        ).first()
        is_home = fix.team_h_id == p.team_id if fix else True
        opp_team_id = (fix.team_a_id if is_home else fix.team_h_id) if fix else 1
        opp_team = teams_map.get(opp_team_id)
        bd = engine.calculate_player_xp_breakdown(p, fix, is_home, opp_team)
        all_diag.append({
            "id": p.id,
            "web_name": p.web_name,
            "position": p.element_type,
            "price": p.now_cost / 10.0,
            "total_xp": bd["total_xp"],
            "ownership": p.selected_by_percent,
            "breakdown": bd
        })
        
    # Compute Model Rank and Consensus Rank per position
    pos_ranks = {}
    for pos in ["FWD", "MID", "DEF", "GKP"]:
        pos_list = [p for p in all_diag if p["position"] == pos]
        
        # Model Rank (xp desc)
        pos_list.sort(key=lambda x: x["total_xp"], reverse=True)
        for i, p in enumerate(pos_list):
            p["model_rank"] = i + 1
            
        # Consensus Rank (ownership desc)
        pos_list.sort(key=lambda x: x["ownership"], reverse=True)
        for i, p in enumerate(pos_list):
            p["consensus_rank"] = i + 1
            
        pos_ranks[pos] = {p["id"]: p for p in pos_list}

    print("=== TARGET PLAYER COMPLETE PRODUCTION OUTPUT ===")
    for key, pinfo in data.items():
        pid = pinfo["player_id"]
        pos = pinfo["element_type"]
        pos_info = pos_ranks[pos].get(pid, {})
        bd = pinfo["breakdown"]
        
        print(f"\n--- {key} ({pinfo['team']}, £{pinfo['price']}m, {pos}) ---")
        print(f"  FPL Ownership: {pinfo['ownership']}% | Model Rank: #{pos_info.get('model_rank', 'N/A')} | Consensus Rank: #{pos_info.get('consensus_rank', 'N/A')}")
        print(f"  GW0 Fixture: {bd['opponent']} (Difficulty: {bd['fixture_difficulty']})")
        print(f"  xMins: {bd['xMins']} | P(start): {bd['p_start']} | P(60+): {bd['p_60_plus']} | P(0): {bd['p_zero']}")
        print(f"  xG Match: {bd['xg_match']} | xA Match: {bd['xa_match']}")
        print(f"  Goal xP: {bd['goals_xp']} | Assist xP: {bd['assists_xp']} | CS xP: {bd['cs_xp']} | DEFCON xP: {bd['defcon_xp']} | Bonus xP: {bd['bonus_xp']} | Cards xP: {bd['cards_xp']} | Total xP: {bd['total_xp']}")
        print(f"  DB Minutes: {pinfo['db_minutes']} | DB Goals: {pinfo['db_goals']} | DB Assists: {pinfo['db_assists']} | DB xG: {pinfo['db_expected_goals']} | DB xA: {pinfo['db_expected_assists']}")
        
        # Calculate raw per-90
        mins = pinfo['db_minutes']
        xg = pinfo['db_expected_goals'] if pinfo['db_expected_goals'] > 0 else pinfo['db_goals']
        xa = pinfo['db_expected_assists'] if pinfo['db_expected_assists'] > 0 else pinfo['db_assists']
        raw_xg90 = (xg / (mins / 90.0)) if mins > 0 else 0.0
        raw_xa90 = (xa / (mins / 90.0)) if mins > 0 else 0.0
        
        # 95% Confidence Interval for xG/90 (Poisson approximate SE)
        # SE = sqrt(xg_events) / (mins / 90.0)
        n_xg_events = max(1.0, xg)
        se_xg90 = math.sqrt(n_xg_events) / (mins / 90.0) if mins > 0 else 0.0
        ci_xg90_low = max(0.0, raw_xg90 - 1.96 * se_xg90)
        ci_xg90_high = raw_xg90 + 1.96 * se_xg90
        
        print(f"  Raw xG/90: {raw_xg90:.3f} (95% CI: [{ci_xg90_low:.3f}, {ci_xg90_high:.3f}]) | Raw xA/90: {raw_xa90:.3f}")

    print("\n\n=== SENSITIVITY ANALYSIS 1: EXPECTED MINUTES ===")
    print("Player\t\t30m xP\t45m xP\t60m xP\t75m xP\t90m xP\t(Prod xMins / xP)")
    for key in ["Awoniyi", "Osula", "Marmoush", "Beto", "Haaland", "João Pedro", "Calvert-Lewin"]:
        pinfo = data[key]
        pid = pinfo["player_id"]
        p = db.query(Player).filter(Player.id == pid).first()
        fix = db.query(Fixture).filter(Fixture.event_id == 1, (Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)).first()
        is_home = fix.team_h_id == p.team_id if fix else True
        opp_team_id = (fix.team_a_id if is_home else fix.team_h_id) if fix else 1
        opp_team = teams_map.get(opp_team_id)
        
        xp_mins = []
        for m in [30, 45, 60, 75, 90]:
            # Temporarily compute breakdown with overridden xMins
            bd = engine.calculate_player_xp_breakdown(p, fix, is_home, opp_team)
            # Recompute total_xp under m mins
            att_mult = bd["fixture_attack_modifier"]
            pos = p.element_type
            metrics = engine.get_player_per_90_metrics(p)
            mins_r = m / 90.0
            app_xp = (2.0 if m >= 60 else 1.0) * mins_r
            g_val = 6.0 if pos in ["DEF", "GKP"] else (5.0 if pos == "MID" else 4.0)
            a_val = 3.0
            
            # Use production xG match scaled by minutes ratio
            xg_match_m = (bd["xg_ml"] if not bd["used_xg_fallback"] else bd["xg_baseline"]) * att_mult * mins_r
            xa_match_m = (bd["xa_ml"] if not bd["used_xa_fallback"] else bd["xa_baseline"]) * att_mult * mins_r
            
            g_xp = xg_match_m * g_val
            a_xp = xa_match_m * a_val
            cs_xp = (bd["cs_prob"] * (4.0 if pos in ["GKP", "DEF"] else 1.0) * mins_r) if pos != "FWD" else 0.0
            defcon_xp = bd["defcon_prob"] * 2.0 * mins_r
            bonus_xp = bd["bonus_xp"] * mins_r
            cards_xp = -0.10 * mins_r
            
            tot = max(0.0, round(app_xp + g_xp + a_xp + cs_xp + defcon_xp + bonus_xp + cards_xp, 2))
            xp_mins.append(tot)
            
        prod_bd = pinfo["breakdown"]
        print(f"{key:<12}\t{xp_mins[0]:.2f}\t{xp_mins[1]:.2f}\t{xp_mins[2]:.2f}\t{xp_mins[3]:.2f}\t{xp_mins[4]:.2f}\t({prod_bd['xMins']}m -> {prod_bd['total_xp']:.2f} xP)")

    print("\n\n=== SENSITIVITY ANALYSIS 2: BAYESIAN PER-90 RATE SHRINKAGE ===")
    print("Player\t\tObs xG/90\tPrior xG/90\tShrunk xG/90\tProd xP\tShrunk xP\tShrunk Rank")
    M0 = 900.0 # 10 full matches prior weight
    
    for key in ["Awoniyi", "Osula", "Marmoush", "Beto", "Haaland", "João Pedro", "Calvert-Lewin"]:
        pinfo = data[key]
        pid = pinfo["player_id"]
        p = db.query(Player).filter(Player.id == pid).first()
        pos = p.element_type
        cost = p.now_cost
        
        if cost >= 90 if pos in ["MID", "FWD"] else cost >= 60:
            tier = "high"
        elif cost >= 65 if pos in ["MID", "FWD"] else cost >= 50:
            tier = "mid"
        else:
            tier = "low"
            
        prior_xg90 = PRICE_TIER_DEFAULTS[pos][tier]["xg90"]
        prior_xa90 = PRICE_TIER_DEFAULTS[pos][tier]["xa90"]
        
        mins = float(p.minutes)
        xg = float(p.expected_goals if p.expected_goals > 0 else p.goals_scored)
        xa = float(p.expected_assists if p.expected_assists > 0 else p.assists)
        obs_xg90 = (xg / (mins / 90.0)) if mins > 0 else prior_xg90
        obs_xa90 = (xa / (mins / 90.0)) if mins > 0 else prior_xa90
        
        # Empirical Bayes Shrinkage formula: (mins / (mins + M0)) * obs + (M0 / (mins + M0)) * prior
        w = mins / (mins + M0)
        shrunk_xg90 = (w * obs_xg90) + ((1.0 - w) * prior_xg90)
        shrunk_xa90 = (w * obs_xa90) + ((1.0 - w) * prior_xa90)
        
        prod_bd = pinfo["breakdown"]
        xMins = prod_bd["xMins"]
        mins_r = xMins / 90.0
        att_mult = prod_bd["fixture_attack_modifier"]
        
        shrunk_xg_match = shrunk_xg90 * mins_r * att_mult
        shrunk_xa_match = shrunk_xa90 * mins_r * att_mult
        
        g_val = 6.0 if pos in ["DEF", "GKP"] else (5.0 if pos == "MID" else 4.0)
        a_val = 3.0
        app_xp = (2.0 if xMins >= 60 else 1.0) * mins_r
        g_xp = shrunk_xg_match * g_val
        a_xp = shrunk_xa_match * a_val
        cs_xp = (prod_bd["cs_prob"] * (4.0 if pos in ["GKP", "DEF"] else 1.0) * mins_r) if pos != "FWD" else 0.0
        defcon_xp = prod_bd["defcon_prob"] * 2.0 * mins_r
        bonus_xp = prod_bd["bonus_xp"] * mins_r
        cards_xp = -0.10 * mins_r
        
        shrunk_xp = max(0.0, round(app_xp + g_xp + a_xp + cs_xp + defcon_xp + bonus_xp + cards_xp, 2))
        
        print(f"{key:<12}\t{obs_xg90:.3f}\t\t{prior_xg90:.3f}\t\t{shrunk_xg90:.3f}\t\t{prod_bd['total_xp']:.2f}\t{shrunk_xp:.2f}")

if __name__ == "__main__":
    analyze()
