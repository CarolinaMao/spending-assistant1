import calendar
import os
from datetime import datetime

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from analytics import get_spending_outliers

from alerts import get_all_alerts
from analytics import (
    filter_by_date,
    get_daily_totals_by_category,
    get_savings_progress,
    get_spending_trends,
    get_top_n_categories,
    get_totals_by_category,
    linear_forecast,
    spending_heatmap,
)

console = Console()


def print_header():
    t = Text(justify="center")
    t.append("💰  Personal Budget Assistant\n", style="bold cyan")
    t.append("COMP1110 B12  ·  HKU  ·  2026", style="dim")
    console.print(Panel(t, border_style="cyan", padding=(0, 4)))


def print_transaction_table(transactions, title="Transaction History"):
    if not transactions:
        console.print(Panel("[dim]No transactions found.[/dim]", title=title, border_style="dim"))
        return
    from data import load_config
    rates = load_config().get("currencies", {})

    table = Table(title=title, box=box.ROUNDED, show_lines=False, expand=False)
    table.add_column("ID", style="cyan", width=4, justify="right")
    table.add_column("Date", style="magenta", width=12)
    table.add_column("Amount", style="green", justify="right", min_width=26, no_wrap=True)
    table.add_column("Category", style="yellow", width=14)
    table.add_column("Description")
    for t in sorted(transactions, key=lambda x: x["date"], reverse=True):
        cur = t.get("currency", "HKD")
        if cur == "HKD":
            amt_str = f"HK${t['amount']:.2f}"
        else:
            hkd = t["amount"] * rates.get(cur, 1.0)
            amt_str = f"{cur} {t['amount']:.2f} [dim]≈ HK${hkd:.2f}[/dim]"
        table.add_row(
            str(t["id"]),
            t["date"],
            amt_str,
            t["category"],
            t["description"],
        )
    console.print(table)


def print_statistics(transactions, period_label="All Time"):
    totals = get_totals_by_category(transactions)
    total = sum(totals.values())
    if not totals:
        console.print(Panel("[dim]No spending data.[/dim]", title="Statistics"))
        return
    table = Table(title=f"Spending by Category — {period_label}", box=box.ROUNDED, expand=False)
    table.add_column("Category", style="cyan")
    table.add_column("Amount", style="green", justify="right")
    table.add_column("Bar", min_width=22, no_wrap=True)
    table.add_column("%", justify="right", width=7)
    for cat, amt in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        pct = (amt / total * 100) if total > 0 else 0
        filled = int(pct / 5)
        bar = "█" * filled + "░" * (20 - filled)
        color = "red" if pct > 50 else "yellow" if pct > 30 else "green"
        table.add_row(cat, f"HK${amt:.2f}", f"[{color}]{bar}[/{color}]", f"{pct:.1f}%")
    console.print(table)
    console.print(f"[bold]  Total: HK${total:.2f}[/bold]\n")


def print_top_categories(transactions, n=3):
    top = get_top_n_categories(transactions, n)
    if not top:
        console.print("[dim]No data.[/dim]")
        return
    medals = ["🥇", "🥈", "🥉"]
    table = Table(title=f"Top {n} Spending Categories", box=box.SIMPLE_HEAVY, expand=False)
    table.add_column("", width=3)
    table.add_column("Category", style="bold")
    table.add_column("Amount", style="green", justify="right")
    table.add_column("Share", justify="right")
    for i, (cat, amt, pct) in enumerate(top):
        icon = medals[i] if i < 3 else f"{i+1}."
        table.add_row(icon, cat, f"HK${amt:.2f}", f"{pct:.1f}%")
    console.print(table)


def print_trends(transactions):
    avg_7, avg_30 = get_spending_trends(transactions)
    table = Table(title="Spending Trends (7d vs 30d)", box=box.SIMPLE_HEAVY, show_header=False, expand=False)
    table.add_column("Label", style="dim", width=16)
    table.add_column("Value", style="bold")
    table.add_row("7-day avg", f"HK${avg_7:.2f}/day")
    table.add_row("30-day avg", f"HK${avg_30:.2f}/day")
    if avg_30 > 0:
        diff = (avg_7 - avg_30) / avg_30 * 100
        if avg_7 > avg_30:
            trend = f"[red]⬆  +{diff:.1f}%  (spending more)[/red]"
        elif avg_7 < avg_30:
            trend = f"[green]⬇  {diff:.1f}%  (spending less)[/green]"
        else:
            trend = "[yellow]→  No change[/yellow]"
    else:
        trend = "[dim]Not enough data[/dim]"
    table.add_row("Trend", trend)
    console.print(table)


