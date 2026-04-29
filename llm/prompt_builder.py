LOW_SAMPLE_THRESHOLD = 10


def _fmt_wr(wr) -> str:
    return f"{float(wr):.1%}" if wr is not None else "N/A"


def _format_personal_vs_community(pvc: dict) -> str:
    lines = [f"{'Hero':<22} {'Personal':>10} {'Community':>11} {'Delta':>8} {'Games':>6}"]
    lines.append("─" * 60)
    for hero, d in sorted(pvc.items(), key=lambda x: x[1].get("personal", 0), reverse=True)[:12]:
        flag = " [LOW]" if d["games"] < LOW_SAMPLE_THRESHOLD else ""
        delta_str = f"{d['delta']:+.1%}" if d["delta"] is not None else "N/A"
        lines.append(
            f"{hero:<22} {_fmt_wr(d['personal']):>10} {_fmt_wr(d['community']):>11} {delta_str:>8} {d['games']:>6}{flag}"
        )
    return "\n".join(lines)


def _format_map_winrates(map_wrs: dict) -> str:
    if not map_wrs:
        return "  No personal map data yet — play more games on this map."
    lines = []
    for hero, wr in sorted(map_wrs.items(), key=lambda x: x[1], reverse=True)[:10]:
        lines.append(f"  {hero:<22} {float(wr):.1%}")
    return "\n".join(lines)


def _format_synergies(active_synergies: list[dict]) -> str:
    if not active_synergies:
        return "  No active synergy data for current allies (need more games together)."
    lines = []
    for s in sorted(active_synergies, key=lambda x: x.get("delta", 0) or 0, reverse=True)[:6]:
        delta_str = f"{s['delta']:+.1%}" if s.get("delta") else ""
        lines.append(f"  Play {s['hero']} + {s['ally']} already on team → {s['win_rate']:.1%} WR ({s['games']}g) {delta_str}")
    return "\n".join(lines)


def _format_community_map(community_map: dict) -> str:
    if not community_map:
        return "  No community data for this map yet."
    lines = []
    for hero, wr in sorted(community_map.items(), key=lambda x: x[1], reverse=True)[:10]:
        lines.append(f"  {hero:<22} {float(wr):.1%}")
    return "\n".join(lines)


def build_context(
    username: str,
    player_rank: str,
    map_name: str,
    side: str,
    ally_heroes: list[str],
    comp_archetype: str,
    personal_vs_community: dict,
    map_winrates: dict,
    community_map_winrates: dict,
    active_synergies: list[dict],
) -> str:
    ally_str = ", ".join(ally_heroes) if ally_heroes else "Unknown"
    side_str = side.capitalize() if side != "unknown" else "Unknown"

    return f"""You are a Marvel Rivals coach advising {username}. Recommend their top 3 hero picks right now.
Ground every reason in the specific data below. Be direct and concise.

MAP: {map_name}
SIDE: {side_str}
CURRENT ALLIES: {ally_str}

PERSONAL WIN RATES — this map{f' ({side_str})' if side != 'unknown' else ''}:
{_format_map_winrates(map_winrates)}

PERSONAL SYNERGIES ACTIVE WITH CURRENT ALLIES:
(Heroes where {username} wins more when a specific current ally is on the team)
{_format_synergies(active_synergies)}

OVERALL PERSONAL vs COMMUNITY WIN RATES (rank: {player_rank}):
{_format_personal_vs_community(personal_vs_community)}
[LOW] = fewer than {LOW_SAMPLE_THRESHOLD} games — treat cautiously

COMMUNITY WIN RATES on {map_name} at {player_rank}:
{_format_community_map(community_map_winrates)}

DECISION RULES (apply in this order):
1. Prioritize heroes {username} wins on THIS MAP on THIS SIDE — that is the strongest signal
2. If a hero activates a synergy with a current ally AND has good personal WR — highlight it
3. Avoid heroes already taken by allies
4. Flag positive personal vs community delta as a skill edge
5. If personal data is thin, fall back to community map win rates

Respond in exactly this format — no extra text:
1. [Hero Name] — [Reason]
2. [Hero Name] — [Reason]
3. [Hero Name] — [Reason]"""
