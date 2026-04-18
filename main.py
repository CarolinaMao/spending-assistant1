import questionary
from questionary import Separator, Style

from alerts import get_all_alerts
from analytics import filter_by_date
from data import (
    ensure_dirs,
    fetch_exchange_rates,
    get_next_id,
    load_budget_rules,
    load_config,
    load_transactions,
    save_budget_rules,
    save_config,
    save_transactions,
)
from datetime import datetime
from display import (
    console,
    export_report,
    print_alerts,
    print_budget_bars,
    print_budget_rules,
    print_forecast,
    print_outliers,
    print_header,
    print_heatmap,
    print_savings_goal,
    print_statistics,
    print_top_categories,
    print_transaction_table,
    print_trends,
)
from validator import validate_amount, validate_date, validate_description

STYLE = Style([
    ("pointer",     "fg:#00ff88 bold"),
    ("highlighted", "fg:#00ff88 bold"),
    ("question",    "bold"),
    ("answer",      "fg:#00ff88 bold"),
    ("separator",   "fg:#555555 italic"),
])

BACK = "↩   Back"

def _sep(label=""):
    return Separator(f"  {'─' * 2} {label} " if label else f"  {'─' * 44}")


def ask(prompt, default=""):
    result = questionary.text(prompt, default=default, style=STYLE).ask()
    if result is None:
        raise KeyboardInterrupt
    return result


def choose(prompt, choices):
    result = questionary.select(prompt, choices=choices, style=STYLE, pointer="❯").ask()
    if result is None:
        raise KeyboardInterrupt
    return result


def confirm(prompt, default=False):
    result = questionary.confirm(prompt, default=default, style=STYLE).ask()
    if result is None:
        raise KeyboardInterrupt
    return result


def pause():
    questionary.press_any_key_to_continue(style=STYLE).ask()


def add_transaction_flow():
    config = load_config()
    transactions = load_transactions()
    console.print("\n[bold cyan]➕  Add Transaction[/bold cyan]")

    while True:
        date_str = ask("Date (YYYY-MM-DD):", default=datetime.now().strftime("%Y-%m-%d"))
        if validate_date(date_str):
            break
        console.print("[red]Invalid date. Use YYYY-MM-DD.[/red]")

    while True:
        amount_str = ask("Amount:")
        valid, amount = validate_amount(amount_str)
        if valid:
            break
        console.print("[red]Must be a positive number.[/red]")

    currency = choose("Currency:", list(config["currencies"].keys()))
    if currency != config["default_currency"]:
        rate = config["currencies"][currency]
        console.print(f"[dim]≈ HK${amount * rate:.2f}[/dim]")

    category = choose("Category:", config["categories"] + ["Uncategorized"])

    while True:
        desc = ask("Description:")
        if validate_description(desc):
            break
        console.print("[red]Description cannot be empty.[/red]")

    txn = {
        "id": get_next_id(transactions),
        "date": date_str,
        "amount": amount,
        "currency": currency,
        "category": category,
        "description": desc.strip(),
    }
    transactions.append(txn)
    save_transactions(transactions)
    console.print(f"\n[green]✅  Transaction #{txn['id']} added.[/green]")

    budget_rules = load_budget_rules()
    triggered = [
        a for a in get_all_alerts(transactions, budget_rules, config["categories"])
        if a["type"] != "uncategorized"
    ]
    if triggered:
        print_alerts(triggered)
    print_budget_bars(transactions, budget_rules)