def print_alerts(alerts):
    if not alerts:
        console.print(Panel("[green]✅  All clear — no active alerts.[/green]", title="Budget Alerts", border_style="green"))
        return
    content = Text()
    for a in alerts:
        if a["type"] in ("daily_exceeded", "pct_exceeded", "consecutive_overspend"):
            content.append(f"🔴  {a['message']}\n", style="bold red")
        else:
            content.append(f"🟡  {a['message']}\n", style="bold yellow")
    console.print(Panel(content, title="⚠️  Budget Alerts", border_style="red"))


def print_budget_bars(transactions, budget_rules):
    if not budget_rules:
        console.print("[dim]No budget rules set.[/dim]")
        return
    today = datetime.now().strftime("%Y-%m-%d")
    table = Table(title="Today's Budget Progress", box=box.SIMPLE, expand=False)
    table.add_column("Category", style="cyan")
    table.add_column("Progress", min_width=22, no_wrap=True)
    table.add_column("Spent", justify="right", style="green")
    table.add_column("Limit", justify="right")
    table.add_column("%", justify="right", width=7)
    for rule in budget_rules:
        if "daily_cap" not in rule:
            continue
        cat = rule["category"]
        cap = rule["daily_cap"]
        daily = get_daily_totals_by_category(transactions, cat)
        spent = daily.get(today, 0)
        pct = (spent / cap * 100) if cap > 0 else 0
        filled = min(int(pct / 5), 20)
        bar = "█" * filled + "░" * (20 - filled)
        color = "red" if pct >= 100 else "yellow" if pct >= 80 else "green"
        table.add_row(
            cat,
            f"[{color}]{bar}[/{color}]",
            f"HK${spent:.2f}",
            f"HK${cap:.2f}",
            f"[{color}]{pct:.1f}%[/{color}]",
        )
    console.print(table)


def print_budget_rules(budget_rules):
    if not budget_rules:
        console.print("[dim]No budget rules set.[/dim]")
        return
    table = Table(title="Budget Rules", box=box.ROUNDED, expand=False)
    table.add_column("Category", style="cyan")
    table.add_column("Daily Cap", justify="right", style="green")
    table.add_column("Monthly Cap", justify="right", style="green")
    table.add_column("% Threshold", justify="right")
    for rule in budget_rules:
        table.add_row(
            rule["category"],
            f"HK${rule['daily_cap']:.2f}" if "daily_cap" in rule else "—",
            f"HK${rule['monthly_cap']:.2f}" if "monthly_cap" in rule else "—",
            f"{rule['pct_threshold']}%" if "pct_threshold" in rule else "—",
        )
    console.print(table)


def print_savings_goal(transactions, config):
    goal = config.get("savings_goal", 0)
    income = config.get("income", 0)
    if goal <= 0 or income <= 0:
        console.print(Panel("[dim]Set income and savings goal in Settings to track progress.[/dim]", border_style="dim"))
        return
    spent, remaining, savings = get_savings_progress(transactions, goal, income)
    pct = max(0, min(100, (savings / goal * 100) if goal > 0 else 0))
    filled = int(pct / 5)
    bar = "█" * filled + "░" * (20 - filled)
    color = "green" if savings >= goal else "yellow" if savings > 0 else "red"
    table = Table(title="💰 Savings Goal Progress", box=box.SIMPLE_HEAVY, show_header=False, expand=False)
    table.add_column("Label", style="dim", width=18)
    table.add_column("Value", style="bold")
    table.add_row("Monthly Income", f"HK${income:.2f}")
    table.add_row("Total Spent", f"HK${spent:.2f}")
    table.add_row("Remaining", f"HK${remaining:.2f}")
    table.add_row("Savings Goal", f"HK${goal:.2f}")
    table.add_row("Progress", f"[{color}]{bar}[/{color}]  {pct:.1f}%")
    status = "[green]✅ Goal achieved![/green]" if savings >= goal else f"[yellow]Need HK${(goal - savings):.2f} more[/yellow]"
    table.add_row("Status", status)
    console.print(table)


