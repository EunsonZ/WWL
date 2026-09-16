"""Small, offline teaching models for routing, scan evidence, authorization and metrics.

No sockets, listeners, subprocesses, downloads, imports with side effects, or file writes.
All identities and examples are synthetic. This module is NOT an authentication server,
Linux routing implementation, production XML parser, or forensic provenance verifier.
Python >= 3.10; standard library only. CLI reads only a fixed demo, never a target URL.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import math
import re
import xml.etree.ElementTree as ET


class InputError(ValueError):
    """Input is outside the explicitly documented teaching domain."""


def _natural(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise InputError(f"{name}: nonnegative integer required (not bool)")
    return value


@dataclass(frozen=True)
class Route:
    prefix: str
    interface: str
    metric: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.prefix, str):
            raise InputError("prefix: text required")
        try:
            network = ipaddress.ip_network(self.prefix, strict=True)
        except ValueError as exc:
            raise InputError("prefix must be a strict network, not a host-with-mask") from exc
        if '%' in self.prefix or '/' not in self.prefix:
            raise InputError("explicit unscoped prefix length required")
        if not isinstance(self.interface, str) or not self.interface or len(self.interface) > 64:
            raise InputError("interface must be 1..64 characters")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", self.interface):
            raise InputError("interface contains unsupported characters")
        _natural(self.metric, "metric")
        object.__setattr__(self, "prefix", str(network))


def choose_route(destination: str, routes: list[Route] | tuple[Route, ...]) -> Route | None:
    """Single-table unicast model: longest prefix, then lowest metric.

    No rules, gateways, link state, local/broadcast tables or ECMP. Ties are rejected,
    rather than using arbitrary input order. None means no matching route in this model.
    """
    if not isinstance(destination, str) or '%' in destination:
        raise InputError("destination must be an unscoped IP address string")
    try:
        address = ipaddress.ip_address(destination)
    except ValueError as exc:
        raise InputError("invalid destination address") from exc
    if not isinstance(routes, (list, tuple)) or len(routes) > 1024:
        raise InputError("routes must be a list/tuple of at most 1024 Route objects")
    candidates = []
    for route in routes:
        if not isinstance(route, Route):
            raise InputError("every entry must be a Route")
        network = ipaddress.ip_network(route.prefix)
        if network.version == address.version and address in network:
            candidates.append((network.prefixlen, route.metric, route))
    if not candidates:
        return None
    best_prefix = max(item[0] for item in candidates)
    longest = [item for item in candidates if item[0] == best_prefix]
    best_metric = min(item[1] for item in longest)
    best = [item[2] for item in longest if item[1] == best_metric]
    if len(best) != 1:
        raise InputError("equal-cost tie: ECMP and duplicate routes are outside this model")
    return best[0]


def infer_scan_state(probe: str, observation: str) -> str:
    """Pedagogical SYN/UDP lookup, not an active scanner.

    'no_response' assumes the caller has exhausted its declared observation window.
    We cannot distinguish packet loss, filtering, and nonresponse from this label alone.
    """
    outcomes = {
        "tcp_syn": {"syn_ack": "open", "rst": "closed", "no_response": "filtered"},
        "udp": {"udp_reply": "open", "icmp_port_unreachable": "closed",
                "no_response": "open|filtered"},
    }
    if not isinstance(probe, str) or not isinstance(observation, str):
        raise InputError("probe and observation must be strings")
    try:
        return outcomes[probe][observation]
    except KeyError as exc:
        raise InputError("unsupported probe/observation pair") from exc


@dataclass(frozen=True)
class PortObservation:
    address: str
    protocol: str
    port: int
    state: str
    reason: str | None

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.address, self.protocol, self.port)


@dataclass(frozen=True)
class ScanSnapshot:
    finished: str
    ports: tuple[PortObservation, ...]
    hosts: tuple[tuple[str, str], ...]
    scan_scope: tuple[tuple[str, str], ...]
    aggregates: tuple[tuple[str, str, int], ...]


PORT_STATES = frozenset({"open", "closed", "filtered", "unfiltered", "open|filtered", "closed|filtered"})


def parse_scan_xml(raw: bytes) -> ScanSnapshot:
    """Read a bounded UTF-8, unnamespaced Nmap XML subset from owned/synthetic files.

    Max 1 MiB, 20000 elements, depth 64; only an optional plain <!DOCTYPE nmaprun>
    is accepted. Reject other DTD/entity declarations, NUL/UTF-16 and unsupported states.
    One IP per host is required (MAC entries may coexist). Port text is 1..5 digits;
    aggregate counts are 0..131072 with at most 6 digits. Missing ports stay missing;
    extraports is retained only as an aggregate. Unknown extra elements are not interpreted.
    These checks reduce ambiguity; they do not constitute a general hostile-XML sandbox.
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 1_048_576:
        raise InputError("XML must be 1..1048576 bytes")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputError("UTF-8 XML required") from exc
    if '\x00' in text:
        raise InputError("NUL/UTF-16 is not supported")
    declaration = re.search(r'<\?xml\s+([^?]*)\?>', text)
    if declaration:
        enc = re.search(r'encoding\s*=\s*[\'"]([^\'"]+)[\'"]', declaration.group(1))
        if enc and enc.group(1).lower() not in {"utf-8", "utf8", "us-ascii"}:
            raise InputError("unsupported XML encoding declaration")
    text, count = re.subn(r'<!DOCTYPE\s+nmaprun\s*>', '', text)
    if count > 1 or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise InputError("external/internal DTD and entity declarations are not accepted")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise InputError("malformed XML") from exc
    if root.tag != "nmaprun":
        raise InputError("expected unnamespaced nmaprun root")
    stack, total = [(root, 1)], 0
    while stack:
        node, depth = stack.pop()
        total += 1
        if depth > 64 or total > 20_000:
            raise InputError("XML structural limit exceeded")
        stack.extend((child, depth + 1) for child in node)
    finished_nodes = root.findall("./runstats/finished")
    if len(finished_nodes) > 1:
        raise InputError("duplicate finished records")
    finished = finished_nodes[0].get("exit", "unknown") if finished_nodes else "unknown"
    if finished not in {"success", "error", "unknown"}:
        raise InputError("unsupported finished status")
    scopes = []
    for node in root.findall("./scaninfo"):
        protocol = node.get("protocol")
        if protocol not in {"tcp", "udp"}:
            raise InputError("scaninfo supports tcp/udp only")
        scopes.append((protocol, node.get("services", "unknown")))
    ports, hosts, aggregates, seen_hosts, seen_ports = [], [], [], set(), set()
    for host in root.findall("./host"):
        addresses = [a for a in host.findall("./address") if a.get("addrtype") in {"ipv4", "ipv6"}]
        if len(addresses) != 1:
            raise InputError("this subset requires exactly one IP address per host")
        address_node = addresses[0]
        try:
            ip = ipaddress.ip_address(address_node.get("addr", ""))
        except ValueError as exc:
            raise InputError("invalid host address") from exc
        if '%' in str(ip) or address_node.get("addrtype") != f"ipv{ip.version}":
            raise InputError("address family mismatch or scoped address")
        address = str(ip)
        if address in seen_hosts:
            raise InputError("duplicate host IP")
        seen_hosts.add(address)
        statuses = host.findall("./status")
        if len(statuses) > 1:
            raise InputError("duplicate host status")
        host_state = statuses[0].get("state", "unknown") if statuses else "unknown"
        if host_state not in {"up", "down", "unknown", "skipped"}:
            raise InputError("unsupported host state")
        hosts.append((address, host_state))
        for node in host.findall("./ports/port"):
            protocol, number = node.get("protocol"), node.get("portid", "")
            if protocol not in {"tcp", "udp"} or not 1 <= len(number) <= 5 or not number.isascii() or not number.isdecimal():
                raise InputError("invalid protocol or port")
            port = int(number)
            if not 0 <= port <= 65535:
                raise InputError("port must be in 0..65535")
            states = node.findall("./state")
            if len(states) != 1 or states[0].get("state") not in PORT_STATES:
                raise InputError("one explicit supported state is required per port")
            observation = PortObservation(address, protocol, port, states[0].get("state"), states[0].get("reason"))
            if observation.key in seen_ports:
                raise InputError("duplicate port observation")
            seen_ports.add(observation.key)
            ports.append(observation)
        for node in host.findall("./ports/extraports"):
            count_text, state = node.get("count", ""), node.get("state")
            if state not in PORT_STATES or not 1 <= len(count_text) <= 6 or not count_text.isascii() or not count_text.isdecimal():
                raise InputError("invalid extraports aggregate")
            count_value = int(count_text)
            if count_value > 131072:
                raise InputError("aggregate exceeds the TCP+UDP teaching bound")
            aggregates.append((address, state, count_value))
    return ScanSnapshot(finished, tuple(ports), tuple(hosts), tuple(scopes), tuple(aggregates))


