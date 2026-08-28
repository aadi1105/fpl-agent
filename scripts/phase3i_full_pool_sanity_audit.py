import os
import sys
import json
import numpy as np
import pandas as pd

sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models import Player, Fixture, Team, ElementType
from backend.projections.engine import ProjectionEngine

def run_phase3i_audit():
    print("=" * 80)
    print("PHASE 3I — FULL-POOL CALIBRATED PROJECTION SANITY AUDIT")
    print("=" * 80)

    db = SessionLocal()
    try:
        engine = ProjectionEngine(db=db)
        players = db.query(Player).all()
        print(f"Total Active Database Players Evaluated: {len(players)}")

        # Collect breakdown for every player in GW1
        audit_rows = []
        for p in players:
            fix = db.query(Fixture).filter(
                ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
                Fixture.event_id == 1
            ).first()
            
            if not fix:
                continue

            is_h = (fix.team_h_id == p.team_id)
            opp_i = fix.team_a_id if is_h else fix.team_h_id
            opp_t = db.query(Team).filter(Team.id == opp_i).first()
            p_team = db.query(Team).filter(Team.id == p.team_id).first()

            bd = engine.calculate_player_xp_breakdown(p, fixture=fix, is_home=is_h, opp_team=opp_t)

            audit_rows.append({
                "player_id": p.id,
                "name": p.web_name,
                "position": p.element_type,
                "club": p_team.short_name if p_team else "UNK",
                "price": p.now_cost / 10.0,
                "price_raw": p.now_cost,
                "fixture": bd["opponent"],
                "is_home": is_h,
                "status": p.status,
                "chance_of_playing": p.chance_of_playing_next_round,
                "expected_minutes": bd["xMins"],
                "p_start": bd["p_start"],
                "raw_xG": bd["xg_match"],
                "calibrated_xG": round(bd["xg_match"] * (engine.calibration_meta.get("prem_xg_ratio", 1.882) if (p.now_cost >= 100 and p.element_type in ['MID', 'FWD']) else engine.calibration_meta.get("non_prem_xg_ratio", 0.984)), 3),
                "raw_xA": bd["xa_match"],
                "calibrated_xA": round(bd["xa_match"] * (engine.calibration_meta.get("prem_xa_ratio", 3.020) if (p.now_cost >= 100 and p.element_type in ['MID', 'FWD']) else engine.calibration_meta.get("non_prem_xa_ratio", 1.446)), 3),
                "raw_CS": f"{bd['cs_prob']*100:.1f}%",
                "calibrated_CS": f"{float(engine.cs_calibrator.predict([bd['cs_prob']])[0])*100:.1f}%",
                "raw_CS_prob": bd['cs_prob'],
                "calibrated_CS_prob": float(engine.cs_calibrator.predict([bd['cs_prob']])[0]),
                "DEFCON": bd["defcon_prob"],
                "raw_xP": bd["raw_xp"],
                "calibrated_xP": bd["calibrated_xp"],
                "adjustment": bd["adjustment"],
                "historical_minutes": p.minutes
            })

        df = pd.DataFrame(audit_rows)
        print(f"Successfully processed {len(df)} player GW1 fixture projections.\n")

        # ----------------------------------------------------
        # 1. SECTION 2: POSITIONAL & PRICE TIER DISTRIBUTION
        # ----------------------------------------------------
        print("=" * 80)
        print("SECTION 2: POSITIONAL & PRICE TIER DISTRIBUTION SUMMARY")
        print("=" * 80)
        print(f"{'Position':<8} | {'Count':<6} | {'Mean Raw xP':<11} | {'Mean Cal xP':<11} | {'Median Cal xP':<13} | {'Min Cal':<8} | {'Max Cal':<8} | {'Std Dev':<8}")
        print("-" * 88)
        for pos in ['GKP', 'DEF', 'MID', 'FWD']:
            sub = df[df['position'] == pos]
            if len(sub) > 0:
                print(f"{pos:<8} | {len(sub):<6} | {sub['raw_xP'].mean():<11.2f} | {sub['calibrated_xP'].mean():<11.2f} | {sub['calibrated_xP'].median():<13.2f} | {sub['calibrated_xP'].min():<8.2f} | {sub['calibrated_xP'].max():<8.2f} | {sub['calibrated_xP'].std():<8.2f}")
        print()

        print("BY PRICE TIER:")
        print(f"{'Price Tier':<12} | {'Count':<6} | {'Mean Raw xP':<11} | {'Mean Cal xP':<11} | {'Median Cal xP':<13} | {'Max Cal xP':<10}")
        print("-" * 72)
        tiers = [
            ("£4.0–£5.0m", 40, 50),
            ("£5.0–£6.0m", 50, 60),
            ("£6.0–£8.0m", 60, 80),
            ("£8.0–£10.0m", 80, 100),
            ("£10.0–£12.0m", 100, 120),
            ("£12.0m+", 120, 200)
        ]
        for name, p_min, p_max in tiers:
            sub = df[(df['price_raw'] >= p_min) & (df['price_raw'] < p_max)]
            if len(sub) > 0:
                print(f"{name:<12} | {len(sub):<6} | {sub['raw_xP'].mean():<11.2f} | {sub['calibrated_xP'].mean():<11.2f} | {sub['calibrated_xP'].median():<13.2f} | {sub['calibrated_xP'].max():<10.2f}")
        print()

        # ----------------------------------------------------
        # 2. SECTION 3: TOP 30 CALIBRATED GW1 PLAYERS
        # ----------------------------------------------------
        print("=" * 80)
        print("SECTION 3: TOP 30 CALIBRATED GW1 PLAYERS")
        print("=" * 80)
        df_top30 = df.sort_values(by="calibrated_xP", ascending=False).head(30).reset_index(drop=True)
        print(f"{'Rank':<4} | {'Player':<15} | {'Pos':<4} | {'Club':<5} | {'Price':<6} | {'GW1 Fixture':<10} | {'xMins':<6} | {'Raw xP':<7} | {'Cal xP':<7} | {'Adjustment':<10}")
        print("-" * 95)
        for i, r in df_top30.iterrows():
            print(f"{i+1:<4} | {r['name']:<15} | {r['position']:<4} | {r['club']:<5} | £{r['price']:<5.1f}m | {r['fixture']:<10} | {r['expected_minutes']:<6.1f} | {r['raw_xP']:<7.2f} | {r['calibrated_xP']:<7.2f} | {r['adjustment']:<+10.2f}")
        print()

        # ----------------------------------------------------
        # 3. SECTION 4: BOTTOM / OUTLIER ADJUSTMENT AUDIT
        # ----------------------------------------------------
        print("=" * 80)
        print("SECTION 4: TOP 10 POSITIVE & TOP 10 NEGATIVE ADJUSTMENTS")
        print("=" * 80)
        print("TOP 10 POSITIVE ADJUSTMENTS (Attackers receiving xG/xA shrinkage boost):")
        pos_adj = df.sort_values(by="adjustment", ascending=False).head(10).reset_index(drop=True)
        print(f"{'Player':<15} | {'Pos':<4} | {'Price':<6} | {'Raw xG':<7} | {'Cal xG':<7} | {'Raw xA':<7} | {'Cal xA':<7} | {'Raw xP':<7} | {'Cal xP':<7} | {'Adjustment':<10}")
        print("-" * 95)
        for _, r in pos_adj.iterrows():
            print(f"{r['name']:<15} | {r['position']:<4} | £{r['price']:<5.1f}m | {r['raw_xG']:<7.3f} | {r['calibrated_xG']:<7.3f} | {r['raw_xA']:<7.3f} | {r['calibrated_xA']:<7.3f} | {r['raw_xP']:<7.2f} | {r['calibrated_xP']:<7.2f} | {r['adjustment']:<+10.2f}")
        print()

        print("TOP 10 NEGATIVE ADJUSTMENTS (Defenders / GKs scaled down due to CS overprediction):")
        neg_adj = df.sort_values(by="adjustment", ascending=True).head(10).reset_index(drop=True)
        print(f"{'Player':<15} | {'Pos':<4} | {'Price':<6} | {'Raw CS':<7} | {'Cal CS':<7} | {'Raw xP':<7} | {'Cal xP':<7} | {'Adjustment':<10}")
        print("-" * 80)
        for _, r in neg_adj.iterrows():
            print(f"{r['name']:<15} | {r['position']:<4} | £{r['price']:<5.1f}m | {r['raw_CS']:<7} | {r['calibrated_CS']:<7} | {r['raw_xP']:<7.2f} | {r['calibrated_xP']:<7.2f} | {r['adjustment']:<+10.2f}")
        print()

        # ----------------------------------------------------
        # 4. SECTION 5 & 6: PREMIUM ATTACKER & DEFENDER AUDIT
        # ----------------------------------------------------
        print("=" * 80)
        print("SECTION 5 & 6: BENCHMARK PLAYERS AUDIT")
        print("=" * 80)
        benchmarks = ["Haaland", "B.Fernandes", "Saka", "Palmer", "João Pedro", "Calvert-Lewin", "Marmoush", "Isak", "Watkins", "Son", "O'Reilly", "Gvardiol", "Calafiori", "Gabriel", "Raya", "Pope"]
        df_bench = df[df['name'].str.contains('|'.join(benchmarks), case=False, na=False)].sort_values(by="calibrated_xP", ascending=False).reset_index(drop=True)
        print(f"{'Player':<15} | {'Pos':<4} | {'Price':<6} | {'Fixture':<10} | {'xMins':<6} | {'Cal xG':<7} | {'Cal xA':<7} | {'Cal CS':<7} | {'Raw xP':<7} | {'Cal xP':<7} | {'Rank':<4}")
        print("-" * 95)
        for _, r in df_bench.iterrows():
            rk = df.sort_values(by="calibrated_xP", ascending=False).reset_index(drop=True)[df.sort_values(by="calibrated_xP", ascending=False).reset_index(drop=True)['player_id'] == r['player_id']].index[0] + 1
            print(f"{r['name']:<15} | {r['position']:<4} | £{r['price']:<5.1f}m | {r['fixture']:<10} | {r['expected_minutes']:<6.1f} | {r['calibrated_xG']:<7.3f} | {r['calibrated_xA']:<7.3f} | {r['calibrated_CS']:<7} | {r['raw_xP']:<7.2f} | {r['calibrated_xP']:<7.2f} | #{rk:<3}")
        print()

        # ----------------------------------------------------
        # 5. SECTION 7: MINUTES CONCENTRATION CHECK
        # ----------------------------------------------------
        df_starters = df[(df['p_start'] >= 0.90) & (df['expected_minutes'] >= 82.0) & (df['position'] != 'GKP')].sort_values(by="calibrated_xP", ascending=False)
        print(f"Outfield Players with P(start) >= 0.90 & E[mins] >= 82: {len(df_starters)} players")
        print()

        # ----------------------------------------------------
        # 6. SECTION 8: LOW-SAMPLE AUDIT (<300 HISTORICAL MINS IN TOP 100)
        # ----------------------------------------------------
        df_ranked = df.sort_values(by="calibrated_xP", ascending=False).reset_index(drop=True)
        df_ranked['rank'] = df_ranked.index + 1
        low_sample_top100 = df_ranked[(df_ranked['rank'] <= 100) & (df_ranked['historical_minutes'] < 300)]
        print("=" * 80)
        print("SECTION 8: LOW-SAMPLE PLAYERS (<300 HISTORICAL MINS) IN TOP 100")
        print("=" * 80)
        if len(low_sample_top100) > 0:
            print(f"{'Rank':<4} | {'Player':<15} | {'Hist Mins':<10} | {'Price':<6} | {'xMins':<6} | {'Cal xG':<7} | {'Cal xA':<7} | {'Raw xP':<7} | {'Cal xP':<7}")
            print("-" * 80)
            for _, r in low_sample_top100.iterrows():
                print(f"#{r['rank']:<3} | {r['name']:<15} | {r['historical_minutes']:<10.0f} | £{r['price']:<5.1f}m | {r['expected_minutes']:<6.1f} | {r['calibrated_xG']:<7.3f} | {r['calibrated_xA']:<7.3f} | {r['raw_xP']:<7.2f} | {r['calibrated_xP']:<7.2f}")
        else:
            print("Zero low-sample players found in Top 100!")
        print()

        # ----------------------------------------------------
        # 7. SECTION 9: TRANSFERS / CURRENT CLUB AUDIT
        # ----------------------------------------------------
        print("=" * 80)
        print("SECTION 9: TRANSFERS / CURRENT CLUB AUDIT")
        print("=" * 80)
        tx_names = ["Awoniyi", "Nelson", "Rice", "Solanke", "Neto", "Smith Rowe"]
        df_tx = df[df['name'].str.contains('|'.join(tx_names), case=False, na=False)]
        print(f"{'Player':<15} | {'Club':<5} | {'GW1 Fixture':<10} | {'xMins':<6} | {'Cal xP':<7}")
        print("-" * 55)
        for _, r in df_tx.iterrows():
            print(f"{r['name']:<15} | {r['club']:<5} | {r['fixture']:<10} | {r['expected_minutes']:<6.1f} | {r['calibrated_xP']:<7.2f}")
        print()

        # ----------------------------------------------------
        # 8. SECTION 14: RAW TOP 20 VS CALIBRATED TOP 20 SIDE-BY-SIDE
        # ----------------------------------------------------
        print("=" * 80)
        print("SECTION 14: RAW TOP 20 VS CALIBRATED TOP 20 COMPARISON")
        print("=" * 80)
        raw_top20 = df.sort_values(by="raw_xP", ascending=False).head(20).reset_index(drop=True)
        cal_top20 = df.sort_values(by="calibrated_xP", ascending=False).head(20).reset_index(drop=True)

        print(f"{'Rank':<4} | {'RAW TOP 20 PLAYER':<20} | {'Raw xP':<7} | {'CALIBRATED TOP 20 PLAYER':<25} | {'Cal xP':<7}")
        print("-" * 75)
        for i in range(20):
            r_row = raw_top20.iloc[i]
            c_row = cal_top20.iloc[i]
            print(f"{i+1:<4} | {r_row['name'] + ' (' + r_row['position'] + ')':<20} | {r_row['raw_xP']:<7.2f} | {c_row['name'] + ' (' + c_row['position'] + ')':<25} | {c_row['calibrated_xP']:<7.2f}")
        print()

    finally:
        db.close()

if __name__ == "__main__":
    run_phase3i_audit()
