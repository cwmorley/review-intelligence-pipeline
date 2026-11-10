"""Load the synthetic CSVs into in-memory SQLite and run coverage_rate.sql."""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = {"candidates": "synthetic_candidates.csv", "reviews": "synthetic_reviews.csv", "engagements": "synthetic_engagements.csv"}


def coverage_rates(data_dir: Path = ROOT / "data") -> list[dict]:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    for table, filename in TABLES.items():
        with (Path(data_dir) / filename).open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = ", ".join(f'"{name}" TEXT' for name in reader.fieldnames)
            connection.execute(f'CREATE TABLE "{table}" ({columns})')
            marks = ", ".join("?" for _ in reader.fieldnames)
            connection.executemany(f'INSERT INTO "{table}" VALUES ({marks})', ([row[name] for name in reader.fieldnames] for row in reader))
    query = (Path(__file__).with_name("coverage_rate.sql")).read_text(encoding="utf-8")
    return [dict(row) for row in connection.execute(query)]


if __name__ == "__main__":
    rows = coverage_rates(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data")
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