def compare_scans(before: ScanSnapshot, after: ScanSnapshot) -> list[dict]:
    """Compare explicit observations, never infer a missing individual port is closed."""
    if not isinstance(before, ScanSnapshot) or not isinstance(after, ScanSnapshot):
        raise InputError("ScanSnapshot objects required")
    old = {p.key: p for p in before.ports}
    new = {p.key: p for p in after.ports}
    rows = []
    for key in sorted(old.keys() | new.keys()):
        left = old[key].state if key in old else "not_observed"
        right = new[key].state if key in new else "not_observed"
        relation = "coverage_gap" if "not_observed" in {left, right} else ("same" if left == right else "explicit_change")
        rows.append({"address": key[0], "protocol": key[1], "port": key[2],
                     "before": left, "after": right, "relation": relation,
                     "before_finished": before.finished, "after_finished": after.finished})
    return rows


@dataclass(frozen=True)
class Principal:
    identity: str
    tenant: str
    role: str


@dataclass(frozen=True)
class Report:
    ident: int
    tenant: str
    owner: str
    status: str
    title: str
    private_note: str


# Trusted server-side registry for this model, never populated from request claims.
_PRINCIPALS = {
    "alice": Principal("alice", "red", "author"),
    "bob": Principal("bob", "red", "reviewer"),
    "carol": Principal("carol", "blue", "reviewer"),
}
_REPORTS = {
    17: Report(17, "red", "alice", "draft", "Report A", "synthetic owner note A"),
    18: Report(18, "red", "alice", "submitted", "Report B", "synthetic owner note B"),
    19: Report(19, "blue", "carol", "submitted", "Report C", "synthetic owner note C"),
    20: Report(20, "red", "bob", "submitted", "Report D", "synthetic owner note D"),
    21: Report(21, "red", "alice", "approved", "Report E", "synthetic owner note E"),
}