def view_transactions_flow():
    transactions = load_transactions()
    config = load_config()
    mode = choose("View mode:", [
        _sep("Browse"),
        "All Transactions",
        _sep("Filter"),
        "Filter by Date Range",
        "Filter by Category",
        "Search by Keyword",
        _sep(),
        BACK,
    ])
    if mode == BACK:
        return
    if mode == "All Transactions":
        print_transaction_table(transactions)
    elif mode == "Filter by Date Range":
        while True:
            start_str = ask("Start date (YYYY-MM-DD):")
            if validate_date(start_str):
                break
            console.print("[red]Invalid date.[/red]")
        while True:
            end_str = ask("End date (YYYY-MM-DD):", default=datetime.now().strftime("%Y-%m-%d"))
            if validate_date(end_str):
                break
            console.print("[red]Invalid date.[/red]")
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        filtered = filter_by_date(transactions, start, end)
        print_transaction_table(filtered, f"Transactions {start_str} → {end_str}")
    elif mode == "Filter by Category":
        cat = choose("Category:", config["categories"])
        filtered = [t for t in transactions if t["category"] == cat]
        print_transaction_table(filtered, f"{cat} Transactions")
    elif mode == "Search by Keyword":
        keyword = ask("Keyword:")
        filtered = [t for t in transactions if keyword.lower() in t["description"].lower()]
        print_transaction_table(filtered, f'Results for "{keyword}"')


def edit_delete_flow():
    transactions = load_transactions()
    if not transactions:
        console.print("[dim]No transactions.[/dim]")
        return
    print_transaction_table(transactions)

    while True:
        id_str = ask("Transaction ID to edit/delete (or 'q' to cancel):")
        if id_str.lower() == "q":
            return
        try:
            txn_id = int(id_str)
            txn = next((t for t in transactions if t["id"] == txn_id), None)
            if txn:
                break
            console.print(f"[red]ID {txn_id} not found.[/red]")
        except ValueError:
            console.print("[red]Enter a valid number.[/red]")

    action = choose(f"Action for #{txn_id}:", [
        "Edit Field",
        "Delete Transaction",
        _sep(),
        "Cancel",
    ])
    if action == "Cancel":
        return

    if action == "Delete Transaction":
        if confirm(f"Delete transaction #{txn_id}?"):
            transactions = [t for t in transactions if t["id"] != txn_id]
            save_transactions(transactions)
            console.print("[green]✅  Deleted.[/green]")

    elif action == "Edit Field":
        config = load_config()
        field = choose("Field to edit:", [
            "Date", "Amount", "Currency", "Category", "Description",
            _sep(),
            "Cancel",
        ])
        if field == "Cancel":
            return
        if field == "Date":
            while True:
                val = ask(f"New date (current: {txn['date']}):")
                if validate_date(val):
                    txn["date"] = val
                    break
                console.print("[red]Invalid date.[/red]")
        elif field == "Amount":
            while True:
                val = ask(f"New amount (current: {txn['amount']}):")
                valid, amt = validate_amount(val)
                if valid:
                    txn["amount"] = amt
                    break
                console.print("[red]Invalid amount.[/red]")
        elif field == "Currency":
            txn["currency"] = choose("Currency:", list(config["currencies"].keys()))
        elif field == "Category":
            txn["category"] = choose("Category:", config["categories"])
        elif field == "Description":
            while True:
                val = ask(f"New description (current: {txn['description']}):")
                if validate_description(val):
                    txn["description"] = val.strip()
                    break
                console.print("[red]Cannot be empty.[/red]")
        save_transactions(transactions)
        console.print("[green]✅  Updated.[/green]")


def statistics_flow():
    transactions = load_transactions()
    budget_rules = load_budget_rules()
    action = choose("Statistics:", [
        _sep("Overview"),
        "Category Totals — Current Month",
        "Category Totals — All Time",
        "Top 3 Categories",
        "Major Expenses (Top 5%)",
        _sep("Trends & Forecast"),
        "Spending Trends (7d vs 30d)",
        "Spending Forecast",
        _sep("Visuals"),
        "Budget Progress Bars",
        "Spending Heatmap",
        _sep(),
        BACK,
    ])
    if action == BACK:
        return
    if action == "Category Totals — Current Month":
        now = datetime.now()
        filtered = filter_by_date(transactions, datetime(now.year, now.month, 1), now)
        print_statistics(filtered, now.strftime("%B %Y"))
    elif action == "Category Totals — All Time":
        print_statistics(transactions)
    elif action == "Top 3 Categories":
        print_top_categories(transactions)
    elif action == "Major Expenses (Top 5%)":
        print_outliers(transactions)
    elif action == "Spending Trends (7d vs 30d)":
        print_trends(transactions)
    elif action == "Budget Progress Bars":
        print_budget_bars(transactions, budget_rules)
    elif action == "Spending Forecast":
        print_forecast(transactions)
    elif action == "Spending Heatmap":
        print_heatmap(transactions)


