#!/usr/bin/env python3
"""Measure system metrics, store them in SQLite and report on them.

Modes:
    measure   measure metrics and add them to the database
    report    show stored measurements, optionally for a time period
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import psutil

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_DATABASE = "monitor.db"


def available_metrics():
    """Return a dict mapping each recognized metric name to a function."""
    metrics = {
        "cpu-usage": lambda: psutil.cpu_percent(interval=1),
        "memory-usage": lambda: psutil.virtual_memory().percent,
    }
    for index, partition in enumerate(psutil.disk_partitions()):
        metrics[f"disk-{index}-usage"] = (
            lambda p=partition: psutil.disk_usage(p.mountpoint).percent)
    return metrics


def parse_time(text, end_of_day=False):
    """Convert YYYY-MM-DD[ HH:MM:SS] to the stored format.

    A bare date used as an end time covers that whole day.
    """
    moment = datetime.fromisoformat(text)
    if end_of_day and len(text) == 10:
        moment = moment.replace(hour=23, minute=59, second=59)
    return moment.strftime(TIME_FORMAT)


def parse_end_time(text):
    """Like parse_time, for an end time (a bare date covers the day)."""
    return parse_time(text, end_of_day=True)


def connect(path):
    """Open the database and make sure the measurements table exists."""
    database = sqlite3.connect(path)
    database.execute(
        "CREATE TABLE IF NOT EXISTS measurements ("
        "time TEXT NOT NULL, metric TEXT NOT NULL, value REAL NOT NULL)")
    return database


def measure(args):
    """Measure the requested metrics and add them to the database."""
    known = available_metrics()
    database = connect(args.database)
    with database:
        if args.reset:
            database.execute("DELETE FROM measurements")
        for name in args.metrics or sorted(known):
            if name not in known:
                print(f"Skipped unknown metric: {name}", file=sys.stderr)
                continue
            timestamp = datetime.now().strftime(TIME_FORMAT)
            value = known[name]()
            database.execute("INSERT INTO measurements VALUES (?, ?, ?)",
                             (timestamp, name, value))
            print(f"{timestamp}  {name}: {value:.1f}%")
    database.close()


def build_filter(args):
    """Return the SQL WHERE clause and parameters for the report filters."""
    clauses, params = [], []
    if args.start:
        clauses.append("time >= ?")
        params.append(args.start)
    if args.end:
        clauses.append("time <= ?")
        params.append(args.end)
    if args.metrics:
        clauses.append(f"metric IN ({','.join('?' * len(args.metrics))})")
        params.extend(args.metrics)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params


def report(args):
    """Display the stored measurements and, optionally, statistics."""
    if not Path(args.database).exists():
        sys.exit(f"No database '{args.database}' yet. Run 'measure' first.")
    database = connect(args.database)
    where, params = build_filter(args)
    rows = database.execute(
        "SELECT time, metric, value FROM measurements" + where
        + " ORDER BY time, metric", params).fetchall()
    if not rows:
        print("No measurements found for this selection.")
        return
    print(f"{'Timestamp':<21}{'Metric':<15}{'Value':>7}")
    for time, metric, value in rows:
        print(f"{time:<21}{metric:<15}{value:>6.1f}%")
    if args.summary:
        print(f"\n{'Metric':<15}{'Count':>6}{'Avg':>8}{'Min':>8}{'Max':>8}")
        for name, count, average, low, high in database.execute(
                "SELECT metric, COUNT(*), AVG(value), MIN(value), MAX(value)"
                " FROM measurements" + where + " GROUP BY metric "
                "ORDER BY metric", params):
            print(f"{name:<15}{count:>6}{average:>7.1f}%"
                  f"{low:>7.1f}%{high:>7.1f}%")
    database.close()


def build_parser():
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("mode", choices=["measure", "report"])
    parser.add_argument("--metrics", nargs="+",
                        help="metrics to measure/show (measure default: all)")
    parser.add_argument("--database", default=DEFAULT_DATABASE,
                        help=f"SQLite database file (default: "
                             f"{DEFAULT_DATABASE})")
    parser.add_argument("--reset", action="store_true",
                        help="measure: delete stored data, start clean")
    parser.add_argument("--start", type=parse_time,
                        help="report: from YYYY-MM-DD[ HH:MM:SS]")
    parser.add_argument("--end", type=parse_end_time,
                        help="report: until YYYY-MM-DD[ HH:MM:SS]")
    parser.add_argument("--summary", action="store_true",
                        help="report: add count, average, min and max")
    return parser


def main():
    """Run the chosen mode."""
    args = build_parser().parse_args()
    {"measure": measure, "report": report}[args.mode](args)


if __name__ == "__main__":
    main()