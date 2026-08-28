import logging
from typing import List, Dict, Any

logger = logging.getLogger("reconciled_minutes")

# Max physical starting slots per team for matchday lineup (in total team minutes)
MAX_TEAM_POSITION_MINUTES = {
    "GKP": 90.0,   # Exactly 1 GKP starts (90 mins total)
    "DEF": 360.0,  # Max 4 DEF starting slots (360 mins total)
    "MID": 450.0,  # Max 5 MID starting slots (450 mins total)
    "FWD": 270.0   # Max 3 FWD starting slots (270 mins total)
}

def reconcile_squad_minutes(player_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Reconcile baseline ML expected minutes across club position competition groups.
    Ensures mutually exclusive starting roles do not exceed physical matchday lineup capacity.
    """
    team_pos_groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for pdata in player_data_list:
        team_id = pdata.get("team_id")
        pos = pdata.get("position") or pdata.get("element_type")
        key = (team_id, pos)
        if key not in team_pos_groups:
            team_pos_groups[key] = []
        team_pos_groups[key].append(pdata)

    for (team_id, pos), group in team_pos_groups.items():
        max_allowed_mins = MAX_TEAM_POSITION_MINUTES.get(pos, 360.0)
        total_baseline_mins = sum(p.get("expected_minutes", 0.0) for p in group)

        if total_baseline_mins > max_allowed_mins and max_allowed_mins > 0:
            scale_factor = max_allowed_mins / total_baseline_mins
            for p in group:
                orig_mins = p.get("expected_minutes", 0.0)
                reconciled_mins = round(orig_mins * scale_factor, 1)
                p["expected_minutes_unconstrained"] = orig_mins
                p["expected_minutes"] = reconciled_mins
                p["used_reconciliation"] = True

                orig_p_start = p.get("p_start", 1.0)
                p["p_start"] = round(min(1.0, orig_p_start * scale_factor), 3)

    return player_data_list
