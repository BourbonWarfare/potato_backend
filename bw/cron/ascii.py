"""
Dynamic ASCII representation for Cron schedules.
Free functions that generate next execution times and visual ASCII charts.
Integrates with the existing bw.cron runner.
"""

import datetime
from typing import Any

import cron_converter

from bw.settings import TIMEZONE
from crons.cron import Cron


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


def get_executions_in_window(
    cron_str: str,
    start: datetime.datetime,
    end: datetime.datetime,
) -> list[datetime.datetime]:
    """Return every execution time for a cron that falls inside [start, end]."""
    schedule = cron_converter.Cron(cron_str).schedule(start_date=start)
    executions: list[datetime.datetime] = []
    current = start
    while True:
        nxt = schedule.next()
        if nxt > end:
            break
        if nxt <= current:
            break
        executions.append(nxt)
        current = nxt
    return executions


def build_daily_timeline(
    cron_specs: list[tuple[str, str]],
    start_time: datetime.datetime | None = None,
) -> str:
    """
    Build an ASCII calendar / timeline of all cron executions in the next 24 hours.

    Args:
        cron_specs: List of (cron_str, job_name) tuples.
        start_time: Window start (default: now in TIMEZONE).

    Returns:
        A multi-line ASCII string showing a merged timeline and hourly grid.

    Example:
        >>> specs = [("*/15 * * * *", "Heartbeat"), ("0 22 * * *", "DailyReport")]
        >>> print(build_daily_timeline(specs))
    """
    if start_time is None:
        start_time = datetime.datetime.now(tz=TIMEZONE)

    end_time = start_time + datetime.timedelta(hours=24)

    # ── Collect executions ──────────────────────────────────────
    all_events: list[tuple[datetime.datetime, str, str]] = []
    job_stats: dict[str, dict[str, Any]] = {}

    for cron_str, name in cron_specs:
        executions = get_executions_in_window(cron_str, start_time, end_time)
        job_stats[name] = {
            'cron_str': cron_str,
            'executions': executions,
            'count': len(executions),
        }
        for dt in executions:
            all_events.append((dt, name, cron_str))

    all_events.sort(key=lambda x: x[0])

    # ── ASCII helpers ───────────────────────────────────────────
    width = 86

    def row(content: str) -> str:
        pad = width - 2 - len(content)
        return '║ ' + content + ' ' * pad + '║'

    def rule(char: str = '═') -> str:
        return '╔' + char * (width - 2) + '╗'

    def mid_rule(char: str = '─') -> str:
        return '╠' + char * (width - 2) + '╣'

    def footer() -> str:
        return '╚' + '═' * (width - 2) + '╝'

    lines: list[str] = []

    # ── Header ──────────────────────────────────────────────────
    start_fmt = start_time.strftime('%a %Y-%m-%d %H:%M')
    end_fmt = end_time.strftime('%a %Y-%m-%d %H:%M')
    lines.append(rule())
    lines.append(row('📅  DAILY CRON TIMELINE — Next 24 Hours'))
    lines.append(row(f'    {start_fmt} → {end_fmt}'))
    lines.append(mid_rule())

    # ── Chronological timeline ──────────────────────────────────
    lines.append(row('⏱️  CHRONOLOGICAL TIMELINE'))
    lines.append(mid_rule('─'))

    if not all_events:
        lines.append(row('   (no executions scheduled in this window)'))
    else:
        from itertools import groupby

        timeline_limit = 30
        current_date: datetime.date | None = None
        shown = 0

        for dt, group in groupby(all_events[:timeline_limit], key=lambda x: x[0]):
            if dt.date() != current_date:
                lines.append(row(f'  ── {dt.strftime("%a %m/%d")} ──'))
                current_date = dt.date()

            time_str = dt.strftime('%H:%M')
            group_list = list(group)
            for i, (_, name, _) in enumerate(group_list):
                prefix = f'  {time_str}  ├─ ' if i == 0 else '        ├─ '
                lines.append(row(f'{prefix}{name}'))
            shown += len(group_list)

        if len(all_events) > timeline_limit:
            lines.append(row(f'        └─ ... and {len(all_events) - timeline_limit} more'))

    lines.append(mid_rule('─'))

    # ── Hourly activity grid ────────────────────────────────────
    lines.append(row('🕐  HOURLY ACTIVITY GRID'))
    lines.append(mid_rule('─'))

    hour_labels = ' '.join(f'{(start_time.hour + h) % 24:02d}' for h in range(24))
    lines.append(row(f'Hour: {hour_labels}'))
    lines.append(row('─' * (width - 4)))

    name_width = 6
    for name, stats in sorted(job_stats.items()):
        trunc = name[:name_width].ljust(name_width)
        cells: list[str] = []
        for h in range(24):
            hour = (start_time.hour + h) % 24
            active = any(dt.hour == hour for dt in stats['executions'])
            cells.append('██ ' if active else '·  ')
        lines.append(row(f'{trunc}  {"".join(cells)}'))

    # Total row
    total_cells: list[str] = []
    for h in range(24):
        hour = (start_time.hour + h) % 24
        count = sum(1 for _, stats in job_stats.items() if any(dt.hour == hour for dt in stats['executions']))
        total_cells.append(f'{count:2d} ' if count > 0 else '·  ')
    lines.append(row('─' * (width - 4)))
    lines.append(row(f'Total  {"".join(total_cells)}'))
    lines.append(mid_rule('─'))

    # ── Job summary ─────────────────────────────────────────────
    lines.append(row('📊  JOB SUMMARY'))
    lines.append(mid_rule('─'))

    for name, stats in sorted(job_stats.items()):
        cron = stats['cron_str']
        count = stats['count']
        execs = stats['executions']

        if count == 0:
            freq = 'no runs'
        elif count == 1:
            freq = 'once'
        elif count >= 1440:
            freq = 'every minute'
        else:
            if len(execs) >= 2:
                interval = (execs[-1] - execs[0]) / (len(execs) - 1)
                freq = f'{_humanize_delta(interval)} avg'
            else:
                freq = f'{count}× in 24h'

        name_pad = name[:12].ljust(12)
        cron_pad = cron[:22].ljust(22)
        lines.append(row(f'   {name_pad} {cron_pad} {count:4d} runs  ({freq})'))

    lines.append(footer())
    return '\n'.join(lines)


def build_daily_timeline_from_classes(
    cron_classes: list[type[Cron]],
    start_time: datetime.datetime | None = None,
) -> str:
    """
    Convenience wrapper that accepts loaded Cron classes directly.

    Usage inside Runner.gather_crons():
        loaded = [m.cron_class for m in self.loaded_crons_.values()]
        chart = build_daily_timeline_from_classes(loaded)
        for line in chart.splitlines():
            logger.info(line)
    """
    specs = [(cls.cron_str(), cls.__name__) for cls in cron_classes]
    return build_daily_timeline(specs, start_time)
