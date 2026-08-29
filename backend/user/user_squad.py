import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.models import UserSquad, UserPick, Player, Team, ElementType, PlayerProjection
from backend.ingestion.current_state import CurrentGameStateManager

logger = logging.getLogger("user_squad")

class UserSquadManager:
    def __init__(self, db: Session):
        self.db = db

    def _get_squad_raw(self) -> UserSquad:
        squad = self.db.query(UserSquad).first()
        if not squad:
            squad = UserSquad(
                name="My FPL Team",
                bank=0,  # £0.0m
                free_transfers=1,
                active_chip=None
            )
            self.db.add(squad)
            self.db.commit()
            self.db.refresh(squad)
        return squad

    def get_or_create_user_squad(self) -> UserSquad:
        """Retrieve existing user squad. Returns empty unconfigured squad if none exists."""
        return self._get_squad_raw()

    def update_user_squad(
        self, 
        player_ids: List[int], 
        bank: int = 0, 
        free_transfers: int = 1, 
        active_chip: Optional[str] = None,
        captain_id: Optional[int] = None,
        vice_captain_id: Optional[int] = None,
        starter_ids: Optional[List[int]] = None
    ) -> UserSquad:
        """Update persistent user squad with 15 player IDs, starters, captaincy, bank, and chips."""
        if len(player_ids) != 15:
            raise ValueError("User squad must contain exactly 15 player IDs.")

        squad = self._get_squad_raw()
        squad.bank = bank
        squad.free_transfers = free_transfers
        squad.active_chip = active_chip

        # Remove old picks
        self.db.query(UserPick).filter(UserPick.squad_id == squad.id).delete()

        # Determine starter ordering if starter_ids specified
        ordered_ids = list(player_ids)
        if starter_ids and len(starter_ids) == 11:
            bench_ids = [pid for pid in player_ids if pid not in starter_ids]
            ordered_ids = list(starter_ids) + bench_ids

        # Set default captain (highest price or first starter) if not specified
        if not captain_id and ordered_ids:
            captain_id = ordered_ids[0]
        if not vice_captain_id and len(ordered_ids) > 1:
            vice_captain_id = ordered_ids[1]

        # Add new picks
        for idx, pid in enumerate(ordered_ids, start=1):
            is_cap = (pid == captain_id)
            is_vc = (pid == vice_captain_id)
            
            if idx <= 11:
                mult = 3 if (is_cap and active_chip == "triplecaptain") else (2 if is_cap else 1)
            else:
                mult = 0  # Bench

            pick = UserPick(
                squad_id=squad.id,
                player_id=pid,
                position=idx,
                is_captain=is_cap,
                is_vice_captain=is_vc,
                multiplier=mult
            )
            self.db.add(pick)

        self.db.commit()
        self.db.refresh(squad)
        return squad

    def get_user_squad_dict(self, current_gw: int = 1) -> Dict[str, Any]:
        """Format User Squad as a machine-readable dictionary with GW projections and FPL AI Team Rating."""
        squad = self.get_or_create_user_squad()
        
        picks_list = []
        total_cost = 0
        starting_xi_xp = 0.0
        bench_xp = 0.0

        for pick in squad.picks:
            p = pick.player
            total_cost += p.now_cost

            # Get projection for current GW
            proj = self.db.query(PlayerProjection).filter(
                PlayerProjection.player_id == p.id,
                PlayerProjection.gameweek_id == current_gw,
                PlayerProjection.source == "internal"
            ).first()

            gw_xp = round(proj.expected_points, 2) if proj else 0.0
            is_starter = (pick.position <= 11) or (pick.multiplier > 0)
            
            if is_starter:
                starting_xi_xp += gw_xp * (pick.multiplier if pick.multiplier > 0 else 1)
            else:
                bench_xp += gw_xp

            picks_list.append({
                "id": p.id,
                "web_name": p.web_name,
                "element_type": p.element_type,
                "position": p.element_type,
                "team_name": p.team.short_name if p.team else "",
                "now_cost": p.now_cost,
                "now_cost_str": f"£{p.now_cost / 10.0:.1f}m",
                "status": p.status,
                "chance_of_playing": p.chance_of_playing_next_round,
                "gw_xp": gw_xp,
                "total_xp": gw_xp,
                "expected_points_gw": gw_xp,
                "gw0_xp": gw_xp,
                "position_order": pick.position,
                "is_starter": is_starter,
                "is_captain": pick.is_captain,
                "is_vice_captain": pick.is_vice_captain,
                "multiplier": pick.multiplier
            })

        # Calculate transparent FPL AI Team Rating (0-100)
        starters = [p for p in picks_list if p["is_starter"]]
        bench = [p for p in picks_list if not p["is_starter"]]

        starter_raw_sum = sum(p["gw_xp"] for p in starters)
        bench_raw_sum = sum(p["gw_xp"] for p in bench)
        captain_p = next((p for p in starters if p["is_captain"]), None)
        captain_raw_xp = captain_p["gw_xp"] if captain_p else (max((p["gw_xp"] for p in starters), default=0.0))

        xi_score = min(100.0, (starter_raw_sum / 55.0) * 100.0) if len(starters) == 11 else 0.0
        bench_score = min(100.0, (bench_raw_sum / 10.0) * 100.0) if len(bench) == 4 else 0.0
        avail_starters = sum(1 for p in starters if p["status"] == "a" or p["chance_of_playing"] in (None, 100))
        avail_score = (avail_starters / 11.0) * 100.0 if len(starters) == 11 else 0.0
        max_xp_starter = max((p["gw_xp"] for p in starters), default=1.0)
        captain_score = min(100.0, (captain_raw_xp / max(1.0, max_xp_starter)) * 100.0) if starters else 0.0
        fixture_score = min(100.0, (starter_raw_sum / 50.0) * 90.0) if starters else 0.0

        overall_rating = round(0.40 * xi_score + 0.15 * bench_score + 0.20 * fixture_score + 0.15 * captain_score + 0.10 * avail_score, 1) if len(picks_list) == 15 else 0.0

        team_rating_breakdown = {
            "overall": overall_rating,
            "starting_xi": round(xi_score, 1),
            "bench": round(bench_score, 1),
            "fixtures": round(fixture_score, 1),
            "captaincy": round(captain_score, 1),
            "availability": round(avail_score, 1)
        }

        cap_obj = next((p for p in starters if p["is_captain"]), None)
        vc_obj = next((p for p in starters if p["is_vice_captain"]), None)

        return {
            "squad_id": squad.id,
            "name": squad.name,
            "is_configured": len(squad.picks) == 15,
            "total_cost": total_cost,
            "total_cost_str": f"£{total_cost / 10.0:.1f}m",
            "bank": squad.bank,
            "bank_str": f"£{squad.bank / 10.0:.1f}m",
            "free_transfers": squad.free_transfers,
            "active_chip": squad.active_chip,
            "starting_xi_xp": round(starting_xi_xp, 2),
            "bench_xp": round(bench_xp, 2),
            "squad_total_xp": round(starting_xi_xp + bench_xp, 2),
            "team_rating": overall_rating,
            "team_rating_breakdown": team_rating_breakdown,
            "starting_11": starters,
            "bench": bench,
            "captain": cap_obj,
            "vice_captain": vc_obj,
            "captain_id": cap_obj["id"] if cap_obj else None,
            "vice_captain_id": vc_obj["id"] if vc_obj else None,
            "picks": picks_list
        }

    def compare_with_optimal_squad(self, optimal_result: Dict[str, Any], current_gw: int = 1) -> Dict[str, Any]:
        """
        Compare user's actual squad vs optimizer's output squad.
        Returns KEEP, TRANSFER IN, TRANSFER OUT, BENCH CHANGE tags and differential stats.
        """
        my_squad = self.get_user_squad_dict(current_gw=current_gw)
        
        my_pids = {p["id"]: p for p in my_squad["picks"]}
        opt_starting = {p["id"]: p for p in optimal_result.get("starting_11", [])}
        opt_bench = {p["id"]: p for p in optimal_result.get("bench", [])}
        opt_all = {**opt_starting, **opt_bench}

        transfers_out = []
        transfers_in = []
        keeps = []
        bench_changes = []

        # Categorize current picks vs ideal optimal squad
        for pid, my_p in my_pids.items():
            if pid not in opt_all:
                transfers_out.append({
                    "action": "TRANSFER OUT",
                    "id": pid,
                    "web_name": my_p["web_name"],
                    "element_type": my_p["element_type"],
                    "team_name": my_p["team_name"],
                    "now_cost": my_p["now_cost"],
                    "now_cost_str": my_p["now_cost_str"],
                    "gw_xp": my_p["gw_xp"]
                })
            else:
                opt_p = opt_all[pid]
                my_starter = my_p["is_starter"]
                opt_starter = (pid in opt_starting)
                if my_starter != opt_starter:
                    bench_changes.append({
                        "action": "BENCH CHANGE",
                        "id": pid,
                        "web_name": my_p["web_name"],
                        "element_type": my_p["element_type"],
                        "from_starter": my_starter,
                        "to_starter": opt_starter,
                        "gw_xp": my_p["gw_xp"]
                    })
                else:
                    keeps.append({
                        "action": "KEEP",
                        "id": pid,
                        "web_name": my_p["web_name"],
                        "element_type": my_p["element_type"],
                        "gw_xp": my_p["gw_xp"]
                    })

        for pid, opt_p in opt_all.items():
            if pid not in my_pids:
                transfers_in.append({
                    "action": "TRANSFER IN",
                    "id": pid,
                    "web_name": opt_p["web_name"],
                    "element_type": opt_p["element_type"],
                    "team_name": opt_p["team_name"],
                    "now_cost": opt_p.get("now_cost", 0),
                    "now_cost_str": opt_p.get("now_cost_str", "£0.0m"),
                    "gw_xp": opt_p.get("gw0_xp", opt_p.get("gw_xp", 0.0))
                })

        # Calculate Best Legal Single Transfer (1 FT) from User's Squad
        best_transfer = None
        best_gain = 0.0  # Only recommend if net xP gain is strictly positive (> 0.0)

        user_squad_cost = sum(p["now_cost"] for p in my_squad["picks"])
        user_bank = my_squad.get("bank", 0)

        # Candidates to buy: top projection players not in squad
        all_players = self.db.query(Player).all()
        teams_map = {t.id: t.short_name for t in self.db.query(Team).all()}
        my_club_counts = {}
        for p in my_squad["picks"]:
            club = p["team_name"]
            my_club_counts[club] = my_club_counts.get(club, 0) + 1

        for out_p in my_squad["picks"]:
            out_club = out_p["team_name"]
            # Try replacing with unowned players of same position
            for buy_cand in all_players:
                if buy_cand.id in my_pids:
                    continue
                if buy_cand.element_type != out_p["element_type"]:
                    continue
                
                # Check strict budget affordability: buy_cost - sell_cost <= user_bank
                cost_diff = buy_cand.now_cost - out_p["now_cost"]
                if cost_diff > user_bank:
                    continue

                # Check club limit (max 3)
                cand_club = teams_map.get(buy_cand.team_id, "UNK")
                current_club_cnt = my_club_counts.get(cand_club, 0)
                if cand_club == out_club:
                    new_club_cnt = current_club_cnt
                else:
                    new_club_cnt = current_club_cnt + 1
                if new_club_cnt > 3:
                    continue

                # Calculate xP differential
                buy_xp = 0.0
                proj = self.db.query(PlayerProjection).filter(
                    PlayerProjection.player_id == buy_cand.id,
                    PlayerProjection.gameweek_id == current_gw,
                    PlayerProjection.source == "internal"
                ).first()
                if proj:
                    buy_xp = proj.expected_points

                xp_diff = round(buy_xp - out_p["gw_xp"], 2)
                if xp_diff > best_gain:
                    best_gain = xp_diff
                    best_transfer = {
                        "sell": {
                            "id": out_p["id"],
                            "web_name": out_p["web_name"],
                            "position": out_p["element_type"],
                            "team_name": out_p["team_name"],
                            "now_cost_str": out_p["now_cost_str"],
                            "gw_xp": out_p["gw_xp"]
                        },
                        "buy": {
                            "id": buy_cand.id,
                            "web_name": buy_cand.web_name,
                            "position": buy_cand.element_type,
                            "team_name": cand_club,
                            "now_cost_str": f"£{buy_cand.now_cost / 10.0:.1f}m",
                            "gw_xp": buy_xp
                        },
                        "bank_after_str": f"£{(user_bank - cost_diff) / 10.0:.1f}m",
                        "gw_xp_gain": xp_diff,
                        "is_financially_legal": True,
                        "reason": f"Replacing {out_p['web_name']} ({out_p['now_cost_str']}) with {buy_cand.web_name} (£{buy_cand.now_cost / 10.0:.1f}m) yields +{xp_diff:.2f} xP gain within available £{user_bank / 10.0:.1f}m bank."
                    }

        return {
            "current_gw": current_gw,
            "my_squad_cost_str": my_squad["total_cost_str"],
            "my_squad_bank_str": my_squad["bank_str"],
            "optimal_squad_cost_str": optimal_result.get("total_cost_str", "N/A"),
            "my_squad_starting_xp": my_squad["starting_xi_xp"],
            "optimal_squad_starting_xp": optimal_result.get("current_gw_starting_xi_xp", 0.0),
            "xp_gain": round(optimal_result.get("current_gw_starting_xi_xp", 0.0) - my_squad["starting_xi_xp"], 2),
            "actionable_1ft_recommendation": best_transfer,
            "recommended_transfer": best_transfer,
            "transfers_required_count": len(transfers_out),
            "transfers_out": transfers_out,
            "transfers_in": transfers_in,
            "keeps_count": len(keeps),
            "bench_changes": bench_changes
        }