def alerts_flow():
    transactions = load_transactions()
    budget_rules = load_budget_rules()
    config = load_config()
    alerts = get_all_alerts(transactions, budget_rules, config["categories"])
    print_alerts(alerts)


def manage_budget_rules_flow():
    budget_rules = load_budget_rules()
    config = load_config()
    action = choose("Budget Rules:", [
        "View Rules",
        "Add / Update Rule",
        "Delete Rule",
        _sep(),
        BACK,
    ])
    if action == BACK:
        return

    if action == "View Rules":
        print_budget_rules(budget_rules)

    elif action == "Add / Update Rule":
        cat = choose("Category:", config["categories"])
        rule = {"category": cat}
        if confirm("Set daily cap?"):
            while True:
                val = ask("Daily cap (HKD):")
                valid, amt = validate_amount(val)
                if valid:
                    rule["daily_cap"] = amt
                    break
                console.print("[red]Invalid.[/red]")
        if confirm("Set monthly cap?"):
            while True:
                val = ask("Monthly cap (HKD):")
                valid, amt = validate_amount(val)
                if valid:
                    rule["monthly_cap"] = amt
                    break
                console.print("[red]Invalid.[/red]")
        if confirm("Set % threshold?"):
            while True:
                val = ask("Max % of total spending (0–100):")
                try:
                    pct = float(val)
                    if 0 < pct <= 100:
                        rule["pct_threshold"] = pct
                        break
                    console.print("[red]Must be 1–100.[/red]")
                except ValueError:
                    console.print("[red]Invalid.[/red]")
        idx = next((i for i, r in enumerate(budget_rules) if r["category"] == cat), None)
        if idx is not None:
            budget_rules[idx] = rule
        else:
            budget_rules.append(rule)
        save_budget_rules(budget_rules)
        console.print("[green]✅  Rule saved.[/green]")

    elif action == "Delete Rule":
        if not budget_rules:
            console.print("[dim]No rules to delete.[/dim]")
            return
        cat = choose("Delete rule for:", [r["category"] for r in budget_rules])
        if confirm(f"Delete rule for '{cat}'?"):
            save_budget_rules([r for r in budget_rules if r["category"] != cat])
            console.print("[green]✅  Deleted.[/green]")


def manage_categories_flow():
    config = load_config()
    action = choose("Categories:", [
        "View",
        "Add",
        "Remove",
        _sep(),
        BACK,
    ])
    if action == BACK:
        return
    if action == "View":
        console.print("[bold]Categories:[/bold]")
        for cat in config["categories"]:
            console.print(f"  • {cat}")
    elif action == "Add":
        name = ask("New category name:").strip()
        if not name:
            return
        if name in config["categories"]:
            console.print("[yellow]Already exists.[/yellow]")
        else:
            config["categories"].append(name)
            save_config(config)
            console.print(f"[green]✅  Added '{name}'.[/green]")
    elif action == "Remove":
        if not config["categories"]:
            console.print("[dim]No categories.[/dim]")
            return
        cat = choose("Remove:", config["categories"])
        if confirm(f"Remove '{cat}'?"):
            config["categories"].remove(cat)
            save_config(config)
            console.print(f"[green]✅  Removed '{cat}'.[/green]")