def _context(identity: object, report_id: object) -> tuple[Principal, Report] | None:
    if not isinstance(identity, str) or type(report_id) is not int:
        return None
    principal, report = _PRINCIPALS.get(identity), _REPORTS.get(report_id)
    if principal is None or report is None or principal.tenant != report.tenant:
        return None
    return principal, report


def allowed(identity: object, report_id: object, action: object) -> bool:
    """Pure policy decision; identity is assumed already authenticated by a trusted caller.

    No state mutation, token verification, HTTP semantics, transactions or concurrency.
    A reviewer may read same-tenant summaries but may not approve their own submitted item.
    """
    context = _context(identity, report_id)
    if context is None or not isinstance(action, str):
        return False
    principal, report = context
    owner = principal.identity == report.owner
    if action == "read":
        return owner or principal.role == "reviewer"
    if action in {"edit", "submit"}:
        return owner and report.status == "draft"
    if action == "approve":
        return principal.role == "reviewer" and not owner and report.status == "submitted"
    return False


def project_report(identity: object, report_id: object) -> dict:
    """New allowed-field dictionary; private_note is owner-only, even for reviewers."""
    if not allowed(identity, report_id, "read"):
        raise PermissionError("report is not readable")
    principal, report = _context(identity, report_id)  # validated by allowed
    result = {"id": report.ident, "status": report.status, "title": report.title}
    if principal.identity == report.owner:
        result["private_note"] = report.private_note
    return result


_TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$')


def utc_timestamp(text: str) -> datetime:
    """Strict teaching subset: explicit date/time, 0..6 fractional digits and UTC offset.

    Reject naive timestamps, leap seconds, fractional offsets and -00:00 (unknown offset).
    This is not a general ISO 8601 parser or a proof the source clock is accurate.
    """
    if not isinstance(text, str) or not _TIMESTAMP.fullmatch(text) or text.endswith("-00:00"):
        raise InputError("timestamp requires a known explicit offset and seconds")
    if not text.endswith("Z") and (int(text[-5:-3]) > 23 or int(text[-2:]) > 59):
        raise InputError("offset hours/minutes out of range")
    try:
        value = datetime.fromisoformat(text.removesuffix('Z') + '+00:00' if text.endswith('Z') else text)
        if value.utcoffset() is None:
            raise InputError("missing offset")
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise InputError("invalid or unrepresentable timestamp") from exc


def definitely_before(first: str, first_error: int, second: str, second_error: int) -> bool:
    """Closed uncertainty intervals in whole seconds; touching/overlapping is not strict order."""
    a, b = utc_timestamp(first), utc_timestamp(second)
    da, db = _natural(first_error, "first_error"), _natural(second_error, "second_error")
    if da > 86400 or db > 86400:
        raise InputError("teaching uncertainty bound is at most one day")
    try:
        return a + timedelta(seconds=da) < b - timedelta(seconds=db)
    except OverflowError as exc:
        raise InputError("uncertainty interval outside datetime range") from exc


def detection_metrics(tp: int, fp: int, tn: int, fn: int) -> dict[str, float | None]:
    """Counts must refer to independently labelled cases from the same defined population."""
    for name, value in (("tp", tp), ("fp", fp), ("tn", tn), ("fn", fn)):
        _natural(value, name)
    def ratio(a: int, b: int) -> float | None:
        return a / b if b else None
    return {"precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn), "fpr": ratio(fp, fp + tn)}


def byte_entropy(data: bytes) -> float:
    """Empirical single-byte Shannon entropy in bits/symbol, not an encryption detector."""
    if not isinstance(data, bytes) or not 1 <= len(data) <= 1_048_576:
        raise InputError("entropy input must be 1..1048576 bytes")
    counts, size = Counter(data), len(data)
    return -sum((count / size) * math.log2(count / size) for count in counts.values())


def run_demo() -> dict:
    route = choose_route("192.168.56.37", [Route("0.0.0.0/0", "uplink", 1),
                         Route("192.168.56.0/24", "lab", 10), Route("192.168.56.32/27", "lab-specific", 900)])
    return {"synthetic": True, "network_io": False, "route": asdict(route),
            "udp_no_response": infer_scan_state("udp", "no_response"),
            "authorization": {"bob_approve_18": allowed("bob", 18, "approve"),
                              "bob_approve_20": allowed("bob", 20, "approve"),
                              "carol_read_17": allowed("carol", 17, "read"),
                              "bob_fields_18": sorted(project_report("bob", 18))},
            "utc": utc_timestamp("2026-09-05T16:00:00+08:00").isoformat(),
            "metrics": detection_metrics(900, 9990, 989010, 100),
            "entropy_uniform_byte_histogram": byte_entropy(bytes(range(256)))}


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2, allow_nan=False))