def print_forecast(transactions):
    forecast = linear_forecast(transactions)
    now = datetime.now()
    table = Table(title="📈 End-of-Month Spending Forecast", box=box.SIMPLE_HEAVY, show_header=False, expand=False)
    table.add_column("Label", style="dim", width=20)
    table.add_column("Value", style="bold")
    table.add_row("Based on", f"{now.day} days of data")
    table.add_row("Projected total", f"[cyan]HK${forecast:.2f}[/cyan]")
    console.print(table)


def print_heatmap(transactions):
    heatmap = spending_heatmap(transactions)
    if not heatmap:
        console.print("[dim]No spending data for current month.[/dim]")
        return
    now = datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    first_day = calendar.weekday(now.year, now.month, 1)

    console.print(f"\n[bold]📅  {now.strftime('%B %Y')} — Spending Heatmap[/bold]")
    console.print("[dim]░ low   ▒ medium   ▓ high   █ very high   · no spending[/dim]\n")

    COLOR = {"·": "dim", "░": "green", "▒": "yellow", "▓": "red", "█": "bold red"}
    DAY_NAMES = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1), expand=False)
    for day_name in DAY_NAMES:
        table.add_column(day_name, width=3, justify="center", no_wrap=True)

    row = [""] * first_day
    for day in range(1, days_in_month + 1):
        date_str = f"{now.year}-{now.month:02d}-{day:02d}"
        sym, _ = heatmap.get(date_str, ("·", 0))
        c = COLOR.get(sym, "dim")
        row.append(f"[{c}]{sym}[/{c}]")
        if len(row) == 7:
            table.add_row(*row)
            row = []
    if row:
        while len(row) < 7:
            row.append("")
        table.add_row(*row)

    console.print(table)
    console.print()

def print_outliers(transactions):
    outliers = get_spending_outliers(transactions)
    if not outliers:
        return
    table = Table(title="🚩 Significant Spendings (Top 5%)", box=box.SIMPLE_HEAVY, expand=False)
    table.add_column("Date", style="magenta")
    table.add_column("Category", style="yellow")
    table.add_column("Amount", style="green", justify="right")
    table.add_column("Description")
    for t in outliers:
        table.add_row(
            t["date"],
            t["category"],
            f"HK${t['amount']:.2f}",
            t["description"]
        )
    console.print(table)
def export_report(transactions, budget_rules, categories, config, filename=None):
    os.makedirs("outputs", exist_ok=True)
    filename = filename or f"outputs/report_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.txt"
    now = datetime.now()
    start = datetime(now.year, now.month, 1)
    monthly = filter_by_date(transactions, start, now)
    totals = get_totals_by_category(monthly)
    total = sum(totals.values())
    avg_7, avg_30 = get_spending_trends(transactions)
    top = get_top_n_categories(monthly, 3)
    alerts = get_all_alerts(transactions, budget_rules, categories)

    fc = Console(file=open(filename, "w", encoding="utf-8"), no_color=True, width=72)
    fc.print("=" * 72)
    fc.print("   MONTHLY SPENDING SUMMARY REPORT")
    fc.print(f"   {now.strftime('%B %Y')}   (generated {now.strftime('%Y-%m-%d %H:%M')})")
    fc.print("=" * 72)

    fc.print("\nSPENDING BY CATEGORY")
    fc.print("-" * 40)
    for cat, amt in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        pct = (amt / total * 100) if total > 0 else 0
        fc.print(f"  {cat:<16} HK${amt:>8.2f}   {pct:>5.1f}%")
    fc.print(f"  {'TOTAL':<16} HK${total:>8.2f}")

    fc.print("\nSPENDING TRENDS")
    fc.print("-" * 40)
    fc.print(f"  7-day avg:    HK${avg_7:.2f}/day")
    fc.print(f"  30-day avg:   HK${avg_30:.2f}/day")
    if avg_30 > 0:
        diff = (avg_7 - avg_30) / avg_30 * 100
        fc.print(f"  Trend:        {'+' if diff >= 0 else ''}{diff:.1f}%")

    fc.print("\nTOP 3 CATEGORIES")
    fc.print("-" * 40)
    for i, (cat, amt, pct) in enumerate(top, 1):
        fc.print(f"  {i}. {cat}: HK${amt:.2f} ({pct:.1f}%)")

    fc.print("\nACTIVE ALERTS")
    fc.print("-" * 40)
    if alerts:
        for a in alerts:
            fc.print(f"  • {a['message']}")
    else:
        fc.print("  No active alerts.")

    fc.print("\n" + "=" * 72)
    fc.file.close()
    return filename