def settings_flow():
    config = load_config()
    action = choose("Settings:", [
        _sep("Income & Goals"),
        "Set Monthly Income",
        "Set Savings Goal",
        "View Savings Progress",
        _sep("Currencies"),
        "Currency Exchange Rates",
        _sep(),
        BACK,
    ])
    if action == BACK:
        return

    if action == "Set Monthly Income":
        while True:
            val = ask(f"Monthly income in HKD (current: HK${config.get('income', 0):.2f}):")
            valid, amt = validate_amount(val)
            if valid:
                config["income"] = amt
                save_config(config)
                console.print("[green]✅  Saved.[/green]")
                break
            console.print("[red]Invalid.[/red]")

    elif action == "Set Savings Goal":
        while True:
            val = ask(f"Monthly savings goal in HKD (current: HK${config.get('savings_goal', 0):.2f}):")
            valid, amt = validate_amount(val)
            if valid:
                config["savings_goal"] = amt
                save_config(config)
                console.print("[green]✅  Saved.[/green]")
                break
            console.print("[red]Invalid.[/red]")

    elif action == "View Savings Progress":
        print_savings_goal(load_transactions(), config)

    elif action == "Currency Exchange Rates":
        console.print("[bold]Current rates (1 unit → HKD):[/bold]")
        for cur, rate in config["currencies"].items():
            console.print(f"  {cur}: {rate}")
        if confirm("Update a rate?"):
            cur = choose("Currency:", list(config["currencies"].keys()))
            while True:
                val = ask(f"1 {cur} = ? HKD:")
                try:
                    rate = float(val)
                    if rate > 0:
                        config["currencies"][cur] = rate
                        save_config(config)
                        console.print("[green]✅  Updated.[/green]")
                        break
                    console.print("[red]Must be positive.[/red]")
                except ValueError:
                    console.print("[red]Invalid.[/red]")


def export_flow():
    transactions = load_transactions()
    budget_rules = load_budget_rules()
    config = load_config()
    filename = export_report(transactions, budget_rules, config["categories"], config)
    console.print(f"\n[green]✅  Report saved → [bold]{filename}[/bold][/green]")


HANDLERS = {
    "➕   Add Transaction":            add_transaction_flow,
    "📋   View / Filter Transactions":  view_transactions_flow,
    "✏️    Edit / Delete Transaction":   edit_delete_flow,
    "📊   Statistics & Analytics":      statistics_flow,
    "⚠️    Check Budget Alerts":         alerts_flow,
    "💰   Budget Rules":                manage_budget_rules_flow,
    "🏷️    Manage Categories":           manage_categories_flow,
    "⚙️    Settings":                    settings_flow,
    "📄   Export Summary Report":       export_flow,
    "🚪   Exit":                         None,
}

MAIN_MENU = [
    _sep("Transactions"),
    "➕   Add Transaction",
    "📋   View / Filter Transactions",
    "✏️    Edit / Delete Transaction",
    _sep("Analytics"),
    "📊   Statistics & Analytics",
    "⚠️    Check Budget Alerts",
    _sep("Management"),
    "💰   Budget Rules",
    "🏷️    Manage Categories",
    "⚙️    Settings",
    _sep(),
    "📄   Export Summary Report",
    "🚪   Exit",
]


def main():
    ensure_dirs()
    console.print("[dim]Fetching live exchange rates...[/dim] ", end="")
    rates = fetch_exchange_rates()
    if rates:
        cfg = load_config()
        cfg["currencies"] = rates
        save_config(cfg)
        console.print("[green]✓[/green]")
    else:
        console.print("[yellow]offline — using cached rates[/yellow]")

    try:
        while True:
            console.clear()
            print_header()
            choice = questionary.select("", choices=MAIN_MENU, style=STYLE, pointer="❯").ask()
            if choice is None or choice == "🚪   Exit":
                console.print("\n[bold cyan]Goodbye! 👋[/bold cyan]\n")
                break
            console.print()
            HANDLERS[choice]()
            console.print()
            pause()
    except KeyboardInterrupt:
        console.print("\n[bold cyan]Goodbye! 👋[/bold cyan]\n")


if __name__ == "__main__":
    main()
