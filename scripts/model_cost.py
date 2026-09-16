#!/usr/bin/env python3
"""Strict, offline USD estimates and budget/retry checks; no client or runtime lock.

Only Python's standard library is used. Importing this module has no side effects.
CLI JSON output represents supplied facts and references, never an invoice.
"""
import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re
import sys

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_ROWS = 10000
MAX_INTEGER = 10**18
RATE_KEYS = {'noncached_input', 'cache_read', 'cache_write', 'output'}
REQUEST_FIELDS = {
    'kind', 'provider', 'billing_scope', 'request_id', 'timestamp', 'price_version',
    'price_sha256', 'model', 'service_tier', 'input_total', 'noncached_input',
    'cache_read', 'cache_write', 'output', 'reasoning', 'cache_policy', 'output_policy',
    'tools', 'problem_id', 'attempt_id', 'prompt_ref',
}
IDENTITY_METADATA = {'problem_id', 'attempt_id', 'prompt_ref'}


class ContractError(ValueError):
    """Invalid or contradictory supplied facts, safe to report without payloads."""


def require(condition, message):
    if not condition:
        raise ContractError(message)


def fields(value, allowed, required, label):
    require(type(value) is dict, f'{label}: object required')
    require(not (set(value) - allowed), f'{label}: unknown field')
    require(required <= set(value), f'{label}: missing required field')


def text_value(value, label, nullable=False):
    if value is None and nullable:
        return None
    require(type(value) is str and bool(value.strip()) and len(value) <= 2000,
            f'{label}: nonempty text of at most 2000 characters required')
    return value


def integer(value, label, nullable=False, minimum=0, maximum=MAX_INTEGER):
    if value is None and nullable:
        return None
    require(type(value) is int and minimum <= value <= maximum,
            f'{label}: bounded nonnegative integer required (booleans rejected)')
    return value


def boolean(value, label):
    require(type(value) is bool, f'{label}: boolean required')
    return value


def money(value, label, nullable=False):
    if value is None and nullable:
        return None
    require(type(value) in (str, int, Decimal), f'{label}: decimal number or string required')
    try:
        number = Decimal(value)
    except (ValueError, ArithmeticError):
        raise ContractError(f'{label}: invalid decimal') from None
    require(number.is_finite() and number >= 0, f'{label}: finite nonnegative decimal required')
    require(number.adjusted() <= 18 and number.as_tuple().exponent >= -18
            and len(number.as_tuple().digits) <= 40, f'{label}: decimal precision/range exceeded')
    return number


def dollars(value):
    value = format(value, 'f')
    return value.rstrip('0').rstrip('.') if '.' in value else value


def timestamp(value, label, nullable=False):
    if value is None and nullable:
        return None
    text_value(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ContractError(f'{label}: ISO timestamp with timezone required') from None
    require(parsed.tzinfo is not None, f'{label}: timezone required')
    try:
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise ContractError(f'{label}: timestamp outside supported range') from None


def rows(value, label, maximum=MAX_ROWS):
    require(type(value) is list and len(value) <= maximum, f'{label}: bounded array required')
    return value


def sha_value(value, label, nullable=False):
    if value is None and nullable:
        return None
    require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None,
            f'{label}: lowercase SHA256 required')
    return value


def schema(value, allowed, required, label):
    fields(value, allowed | {'schema_version'}, required | {'schema_version'}, label)
    require(type(value['schema_version']) is int and value['schema_version'] == 1,
            f'{label}: unsupported schema_version')


