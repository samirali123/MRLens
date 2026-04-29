from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def print_header(username: str, map_name: str, enemy_heroes: list[str]):
    console.print(Panel(
        f"[bold cyan]Player:[/] {username}\n"
        f"[bold cyan]Map:[/]    {map_name}\n"
        f"[bold cyan]Enemies:[/] {', '.join(enemy_heroes)}",
        title="[bold yellow]Marvel Rivals Counter-Pick Engine[/]",
        border_style="yellow",
    ))


def print_recommendation(recommendation: str):
    console.print(Panel(
        recommendation,
        title="[bold green]Recommended Picks[/]",
        border_style="green",
    ))


def print_hero_stats(stats: dict, title: str = "Your Hero Stats"):
    table = Table(title=title, box=box.SIMPLE_HEAVY, show_lines=False)
    table.add_column("Hero", style="cyan", no_wrap=True)
    table.add_column("Games", justify="right")
    table.add_column("Win Rate", justify="right")
    for hero, data in sorted(stats.items(), key=lambda x: x[1]["win_rate"], reverse=True)[:15]:
        wr = data["win_rate"]
        color = "green" if wr >= 0.55 else "red" if wr < 0.45 else "yellow"
        table.add_row(hero, str(data["games"]), f"[{color}]{wr:.1%}[/]")
    console.print(table)


def print_timing(timings: dict[str, float]):
    console.print("\n[dim]--- Timing ---[/dim]")
    for label, seconds in timings.items():
        console.print(f"[dim][INFO] {label}: {seconds:.1f}s[/dim]")
    total = sum(timings.values())
    console.print(f"[dim][INFO] Total: {total:.1f}s[/dim]")


def print_error(message: str):
    console.print(f"[bold red][ERROR][/] {message}")


def print_info(message: str):
    console.print(f"[dim][INFO][/dim] {message}")
