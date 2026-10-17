"""Online read-only SQLite source backup to a new output; no checkpoint/source writes."""
import argparse,sqlite3
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists() or a.output.is_symlink():raise FileExistsError('fresh backup required')
s=sqlite3.connect(a.source.resolve().as_uri()+'?mode=ro',uri=True);d=sqlite3.connect(a.output);s.backup(d);d.close();s.close()