def decode_json(content):
    def pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'JSON: duplicate object key')
            result[key] = value
        return result

    def constant_hook(_value):
        raise ContractError('JSON: NaN and Infinity are forbidden')

    try:
        return json.loads(content, object_pairs_hook=pairs_hook,
                          parse_float=Decimal, parse_constant=constant_hook)
    except (json.JSONDecodeError, RecursionError, ValueError, ArithmeticError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError('JSON: malformed or excessively nested input') from None


def read_json(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    require(len(raw) <= MAX_FILE_BYTES, 'JSON: file exceeds 8 MiB')
    try:
        document = decode_json(raw.decode('utf-8'))
    except UnicodeDecodeError:
        raise ContractError('JSON: UTF-8 required') from None
    return document, hashlib.sha256(raw).hexdigest()


def validate_prices(document):
    required = {'version', 'currency', 'status', 'verified_at', 'source', 'scope_note', 'entries'}
    schema(document, required, required, 'prices')
    for key in ('version', 'source', 'scope_note'):
        text_value(document[key], 'prices.' + key)
    require(document['currency'] == 'USD', 'prices: only USD supported')
    require(document['status'] in ('hypothetical', 'verified_reference'), 'prices: invalid status')
    try:
        date.fromisoformat(document['verified_at'])
    except (TypeError, ValueError):
        raise ContractError('prices.verified_at: ISO date required') from None
    selectors = set()
    for entry in rows(document['entries'], 'prices.entries', 1000):
        keys = {'provider', 'billing_scope', 'model', 'service_tier', 'valid_from',
                'valid_until', 'input_tiers', 'tool_rates_per_unit'}
        fields(entry, keys | {'source', 'notes'}, keys, 'price entry')
        for key in ('provider', 'billing_scope', 'model', 'service_tier', 'source', 'notes'):
            if key in entry:
                text_value(entry[key], 'price entry.' + key)
        selector = tuple(entry[key] for key in ('provider', 'billing_scope', 'model', 'service_tier'))
        require(selector not in selectors, 'prices: duplicate model/service selector')
        selectors.add(selector)
        start = timestamp(entry['valid_from'], 'price.valid_from')
        end = timestamp(entry['valid_until'], 'price.valid_until')
        require(start < end, 'prices: validity interval must be nonempty')
        tiers = rows(entry['input_tiers'], 'price.input_tiers', 100)
        require(bool(tiers), 'prices: at least one input tier required')
        previous = -1
        for index, tier in enumerate(tiers):
            fields(tier, {'max_input_tokens', 'rates_per_million'},
                   {'max_input_tokens', 'rates_per_million'}, 'price tier')
            maximum = integer(tier['max_input_tokens'], 'tier.max_input_tokens', nullable=True)
            if maximum is None:
                require(index == len(tiers) - 1, 'prices: unbounded tier must be last')
            else:
                require(maximum > previous, 'prices: input boundaries must strictly increase')
                previous = maximum
            fields(tier['rates_per_million'], RATE_KEYS, RATE_KEYS, 'token rates')
            for key in RATE_KEYS:
                money(tier['rates_per_million'][key], 'rate.' + key, nullable=True)
        require(tiers[-1]['max_input_tokens'] is None, 'prices: final unbounded tier required')
        require(type(entry['tool_rates_per_unit']) is dict, 'prices: tool rates object required')
        require(len(entry['tool_rates_per_unit']) <= 1000, 'prices: too many tool rates')
        for key, rate in entry['tool_rates_per_unit'].items():
            text_value(key, 'tool rate name')
            money(rate, 'tool unit rate', nullable=True)
    return document


def validate_request(row):
    fields(row, REQUEST_FIELDS, {'kind'}, 'request')
    require(row['kind'] in ('actual', 'hypothetical'), 'request: kind must be actual or hypothetical')
    for key in ('provider', 'billing_scope', 'request_id', 'price_version', 'model',
                'service_tier', 'cache_policy', 'output_policy', *IDENTITY_METADATA):
        text_value(row.get(key), 'request.' + key, nullable=True)
    timestamp(row.get('timestamp'), 'request.timestamp', nullable=True)
    sha_value(row.get('price_sha256'), 'request.price_sha256', nullable=True)
    for key in ('input_total', *RATE_KEYS, 'reasoning'):
        integer(row.get(key), 'request.' + key, nullable=True)
    require(row.get('cache_policy') in (None, 'disjoint_v1'), 'request: unsupported cache_policy')
    require(row.get('output_policy') in (None, 'includes_reasoning'), 'request: unsupported output_policy')
    total = row.get('input_total')
    components = [row.get(key) for key in ('noncached_input', 'cache_read', 'cache_write')]
    if total is not None:
        require(sum(value for value in components if value is not None) <= total,
                'request: known input partition exceeds input_total')
        if all(value is not None for value in components):
            require(sum(components) == total, 'request: input partition does not equal input_total')
    if row.get('reasoning') is not None and row.get('output') is not None:
        require(row['reasoning'] <= row['output'], 'request: reasoning exceeds inclusive output')
    tools = row.get('tools')
    if tools is not None:
        fields(tools, {'none', 'charges', 'evidence'}, {'evidence'}, 'request.tools')
        text_value(tools['evidence'], 'tools.evidence')
        require(('none' in tools) != ('charges' in tools), 'tools: exactly one of none or charges required')
        if 'none' in tools:
            require(tools['none'] is True, 'tools.none must be true with evidence')
        else:
            charges = rows(tools['charges'], 'tools.charges', 1000)
            require(bool(charges), 'tools: empty charges must use evidenced none')
            names = set()
            for charge in charges:
                fields(charge, {'name', 'units'}, {'name', 'units'}, 'tool charge')
                name = text_value(charge['name'], 'tool.name')
                require(name not in names, 'tools: repeated name must be consolidated explicitly')
                names.add(name)
                integer(charge['units'], 'tool.units', nullable=True)


def request_cost(row, catalogs):
    unknown = []
    subtotal = Decimal(0)
    binding = (row.get('price_version'), row.get('price_sha256'))
    document = catalogs.get(binding)
    if document is None:
        unknown.append('historical_price_binding_missing_or_unavailable')
    elif row['kind'] == 'actual' and document['status'] != 'verified_reference':
        unknown.append('hypothetical_price_cannot_price_actual_usage')
        document = None
    selector_keys = ('provider', 'billing_scope', 'model', 'service_tier')
    selector = tuple(row.get(key) for key in selector_keys)
    entry = None
    if document is not None:
        entry = next((item for item in document['entries']
                      if tuple(item[key] for key in selector_keys) == selector), None)
        if entry is None:
            unknown.append('exact_provider_scope_model_service_price_unavailable')
    when = timestamp(row.get('timestamp'), 'request.timestamp', nullable=True)
    if entry is not None:
        if when is None:
            unknown.append('request_timestamp_missing')
            entry = None
        elif not (timestamp(entry['valid_from'], 'valid_from') <= when
                  < timestamp(entry['valid_until'], 'valid_until')):
            unknown.append('request_outside_reference_validity')
            entry = None
    total_input = row.get('input_total')
    tier = None
    if entry is not None and total_input is not None:
        tier = next(item for item in entry['input_tiers']
                    if item['max_input_tokens'] is None or total_input <= item['max_input_tokens'])
    if total_input is None:
        unknown.append('input_total_missing_tier_unknown')
    if row.get('cache_policy') is None:
        unknown.append('input_cache_semantics_missing')
    if row.get('output_policy') is None:
        unknown.append('output_reasoning_semantics_missing')
    for key in sorted(RATE_KEYS):
        count = row.get(key)
        if count is None:
            unknown.append(key + '_tokens_missing')
            continue
        semantics_known = row.get('output_policy') is not None if key == 'output' else row.get('cache_policy') is not None
        if not semantics_known:
            continue
        if tier is not None:
            rate = money(tier['rates_per_million'][key], 'rate', nullable=True)
            if rate is None and count:
                unknown.append(key + '_rate_unverified')
            elif rate is not None:
                subtotal += Decimal(count) * rate / Decimal(1000000)
    tools = row.get('tools')
    if tools is None:
        unknown.append('tool_usage_or_fees_missing')
    elif 'charges' in tools:
        for charge in tools['charges']:
            units = charge['units']
            if units is None:
                unknown.append('tool_units_missing')
                continue
            if entry is not None:
                rate = money(entry['tool_rates_per_unit'].get(charge['name']), 'tool rate', nullable=True)
                if rate is None and units:
                    unknown.append('tool_fee_unverified')
                elif rate is not None:
                    subtotal += Decimal(units) * rate
    return subtotal, sorted(set(unknown)), tier['max_input_tokens'] if tier is not None else None


def estimate_many(usage, price_snapshots):
    schema(usage, {'requests'}, {'requests'}, 'usage')
    records = rows(usage['requests'], 'usage.requests')
    catalogs = {}
    for document, digest in price_snapshots:
        validate_prices(document)
        sha_value(digest, 'price file hash')
        binding = (document['version'], digest)
        require(binding not in catalogs, 'prices: duplicate supplied snapshot')
        catalogs[binding] = document
    require(bool(catalogs), 'prices: at least one snapshot required')
    # Validate every record, including duplicate records, before any aggregation.
    for row in records:
        validate_request(row)
    seen = {}
    duplicate_count = 0
    unconfirmed = 0
    details = []
    groups = {kind: {'subtotal': Decimal(0), 'unknown_records': 0, 'unique_records': 0}
              for kind in ('actual', 'hypothetical')}
    with localcontext() as context:
        context.prec = 100
        for index, row in enumerate(records):
            identity = tuple(row.get(key) for key in ('provider', 'billing_scope', 'request_id'))
            if all(value is not None for value in identity):
                facts = {key: row.get(key) for key in REQUEST_FIELDS - IDENTITY_METADATA}
                if identity in seen:
                    require(seen[identity] == facts, 'request identity: conflicting billing facts')
                    duplicate_count += 1
                    continue
                seen[identity] = facts
            else:
                unconfirmed += 1
            subtotal, reasons, boundary = request_cost(row, catalogs)
            if any(value is None for value in identity):
                reasons.append('request_identity_missing_deduplication_unconfirmed')
            group = groups[row['kind']]
            group['subtotal'] += subtotal
            group['unique_records'] += 1
            group['unknown_records'] += bool(reasons)
            details.append({'record_index': index, 'kind': row['kind'],
                            'status': 'unknown' if reasons else 'known',
                            'known_subtotal_usd': dollars(subtotal),
                            'unknown_reasons': reasons,
                            'tier_max_input_tokens': boundary,
                            'deduplication_confirmed': all(value is not None for value in identity)})
    result = {'schema_version': 1, 'currency': 'USD', 'basis': 'offline_reference_estimate_not_invoice',
              'codex_subscription_usage': 'unknown', 'duplicate_records': duplicate_count,
              'deduplication_unconfirmed_records': unconfirmed, 'requests': details,
              'price_snapshots': [{'version': version, 'sha256': digest} for version, digest in catalogs]}
    for kind, group in groups.items():
        known = bool(group['unique_records']) and not group['unknown_records']
        result[kind] = {'status': 'not_supplied' if not group['unique_records'] else 'known' if known else 'unknown',
                        'known_subtotal_usd': dollars(group['subtotal']),
                        'total_usd': dollars(group['subtotal']) if known else None,
                        'unique_records': group['unique_records'],
                        'unknown_records': group['unknown_records']}
    return result


def estimate(usage, price_document, price_sha256):
    """Convenience API; callers supply the actual raw-byte snapshot hash."""
    return estimate_many(usage, [(price_document, price_sha256)])


def check_budget(ledger):
    keys = {'currency', 'actor', 'controller', 'authorized_budget', 'spent', 'reservations', 'proposals'}
    schema(ledger, keys, keys, 'budget ledger')
    require(ledger['currency'] == 'USD', 'budget: only USD supported')
    actor = text_value(ledger['actor'], 'budget.actor')
    controller = ledger['controller']
    fields(controller, {'id', 'confirmed', 'active_claimants'}, {'id', 'confirmed', 'active_claimants'}, 'controller')
    owner = text_value(controller['id'], 'controller.id')
    boolean(controller['confirmed'], 'controller.confirmed')
    claimants = rows(controller['active_claimants'], 'controller.active_claimants', 1000)
    for claimant in claimants:
        text_value(claimant, 'controller claimant')
    control = controller['confirmed'] and claimants == [owner] and actor == owner
    amount_limit = money(ledger['authorized_budget'], 'authorized_budget')
    spent = ledger['spent']
    fields(spent, {'amount', 'complete'}, {'amount', 'complete'}, 'spent')
    confirmed_spent = money(spent['amount'], 'spent.amount')
    complete = boolean(spent['complete'], 'spent.complete')
    reservations = rows(ledger['reservations'], 'reservations')
    proposals = rows(ledger['proposals'], 'proposals')
    ids = set()
    retained = Decimal(0)
    unknown = not complete
    pending_proposals = []
    with localcontext() as context:
        context.prec = 100
        for reservation in reservations:
            keys = {'id', 'problem_id', 'amount', 'state', 'usage_reconciled'}
            fields(reservation, keys, keys, 'reservation')
            item_id = text_value(reservation['id'], 'reservation.id')
            require(item_id not in ids, 'budget: duplicate reservation/proposal id')
            ids.add(item_id)
            text_value(reservation['problem_id'], 'reservation.problem_id')
            amount = money(reservation['amount'], 'reservation.amount', nullable=True)
            require(reservation['state'] in ('in_flight', 'cancel_requested', 'unknown', 'settled', 'cancelled_confirmed'),
                    'reservation: invalid state')
            reconciled = boolean(reservation['usage_reconciled'], 'reservation.usage_reconciled')
            released = reservation['state'] in ('settled', 'cancelled_confirmed') and reconciled
            if not released:
                if amount is None:
                    unknown = True
                else:
                    retained += amount
        for proposal in proposals:
            keys = {'id', 'problem_id', 'work', 'review', 'closeout'}
            fields(proposal, keys | {'zero_cost_evidence'}, keys, 'proposal')
            item_id = text_value(proposal['id'], 'proposal.id')
            require(item_id not in ids, 'budget: duplicate reservation/proposal id')
            ids.add(item_id)
            text_value(proposal['problem_id'], 'proposal.problem_id')
            parts = [money(proposal[key], 'proposal.' + key) for key in ('work', 'review', 'closeout')]
            if any(part == 0 for part in parts) or 'zero_cost_evidence' in proposal:
                text_value(proposal.get('zero_cost_evidence'), 'proposal.zero_cost_evidence')
            required = sum(parts, Decimal(0))
            pending_proposals.append((item_id, required))
        available = amount_limit - confirmed_spent - retained
        decisions = []
        for item_id, required in pending_proposals:
            reason = ('control_unconfirmed' if not control else 'existing_cost_or_reservation_unknown' if unknown
                      else 'insufficient_budget' if required > available else None)
            if reason is None:
                available -= required
            decisions.append({'id': item_id, 'required_usd': dollars(required),
                              'decision': 'deny' if reason else 'allow', 'reason': reason})
    return {'schema_version': 1, 'currency': 'USD', 'basis': 'offline_simulation_no_allocation_or_lock',
            'status': 'unknown' if unknown else 'checked', 'control_confirmed': control,
            'confirmed_spent_usd': dollars(confirmed_spent), 'retained_reservations_usd': dollars(retained),
            'remaining_after_proposals_usd': None if unknown else dollars(available), 'proposals': decisions,
            'runtime_exclusivity_verified': False, 'hard_cap_guaranteed': False}


def check_retry(config):
    keys = {'retry_layers', 'max_attempts', 'initial_backoff_seconds', 'max_backoff_seconds',
            'jitter', 'respect_retry_after', 'concurrency'}
    schema(config, keys, keys, 'retry configuration')
    layers = rows(config['retry_layers'], 'retry_layers', 2)
    require(len(layers) <= 1 and all(layer in ('sdk', 'outer') for layer in layers),
            'retry: exactly one retry layer at most')
    attempts = integer(config['max_attempts'], 'max_attempts', minimum=1, maximum=10)
    require(bool(layers) == (attempts > 1), 'retry: layer required exactly when retrying')
    first = money(config['initial_backoff_seconds'], 'initial_backoff_seconds')
    maximum = money(config['max_backoff_seconds'], 'max_backoff_seconds')
    require(0 < first <= maximum <= 3600, 'retry: backoff must satisfy 0 < initial <= max <= 3600')
    concurrency = integer(config['concurrency'], 'concurrency', minimum=1, maximum=MAX_ROWS)
    require(config['jitter'] in ('none', 'full'), 'retry: unknown jitter policy')
    if concurrency > 1 and attempts > 1:
        require(config['jitter'] == 'full', 'retry: concurrent retries require full jitter')
    require(config['respect_retry_after'] is True, 'retry: must honor Retry-After or stop if it exceeds allowed wait')
    return {'schema_version': 1, 'status': 'valid_offline_configuration',
            'max_attempts_including_first': attempts, 'max_backoff_seconds': dollars(maximum),
            'retry_after_policy': 'wait_at_least_server_delay_or_stop',
            'runtime_enforcement_verified': False, 'requests_sent': 0}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    subcommands = result.add_subparsers(dest='command', required=True)
    estimate_parser = subcommands.add_parser('estimate', help='Estimate supplied records against bound local price snapshots.')
    estimate_parser.add_argument('--usage', required=True, help='Schema 1 JSON usage file (no secrets/prompts needed).')
    estimate_parser.add_argument('--prices', required=True, action='append', help='Price JSON snapshot; repeat for historical versions.')
    budget_parser = subcommands.add_parser('budget', help='Simulate sequential reservations; never allocate or lock a real budget.')
    budget_parser.add_argument('--ledger', required=True, help='Schema 1 ledger with controller and review/closeout reserves.')
    retry_parser = subcommands.add_parser('retry', help='Validate a bounded single-layer retry policy; never send requests.')
    retry_parser.add_argument('--config', required=True, help='Schema 1 retry policy JSON.')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'estimate':
            usage, _digest = read_json(args.usage)
            result = estimate_many(usage, [read_json(path) for path in args.prices])
        elif args.command == 'budget':
            ledger, _digest = read_json(args.ledger)
            result = check_budget(ledger)
        else:
            config, _digest = read_json(args.config)
            result = check_retry(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == 'budget' and (not result['control_confirmed'] or result['status'] == 'unknown'
                                        or any(item['decision'] == 'deny' for item in result['proposals'])):
            return 3
        return 0
    except (ContractError, OSError) as exc:
        message = str(exc) if isinstance(exc, ContractError) else 'Cannot read specified local input file.'
        print(json.dumps({'status': 'error', 'message': message}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
