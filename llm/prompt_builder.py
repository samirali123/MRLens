LOW_SAMPLE_THRESHOLD = 10


def _format_hero_comparison(personal_vs_community: dict) -> str:
    lines = ["Hero | Personal WR | Community WR | Delta | Games"]
    lines.append("-" * 55)
    sorted_heroes = sorted(personal_vs_community.items(), key=lambda x: x[1].get("personal", 0), reverse=True)
    for hero, data in sorted_heroes[:15]:
        p_wr = f"{data['personal']:.1%}" if data["personal"] is not None else "N/A"
        c_wr = f"{data['community']:.1%}" if data["community"] is not None else "N/A"
        delta = f"{data['delta']:+.1%}" if data["delta"] is not None else "N/A"
        games = data["games"]
        flag = " [LOW SAMPLE]" if games < LOW_SAMPLE_THRESHOLD else ""
        lines.append(f"{hero:<20} {p_wr:<14} {c_wr:<14} {delta:<8} {games}{flag}")
    return "\n".join(lines)


def _format_archetype_winrates(archetype_winrates: dict) -> str:
    if not archetype_winrates:
        return "No historical data vs this comp type."
    lines = []
    for hero, stats in sorted(archetype_winrates.items(), key=lambda x: x[1]["win_rate"], reverse=True)[:10]:
        lines.append(f"  {hero}: {stats['win_rate']:.1%} ({stats['games']} games)")
    return "\n".join(lines)


def _format_enemy_signals(enemy_signals: dict, vulnerabilities: dict) -> str:
    lines = []
    for player, data in enemy_signals.items():
        worst = [f"{e['hero']} ({e['win_rate']:.0%} WR)" for e in data["worst_heroes"][:3]]
        if worst:
            lines.append(f"  {player} struggles against: {', '.join(worst)}")
    if vulnerabilities:
        top = list(vulnerabilities.items())[:5]
        lines.append(f"\n  Heroes exploiting MULTIPLE enemies: {', '.join(f'{h}({c})' for h, c in top)}")
    return "\n".join(lines) if lines else "  No enemy profile data available (private accounts or no DB history)."


def _format_map_winrates(map_winrates: dict) -> str:
    if not map_winrates:
        return "  No map-specific data available."
    lines = []
    for hero, wr in sorted(map_winrates.items(), key=lambda x: x[1], reverse=True)[:10]:
        lines.append(f"  {hero}: {wr:.1%}")
    return "\n".join(lines)


def build_context(
    username: str,
    player_rank: str,
    map_name: str,
    enemy_heroes: list[str],
    comp_archetype: str,
    personal_vs_community: dict,
    archetype_winrates: dict,
    enemy_signals: dict,
    enemy_vulnerabilities: dict,
    map_winrates: dict,
) -> str:
    return f"""You are a Marvel Rivals coach. Recommend the top 3 hero picks for this player.
For each pick give a 1-2 sentence reason grounded in the data below.

PLAYER: {username}
CURRENT RANK: {player_rank}
MAP: {map_name}
ENEMY COMP: {', '.join(enemy_heroes)}
COMP TYPE: {comp_archetype}

PLAYER'S TOP HEROES — personal win rate vs community win rate at {player_rank}:
(Format: Hero | Personal WR | Community WR | Delta | Games Played)
{_format_hero_comparison(personal_vs_community)}
Note: heroes with <{LOW_SAMPLE_THRESHOLD} games marked [LOW SAMPLE] — treat with caution

PLAYER WIN RATE VS {comp_archetype.upper()} COMPS HISTORICALLY:
{_format_archetype_winrates(archetype_winrates)}

ENEMY VULNERABILITIES (heroes each enemy loses most to):
{_format_enemy_signals(enemy_signals, enemy_vulnerabilities)}

MAP WIN RATES ON {map_name} (community, {player_rank} rank):
{_format_map_winrates(map_winrates)}

INSTRUCTIONS:
- Weight personal performance most heavily — a hero the player wins on beats a meta pick they struggle with
- Flag if a strong personal pick has a positive delta (they outperform community) — this is a skill edge
- If the player has low sample on their top options, lean more on community map data
- Consider how well the pick exploits enemy vulnerabilities

Respond in this exact format:
1. [Hero Name] — [Reason grounded in data]
2. [Hero Name] — [Reason grounded in data]
3. [Hero Name] — [Reason grounded in data]"""
