"""
Dynamic ASCII representation for Cron schedules.
Free functions that generate next execution times and visual ASCII charts.
Integrates with the existing bw.cron runner.
"""

import datetime

import cron_converter

from bw.settings import TIMEZONE


def get_next_executions(
    cron_str: str,
    count: int = 5,
    start_time: datetime.datetime | None = None,
) -> list[datetime.datetime]:
    """
    Generate a list of the next N execution times for a cron expression.

    Args:
        cron_str: Standard 5-field cron string (e.g. "*/15 * * * *").
        count: How many future execution times to return (default 5).
        start_time: Reference datetime to start from (default: now in TIMEZONE).

    Returns:
        A list of datetime objects sorted chronologically.

    Example:
        >>> get_next_executions("0 9 * * 1-5", count=3)
        [datetime(2026, 8, 28, 9, 0), datetime(2026, 8, 31, 9, 0), datetime(2026, 9, 1, 9, 0)]
    """
    if start_time is None:
        start_time = datetime.datetime.now(tz=TIMEZONE)

    schedule = cron_converter.Cron(cron_str).schedule(start_date=start_time)
    executions: list[datetime.datetime] = []
    current = start_time

    for _ in range(count):
        nxt = schedule.next()
        # Guard against duplicate or stuck schedules
        if nxt <= current:
            break
        executions.append(nxt)
        current = nxt

    return executions


def _expand_cron_field(field: str, min_val: int, max_val: int) -> set[int]:
    """Expand a single cron field into a set of matching integers."""
    values: set[int] = set()
    for part in field.split(','):
        part = part.strip()
        if part == '*':
            values.update(range(min_val, max_val + 1))
        elif '/' in part:
            base, step = part.split('/', 1)
            step_val = int(step)
            start = min_val if base == '*' else int(base)
            values.update(range(start, max_val + 1, step_val))
        elif '-' in part:
            start, end = map(int, part.split('-', 1))
            values.update(range(start, end + 1))
        else:
            values.add(int(part))
    return values


def _humanize_delta(delta: datetime.timedelta) -> str:
    """Convert a timedelta into a short human-readable string."""
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return f'{total_seconds}s'
    if total_seconds < 3600:
        return f'{total_seconds // 60}m'
    if total_seconds < 86400:
        return f'{total_seconds // 3600}h {(total_seconds % 3600) // 60}m'
    return f'{total_seconds // 86400}d {(total_seconds % 86400) // 3600}h'


def ascii_cron_schedule(
    cron_str: str,
    next_count: int = 5,
    start_time: datetime.datetime | None = None,
    title: str = 'Cron Schedule',
) -> str:
    """
    Build a dynamic ASCII chart showing a cron schedule overview.

    Args:
        cron_str: Standard 5-field cron string.
        next_count: Number of upcoming execution times to list.
        start_time: Reference time for "next" calculations.
        title: Header text for the chart.

    Returns:
        A multi-line ASCII string ready for logging or terminal output.

    Example:
        >>> print(ascii_cron_schedule("*/15 * * * *", title="Heartbeat"))
    """
    if start_time is None:
        start_time = datetime.datetime.now(tz=TIMEZONE)

    parts = cron_str.split()
    if len(parts) != 5:
        return f'[ERROR] Invalid cron string: {cron_str!r}'

    minute_f, hour_f, day_f, month_f, dow_f = parts
    minutes = _expand_cron_field(minute_f, 0, 59)
    hours = _expand_cron_field(hour_f, 0, 23)
    days = _expand_cron_field(day_f, 1, 31)
    months = _expand_cron_field(month_f, 1, 12)
    dows = _expand_cron_field(dow_f, 0, 6)

    executions = get_next_executions(cron_str, count=next_count, start_time=start_time)

    # ── Build the chart ──────────────────────────────────────────
    lines: list[str] = []
    width = 62

    def rule(char: str = '═') -> str:
        return '╔' + char * (width - 2) + '╗'

    def mid_rule(char: str = '─') -> str:
        return '╠' + char * (width - 2) + '╣'

    def footer() -> str:
        return '╚' + '═' * (width - 2) + '╝'

    def row(content: str) -> str:
        pad = width - 2 - len(content)
        return '║ ' + content + ' ' * pad + '║'

    lines.append(rule())
    lines.append(row(f'📅  {title}'))
    lines.append(row(f'    Expression: {cron_str}'))
    lines.append(mid_rule())

    # Next executions block
    lines.append(row('⏰  NEXT EXECUTIONS'))
    lines.append(mid_rule('─'))
    if executions:
        prev = start_time
        for i, dt in enumerate(executions, 1):
            gap = _humanize_delta(dt - prev)
            date_str = dt.strftime('%a %Y-%m-%d %H:%M')
            lines.append(row(f'   {i}. {date_str}   (+{gap})'))
            prev = dt
    else:
        lines.append(row('   (no upcoming executions)'))
    lines.append(mid_rule('─'))

    # 24-hour heat-map
    lines.append(row('🌡️  24-HOUR HEAT MAP'))
    lines.append(mid_rule('─'))
    lines.append(row('    00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23'))
    lines.append(row('   ┌' + '──┬' * 23 + '──┐'))

    for m in range(0, 60, 10):
        cells = []
        for h in range(24):
            active = '██' if (h in hours and m in minutes) else '  '
            cells.append(active)
        lines.append(row(f'{m:02d} │' + '│'.join(cells) + '│'))
        if m < 50:
            lines.append(row('   ├' + '──┼' * 23 + '──┤'))
    lines.append(row('   └' + '──┴' * 23 + '──┘'))
    lines.append(mid_rule('─'))

    # Minute distribution
    lines.append(row('📊  MINUTE DISTRIBUTION'))
    lines.append(mid_rule('─'))
    buckets = [(0, 14), (15, 29), (30, 44), (45, 59)]
    for lo, hi in buckets:
        cnt = len([m for m in minutes if lo <= m <= hi])
        bar = '█' * cnt
        lines.append(row(f'   {lo:02d}-{hi:02d}  {bar:<30} {cnt}'))
    lines.append(mid_rule('─'))

    # Parsed fields summary
    lines.append(row('📝  PARSED FIELDS'))
    lines.append(mid_rule('─'))
    field_info = [
        ('Minute', minute_f, f'{len(minutes)} values'),
        ('Hour  ', hour_f, f'{len(hours)} values'),
        ('Day   ', day_f, f'{len(days)} values'),
        ('Month ', month_f, f'{len(months)} values'),
        ('DOW   ', dow_f, f'{len(dows)} values'),
    ]
    for name, expr, info in field_info:
        lines.append(row(f'   {name} : {expr:<20} {info}'))

    lines.append(footer())
    return '\n'.join(lines)
