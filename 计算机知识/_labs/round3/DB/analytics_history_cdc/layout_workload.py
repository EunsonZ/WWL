"""Same coded finite records in row/column files; payload counts, NOT engine speed claims."""
import argparse
import json
from pathlib import Path
import struct

COLUMNS = ["fact_id", "customer_id", "occurred_day", "duration_seconds", "region", "channel", "note", "source_ref", "version"]
ROW = struct.Struct("<9q")
VALUE = struct.Struct("<q")
PAIR = struct.Struct("<qq")


def encode(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_workload(entities, assignments, repeat):
    if type(repeat) is not int or not 0 <= repeat <= 1000:
        raise ValueError("repeat must be 0..1000")
    live = [(key, row["after"]) for key, row in sorted(entities.items()) if row["op"] == "put"]
    by_key = {a[0]: encode(a[2:]) for a in assignments}
    dictionaries = {name: sorted({row[name] for _, row in live}) for name in ("customer_id", "channel", "note", "source_ref")}
    dictionaries["region"] = sorted(set(by_key.values()))
    maps = {k: {v: i for i, v in enumerate(values)} for k, values in dictionaries.items()}
    rows = []
    for copy_index in range(repeat):
        for _, (key, fact) in enumerate(live):
            rows.append([len(rows), maps["customer_id"][fact["customer_id"]], fact["occurred_day"],
                         fact["duration_seconds"], maps["region"][by_key[key]], maps["channel"][fact["channel"]],
                         maps["note"][fact["note"]], maps["source_ref"][fact["source_ref"]], fact["version"]])
    return {"columns": COLUMNS, "rows": rows, "dictionaries": dictionaries,
            "base_fact_count": len(live), "repeat": repeat, "scalar_bytes": 8}


def write_layout(workload, directory):
    directory.mkdir()
    rows = workload["rows"]
    with (directory / "rows.bin").open("wb") as stream:
        for row in rows:
            stream.write(ROW.pack(*row))
    for j, name in enumerate(COLUMNS):
        with (directory / (name + ".bin")).open("wb") as stream:
            for row in rows:
                stream.write(VALUE.pack(row[j]))


def metrics(n, selected, calls, payload_bytes, read_calls, scratch=0):
    return {"rows": n, "predicate_rows": n, "selected_rows": selected, "aggregate_updates": selected,
            "operator_calls": calls, "returned_payload_bytes": payload_bytes,
            "nonempty_read_calls": read_calls, "scratch_slots_peak": scratch}


def decode_groups(groups, workload):
    result = []
    for code in sorted(groups):
        status, region = json.loads(workload["dictionaries"]["region"][code])
        result.append([status, region, *groups[code]])
    return result


def query_rows(path, workload, day, channel):
    channels = workload["dictionaries"]["channel"]
    code = channels.index(channel) if channel in channels else -1
    groups, n, selected, payload, reads = {}, 0, 0, 0, 0
    def process(row):
        nonlocal selected
        if row[2] >= day and row[5] == code:
            selected += 1
            total, count = groups.get(row[4], (0, 0))
            groups[row[4]] = (total + row[3], count + 1)
    with path.open("rb") as stream:
        while raw := stream.read(ROW.size):
            if len(raw) != ROW.size:
                raise ValueError("truncated row")
            payload += len(raw)
            reads += 1
            n += 1
            process(ROW.unpack(raw))
    return {"groups": decode_groups(groups, workload), "metrics": metrics(n, selected, n, payload, reads)}


def read_column(directory, name):
    raw = (directory / (name + ".bin")).read_bytes()
    if len(raw) % 8:
        raise ValueError("truncated column")
    return [v[0] for v in struct.iter_unpack("<q", raw)], len(raw)


def query_columns(directory, workload, day, channel, batch=None):
    columns, payload = {}, 0
    for name in ("occurred_day", "channel", "region", "duration_seconds"):
        columns[name], size = read_column(directory, name)
        payload += size
    n = len(columns["occurred_day"])
    if any(len(values) != n for values in columns.values()):
        raise ValueError("misaligned column lengths")
    channels = workload["dictionaries"]["channel"]
    channel_code = channels.index(channel) if channel in channels else -1
    groups, selected, calls, scratch = {}, 0, 0, 0
    def add(index):
        nonlocal selected
        selected += 1
        code = columns["region"][index]
        total, count = groups.get(code, (0, 0))
        groups[code] = (total + columns["duration_seconds"][index], count + 1)
    if batch is None:
        def process(index):
            if columns["occurred_day"][index] >= day and columns["channel"][index] == channel_code:
                add(index)
        for index in range(n):
            process(index)
            calls += 1
    else:
        if type(batch) is not int or not 1 <= batch <= 4096:
            raise ValueError("batch must be 1..4096")
        def process_batch(low, high):
            nonlocal scratch
            mask = [columns["occurred_day"][i] >= day and columns["channel"][i] == channel_code for i in range(low, high)]
            selection = [low + i for i, chosen in enumerate(mask) if chosen]
            scratch = max(scratch, len(mask) + len(selection))
            for index in selection:
                add(index)
        for low in range(0, n, batch):
            process_batch(low, min(n, low + batch))
            calls += 1
    return {"groups": decode_groups(groups, workload),
            "metrics": metrics(n, selected, calls, payload, 4 if n else 0, scratch)}


def rle(values):
    pairs = []
    for value in values:
        if pairs and pairs[-1][0] == value:
            pairs[-1][1] += 1
        else:
            pairs.append([value, 1])
    raw = b"".join(PAIR.pack(v, n) for v, n in pairs)
    decoded = [v for v, n in struct.iter_unpack("<qq", raw) for _ in range(n)]
    if decoded != list(values):
        raise AssertionError("RLE roundtrip")
    return {"runs": len(pairs), "encoded_bytes": len(raw), "decoded_values": len(decoded)}


def run(workload, directory, day, channel, batches):
    write_layout(workload, directory)
    rows = query_rows(directory / "rows.bin", workload, day, channel)
    columns = query_columns(directory, workload, day, channel)
    blocked = {str(b): query_columns(directory, workload, day, channel, b) for b in batches}
    if any(result["groups"] != rows["groups"] for result in [columns, *blocked.values()]):
        raise AssertionError("same workload has different aggregates")
    point = None
    n = len(workload["rows"])
    if n:
        index = n // 2
        with (directory / "rows.bin").open("rb") as stream:
            stream.seek(index * ROW.size)
            row_point = list(ROW.unpack(stream.read(ROW.size)))
        col_point = []
        for name in COLUMNS:
            with (directory / (name + ".bin")).open("rb") as stream:
                stream.seek(index * 8)
                col_point.append(VALUE.unpack(stream.read(8))[0])
        if row_point != col_point:
            raise AssertionError("point record alignment")
        point = {"index": index, "row": row_point, "row_payload_bytes": 72, "row_read_calls": 1,
                 "column_payload_bytes": 72, "column_read_calls": 9}
    region = [row[4] for row in workload["rows"]]
    # Reorder FULL rows, so every column keeps its fact identity; query is order-independent.
    sorted_rows = sorted(workload["rows"], key=lambda row: row[4])
    return {"query": {"day_at_least": day, "channel": channel}, "columns": COLUMNS,
            "N": n, "W": len(COLUMNS), "projected_columns": 4, "scalar_bytes": 8,
            "row_scan": rows, "column_scan": columns, "blocked": blocked, "point": point,
            "rle_region": {"raw_bytes": 8 * n, "unsorted": rle(region),
                           "full_rows_sorted_by_region": rle([row[4] for row in sorted_rows]),
                           "sort_requires_full_row_permutation": True},
            "boundary": "returned serialized payload bytes and explicit Python calls; not disk I/O, cache misses, SIMD or measured engine speed"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--actual", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    spec = json.loads(args.input.read_text())
    actual = json.loads(args.actual.read_text())
    workload = build_workload(dict(actual["final"]["entities"]), actual["final"]["as_of"]["assignments"], spec["workload"]["repeat"])
    result = run(workload, args.work, spec["workload"]["day_at_least"], spec["workload"]["channel"], spec["workload"]["batch_sizes"])
    args.out.write_text(json.dumps({"workload": workload, "result": result}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
