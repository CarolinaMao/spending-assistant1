
# Individual Contribution Documentation: Core Logic & System Integration

**Developer**: [Your Name]  
**Responsibility**: Design and implementation of the Analytics Engine and Automated Alerting System.

---

## 1. Module: `analytics.py` (The Computational Engine)

I independently developed this module to handle all statistical heavy-lifting. It contains the pure mathematical logic required to transform transaction JSON data into meaningful financial metrics.

### Function-Level Documentation

#### `parse_date(date_str: str) -> datetime`
- **Input**: A string in `YYYY-MM-DD` format.
- **Process**: Uses `datetime.strptime` for strict ISO 8601 conversion.
- **Validation**: Acts as a foundation for all time-series calculations in the engine.

#### `filter_by_date(transactions: list, start: datetime, end: datetime) -> list`
- **Input**: The full transaction ledger and optional date bounds.
- **Process**: Iterates through the list, converting strings to objects via `parse_date` to perform inclusive range comparisons.
- **Returns**: A filtered subset of transactions.

#### `get_totals_by_category(transactions: list, start: datetime, end: datetime) -> dict`
- **Input**: Transaction list and time window.
- **Process**: Utilizes a `defaultdict(float)` to aggregate spending. It groups and sums the converted HKD amounts by their category labels.
- **Output**: `{category_name: total_amount_hkd}`.

#### `get_top_n_categories(transactions: list, n: int = 3) -> list[tuple]`
- **Input**: Data ledger and desired rank count.
- **Process**: Calls `get_totals_by_category`, sorts the result descending by value, and calculates the percentage share for each of the top `n` items.
- **Output**: Sorted list of `(category, amount, percentage)`.

#### `get_spending_trends(transactions: list) -> tuple[float, float]`
- **Process**: Defines two windows (last 7 days and last 30 days from `now`). It calculates the daily average for both.
- **Logic**: Used to determine if recent spending behavior is deviating from the monthly baseline.

#### `get_daily_totals_by_category(transactions: list, category: str) -> dict`
- **Process**: Filters data for a specific category and maps every unique date to its total spending.
- **Purpose**: Critical helper function for streak detection and heatmap intensity.

#### `get_consecutive_overspend(transactions: list, category: str, daily_cap: float) -> int`
- **Process**: Analyzes the daily spending timeline for a category. Starting from the most recent entry, it counts backwards until it hits a day that is *under* the cap.
- **Purpose**: Identifies behavioral patterns rather than isolated incidents.

#### `linear_forecast(transactions: list) -> float`
- **Algorithm**: Implements a linear projection: `(Total Spent This Month / Days Passed) * Days In Month`.
- **Purpose**: Predicts the end-of-month financial outcome to allow for proactive budget adjustments.

#### `spending_heatmap(transactions: list) -> dict`
- **Logic**: Normalizes daily spending against the monthly average.
- **Mapping**: Assigns Unicode block density based on intensity: `░` (<50%), `▒` (50-100%), `▓` (100-150%), `█` (>150%).

#### `get_spending_outliers(transactions: list, top_percent=0.05) -> list`
- **Logic**: Sorts the entire ledger by amount and applies a percentage-based slice to isolate the highest-value transactions.
- **Purpose**: Automated detection of "Major Expenses."

---

## 2. Module: `alerts.py` (The Budget Auditor)

I designed this module to enforce financial constraints. It transforms the output of the Analytics Engine into actionable "Red Flags."

### Function-Level Documentation

#### `check_daily_caps(transactions, budget_rules) -> list`
- **Logic**: Filters today's transactions and compares the category sums against the user-defined `daily_cap`.
- **Output**: Generates `daily_exceeded` alert dictionaries with real-time spending vs. limit data.

#### `check_percentage_thresholds(transactions, budget_rules) -> list`
- **Logic**: Evaluates long-term category weight. If a category's share of total historical spending exceeds the allowed percentage (e.g., Entertainment > 20%), an alert is raised.

#### `check_consecutive_overspend(transactions, budget_rules) -> list`
- **Logic**: Monitors habitual overspending by triggering an alert only if a category's `consecutive_overspend` count is $\ge 3$.

#### `check_forecast_alerts(transactions, budget_rules) -> list`
- **Logic**: Proactive monitoring. It runs the `linear_forecast` and compares the projected total against the global monthly budget.

#### `check_uncategorized(transactions, categories) -> list`
- **Logic**: A data integrity check that identifies transactions with missing categories or labels that no longer exist in the system configuration.

#### `get_all_alerts(transactions, budget_rules, categories) -> list`
- **Logic**: The central hub for alerting. It aggregates results from all five check functions into a single sorted list for display.

---

## 3. System Integration (Modifications to Main/Display)

To support my core modules, I implemented necessary updates to the integration layer:

### `main.py` Updates
- **`statistics_flow()` Integration**: I expanded the statistics menu to include a dedicated entry for **"Major Expenses (Top 5%)"**, linking the UI to the outlier detection logic.
- **`pause()` Patching**: I optimized the pausing mechanism to handle library version discrepancies (specifically `questionary` attribute errors), ensuring the application doesn't crash between menu transitions.

### `display.py` Updates
- **`print_outliers(transactions)`**: Created a custom rendering function using `Rich.Table`. I configured the table to highlight dates in Magenta and amounts in Green for high-value transaction clarity.
- **Unified Alert Display**: Updated the dashboard to call `get_all_alerts` immediately after any transaction modification, providing the user with an instant "Financial Health Check."

---

## 4. Engineering Standards

- **PEP 257 Compliance**: Every function I developed or integrated is documented with professional English Docstrings.
- **Circular Import Prevention**: Applied local imports (inside functions) where necessary to maintain a clean dependency graph.
- **Data Robustness**: Implemented fallback values (e.g., returning `0.0` or empty lists) to ensure the UI remains stable even when the user has no transaction history.