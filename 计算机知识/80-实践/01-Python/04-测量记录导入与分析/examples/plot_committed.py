"""Read-only committed rows -> SVG plus exact CSV plot source; standard library."""
import argparse
from contextlib import closing
import csv
from fractions import Fraction
from html import escape
from pathlib import Path
import sqlite3

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("svg", type=Path)
    args = parser.parse_args()
    if args.svg.suffix.lower() != ".svg":
        parser.error("output must end in .svg")
    source = args.svg.with_suffix(".csv")
    if not args.database.is_file():
        parser.error("database must already exist")
    paths = [args.database, args.svg, source]
    for i, left in enumerate(paths):
        for right in paths[i+1:]:
            if left.resolve() == right.resolve() or (left.exists() and right.exists() and left.samefile(right)):
                parser.error("database, SVG and CSV must be distinct files")
    with closing(sqlite3.connect(args.database.resolve().as_uri()+"?mode=ro", uri=True)) as db:
        rows = db.execute("SELECT sample_id,tick_ms,code FROM samples ORDER BY tick_ms,sample_id").fetchall()
    # This visualization intentionally materializes its selected finite dataset.
    if not rows:
        parser.error("no committed samples to plot")
    count = len(rows)
    mean = Fraction(sum(row[2] for row in rows), count)
    pvar = sum((Fraction(row[2])-mean)**2 for row in rows)/count
    xmin, xmax = rows[0][1], rows[-1][1]
    xmax = max(xmax, xmin+1)
    ymax = max(1, max(row[2] for row in rows)) * 1.25
    def x(tick): return 90+(tick-xmin)/(xmax-xmin)*590
    def y(code): return 360-code/ymax*270
    points = " ".join(f"{x(t):.2f},{y(c):.2f}" for _,t,c in rows)
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="470" viewBox="0 0 800 470" role="img" aria-labelledby="title desc">',
        '<title id="title">Committed synthetic measurement records</title>',
        '<desc id="desc">Time in milliseconds, voltage in millivolts. Labeled circles show committed sample identities. A dashed horizontal line shows their descriptive mean, not a confidence interval. Lines connect records for reading order only.</desc>',
        '<rect width="800" height="470" fill="#fff"/>',
        '<g font-family="sans-serif" font-size="15" fill="#172b4d">',
        '<text x="90" y="35" font-size="21">Committed synthetic measurement records</text>',
        f'<text x="90" y="60">n={count}; mean={mean} mV; descriptive variance={pvar} mV²</text>',
        '<path d="M90 90 V360 H680" fill="none" stroke="#172b4d" stroke-width="2"/>',
        '<text x="310" y="420">tick_ms (ms)</text>',
        '<text x="22" y="285" transform="rotate(-90 22 285)">voltage (mV)</text>',
        f'<line x1="90" y1="{y(mean):.2f}" x2="680" y2="{y(mean):.2f}" stroke="#a14c00" stroke-width="2" stroke-dasharray="8 5"/>',
        f'<text x="688" y="{y(mean)+5:.2f}" fill="#a14c00">mean {mean}</text>',
        f'<polyline points="{points}" fill="none" stroke="#1f6b9c" stroke-width="2"/>',
    ]
    for i in range(6):
        value = ymax*i/5
        elements += [f'<text x="55" y="{y(value)+5:.2f}">{value:g}</text>']
    for identity,tick,code in rows:
        elements += [f'<circle cx="{x(tick):.2f}" cy="{y(code):.2f}" r="5" fill="#1f6b9c"/>',
                     f'<text x="{x(tick)+9:.2f}" y="{y(code)-9:.2f}">{escape(identity)}: {code}</text>',
                     f'<text x="{x(tick)-15:.2f}" y="386">{tick}</text>']
    elements += ['<text x="90" y="452" font-size="13">1 mV/code, zero offset; synthetic finite records; no confidence interval.</text>', '</g></svg>']
    # Files do not share a transaction with one another or the read-only database.
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["sample_id", "tick_ms", "voltage_mV"])
        writer.writerows(rows)
    args.svg.write_text("\n".join(elements)+"\n", encoding="utf-8")
    print(f"wrote {args.svg} and {source}; rows={count}")

if __name__ == "__main__":
    main()
