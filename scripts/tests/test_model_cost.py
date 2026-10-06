"""Independent hand-calculated billing and fail-closed offline policy cases."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'model_cost.py'
spec = importlib.util.spec_from_file_location('model_cost', SCRIPT)
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)


def prices():
    return {'schema_version': 1, 'version': 'fixture-old', 'currency': 'USD',
            'status': 'verified_reference', 'verified_at': '2026-09-15',
            'source': 'https://example.invalid/test-only',
            'scope_note': 'Unit-test fixture only, never a real quotation.',
            'entries': [{'provider': 'fixture', 'billing_scope': 'direct-api',
                         'model': 'exact-model', 'service_tier': 'standard',
                         'valid_from': '2026-01-01T00:00:00Z',
                         'valid_until': '2027-01-01T00:00:00Z',
                         'input_tiers': [
                             {'max_input_tokens': 100000, 'rates_per_million':
                              {'noncached_input': '2', 'cache_read': '0.5',
                               'cache_write': '3', 'output': '8'}},
                             {'max_input_tokens': None, 'rates_per_million':
                              {'noncached_input': '4', 'cache_read': '1',
                               'cache_write': '6', 'output': '12'}}],
                         'tool_rates_per_unit': {'search': '0.01'}}]}


HASH = 'a' * 64


def request(**changes):
    value = {'kind': 'actual', 'provider': 'fixture', 'billing_scope': 'direct-api',
             'request_id': 'req-1', 'timestamp': '2026-09-15T00:00:00Z',
             'price_version': 'fixture-old', 'price_sha256': HASH,
             'model': 'exact-model', 'service_tier': 'standard',
             'input_total': 1000, 'noncached_input': 600, 'cache_read': 300,
             'cache_write': 100, 'output': 200, 'reasoning': 150,
             'cache_policy': 'disjoint_v1', 'output_policy': 'includes_reasoning',
             'tools': {'none': True, 'evidence': 'Fixture declares no tools.'}}
    value.update(changes)
    return value


def estimate(rows, price=None):
    return mc.estimate({'schema_version': 1, 'requests': rows}, price or prices(), HASH)


def ledger():
    return {'schema_version': 1, 'currency': 'USD', 'actor': 'owner',
            'controller': {'id': 'owner', 'confirmed': True, 'active_claimants': ['owner']},
            'authorized_budget': '10', 'spent': {'amount': '3', 'complete': True},
            'reservations': [{'id': 'r1', 'problem_id': 'same-question', 'amount': '2',
                              'state': 'cancel_requested', 'usage_reconciled': False}],
            'proposals': [{'id': 'p1', 'problem_id': 'q1', 'work': '3',
                           'review': '1', 'closeout': '1'},
                          {'id': 'p2', 'problem_id': 'q2', 'work': '0.01',
                           'review': '0', 'closeout': '0', 'zero_cost_evidence': 'Local review and closeout need no API call.'}]}


def retry():
    return {'schema_version': 1, 'retry_layers': ['outer'], 'max_attempts': 3,
            'initial_backoff_seconds': '1', 'max_backoff_seconds': '30',
            'jitter': 'full', 'respect_retry_after': True, 'concurrency': 32}


class Billing(unittest.TestCase):
    def test_T20_exact_duplicate_and_real_retry(self):
        one = request(prompt_ref='same-public-fixture')
        result = estimate([one, copy.deepcopy(one), request(request_id='retry-2',
                                                          prompt_ref='same-public-fixture')])
        # 600*2/1e6 + 300*.5/1e6 + 100*3/1e6 + 200*8/1e6 = .00325
        self.assertEqual(result['actual']['total_usd'], '0.0065')
        self.assertEqual(result['duplicate_records'], 1)
        self.assertEqual(result['actual']['unique_records'], 2)

    def test_T20_conflicting_fact_fails(self):
        for change in ({'output': 201}, {'model': 'alias'}, {'service_tier': 'priority'},
                       {'price_version': 'new'}, {'kind': 'hypothetical'}):
            with self.subTest(change=change), self.assertRaises(mc.ContractError):
                estimate([request(), request(**change)])

    def test_T20_scope_provider_and_missing_id(self):
        other = copy.deepcopy(prices()['entries'][0]); other['billing_scope'] = 'other'
        p = prices(); p['entries'].append(other)
        result = estimate([request(), request(billing_scope='other'),
                           request(request_id=None), request(request_id=None)], p)
        self.assertEqual(result['actual']['known_subtotal_usd'], '0.013')
        self.assertIsNone(result['actual']['total_usd'])
        self.assertEqual(result['deduplication_unconfirmed_records'], 2)
        other = copy.deepcopy(other); other['provider'] = 'second'; p['entries'].append(other)
        self.assertEqual(estimate([request(), request(provider='second', billing_scope='other')], p)
                         ['actual']['unique_records'], 2)

    def test_T21_reasoning_and_disjoint_cache_and_tool(self):
        result = estimate([request(tools={'charges': [{'name': 'search', 'units': 2}],
                                         'evidence': 'Two recorded fixture calls.'})])
        self.assertEqual(result['actual']['total_usd'], '0.02325')
        self.assertEqual(estimate([request(reasoning=0)])['actual']['total_usd'], '0.00325')
        for change in ({'cache_read': 1001}, {'noncached_input': 601}, {'reasoning': 201}):
            with self.subTest(change=change), self.assertRaises(mc.ContractError):
                estimate([request(**change)])

    def test_T21_service_price_is_explicit_tool_fee_not_scaled(self):
        p = prices(); priority = copy.deepcopy(p['entries'][0]); priority['service_tier'] = 'priority'
        priority['input_tiers'][0]['rates_per_million']['output'] = '16'
        p['entries'].append(priority)
        result = estimate([request(service_tier='priority', tools={'charges': [
            {'name': 'search', 'units': 2}], 'evidence': 'Fixture.'})], p)
        self.assertEqual(result['actual']['total_usd'], '0.02485')

    def test_T22_missing_facts_and_unknown_alias(self):
        for key in ('model', 'service_tier', 'output', 'input_total', 'cache_policy',
                    'output_policy', 'tools', 'timestamp', 'price_version', 'price_sha256'):
            row = request(); del row[key]
            with self.subTest(key=key):
                result = estimate([row])['actual']
                self.assertEqual(result['status'], 'unknown')
                self.assertIsNone(result['total_usd'])
        self.assertEqual(estimate([request(model='unverified-alias')])['actual']['status'], 'unknown')
        result = estimate([request(tools={'charges': [{'name': 'unknown-tool', 'units': 1}],
                                         'evidence': 'Recorded event.'})])
        self.assertEqual(result['actual']['known_subtotal_usd'], '0.00325')
        result = estimate([request(output=None)])
        self.assertEqual(result['actual']['known_subtotal_usd'], '0.00165')

    def test_T22_illegal_numbers_strict_json_and_unknown_fields(self):
        for value in (-1, True, '5', 1.5, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(mc.ContractError):
                estimate([request(output=value)])
        for payload in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}',
                        '{"x":1e999999999999999999999999999999999999}',
                        '{"x":1e-999999999999999999999999999999999999}'):
            with self.subTest(payload=payload), self.assertRaises(mc.ContractError):
                mc.decode_json(payload)
        with self.assertRaises(mc.ContractError): estimate([request(service_multplier=2)])
        for bad in ('NaN', 'Infinity', '-1', True):
            p = prices(); p['entries'][0]['input_tiers'][0]['rates_per_million']['output'] = bad
            with self.subTest(bad=bad), self.assertRaises(mc.ContractError): estimate([request()], p)

    def test_T22_hypothetical_is_separate_and_never_actual_price(self):
        result = estimate([request(), request(kind='hypothetical', request_id='hypo-1')])
        self.assertEqual(result['actual']['total_usd'], '0.00325')
        self.assertEqual(result['hypothetical']['total_usd'], '0.00325')
        p = prices(); p['status'] = 'hypothetical'
        result = estimate([request(), request(kind='hypothetical', request_id='hypo-1')], p)
        self.assertEqual(result['actual']['status'], 'unknown')
        self.assertEqual(result['hypothetical']['status'], 'known')

    def test_T23_32_short_requests_do_not_trigger_long_tier(self):
        rows = [request(request_id=f'req-{i}', input_total=100000, noncached_input=100000,
                        cache_read=0, cache_write=0, output=0, reasoning=0) for i in range(32)]
        self.assertEqual(estimate(rows)['actual']['total_usd'], '6.4')
        long = request(input_total=100001, noncached_input=100001, cache_read=0,
                       cache_write=0, output=100, reasoning=0)
        self.assertEqual(estimate([long])['actual']['total_usd'], '0.401204')

    def test_T23_history_hash_version_and_validity(self):
        for change in ({'price_version': 'new'}, {'price_sha256': 'b'*64},
                       {'timestamp': '2027-01-01T00:00:00Z'}):
            with self.subTest(change=change):
                self.assertEqual(estimate([request(**change)])['actual']['status'], 'unknown')
        with self.assertRaises(mc.ContractError): estimate([request(timestamp='2026-99-20')])


    def test_T23_multiple_bound_snapshots_keep_old_request_price(self):
        old = prices(); new = copy.deepcopy(old); new['version'] = 'fixture-new'
        new['entries'][0]['input_tiers'][0]['rates_per_million']['noncached_input'] = '4'
        rows = [request(), request(request_id='new-call', price_version='fixture-new', price_sha256='b'*64)]
        result = mc.estimate_many({'schema_version': 1, 'requests': rows}, [(old, HASH), (new, 'b'*64)])
        self.assertEqual(result['requests'][0]['known_subtotal_usd'], '0.00325')
        self.assertEqual(result['requests'][1]['known_subtotal_usd'], '0.00445')
        self.assertEqual(result['actual']['total_usd'], '0.0077')

    def test_official_reference_unknown_long_cache_is_not_zero(self):
        document, digest = mc.read_json(SCRIPT.parent/'model-prices.json')
        row = request(kind='hypothetical', provider='openai', model='gpt-5.6-luna',
                      price_version=document['version'], price_sha256=digest,
                      input_total=272001, noncached_input=272000, cache_read=1,
                      cache_write=0, output=200)
        result = mc.estimate({'schema_version': 1, 'requests': [row]}, document, digest)
        self.assertIsNone(result['hypothetical']['total_usd'])
        self.assertEqual(result['hypothetical']['known_subtotal_usd'], '0.10916')
        self.assertIn('cache_read_rate_unverified', result['requests'][0]['unknown_reasons'])
        row.update(noncached_input=272001, cache_read=0)
        self.assertEqual(mc.estimate({'schema_version': 1, 'requests': [row]}, document, digest)
                         ['hypothetical']['total_usd'], '0.1091604')

    def test_no_records_do_not_claim_zero_actual_bill(self):
        result = estimate([])
        self.assertEqual(result['actual']['status'], 'not_supplied')
        self.assertIsNone(result['actual']['total_usd'])

class BudgetAndRetry(unittest.TestCase):
    def test_T19_unique_controller_and_unconfirmed_cancel(self):
        value = ledger(); result = mc.check_budget(value)
        self.assertEqual(result['retained_reservations_usd'], '2')
        self.assertEqual([p['decision'] for p in result['proposals']], ['allow', 'deny'])
        for state in ('unknown', 'cancel_requested', 'settled', 'cancelled_confirmed'):
            value = ledger(); value['reservations'][0]['state'] = state
            self.assertEqual(mc.check_budget(value)['retained_reservations_usd'], '2')
        value = ledger(); value['controller']['active_claimants'].append('other-session')
        self.assertTrue(all(p['decision'] == 'deny' for p in mc.check_budget(value)['proposals']))
        value = ledger(); value['actor'] = 'different'
        self.assertFalse(mc.check_budget(value)['control_confirmed'])

    def test_T19_release_only_terminal_and_reconciled(self):
        value = ledger(); value['reservations'][0].update(state='cancelled_confirmed', usage_reconciled=True)
        self.assertEqual(mc.check_budget(value)['retained_reservations_usd'], '0')
        value['reservations'][0]['state'] = 'in_flight'
        self.assertEqual(mc.check_budget(value)['retained_reservations_usd'], '2')

    def test_T24_atomic_batch_simulation_reserves_review_closeout(self):
        result = mc.check_budget(ledger())
        self.assertEqual(result['proposals'][0]['required_usd'], '5')
        self.assertEqual(result['remaining_after_proposals_usd'], '0')
        value = ledger(); value['reservations'][0]['amount'] = None
        self.assertEqual(mc.check_budget(value)['status'], 'unknown')
        self.assertTrue(all(p['decision'] == 'deny' for p in mc.check_budget(value)['proposals']))
        value = ledger(); value['spent']['complete'] = False
        self.assertEqual(mc.check_budget(value)['status'], 'unknown')
        value = ledger(); del value['proposals'][1]['zero_cost_evidence']
        with self.assertRaises(mc.ContractError): mc.check_budget(value)
        value = ledger(); del value['proposals'][0]['review']
        with self.assertRaises(mc.ContractError): mc.check_budget(value)
        value = ledger(); value['proposals'].append(copy.deepcopy(value['proposals'][0]))
        with self.assertRaises(mc.ContractError): mc.check_budget(value)

    def test_T24_single_layer_bounded_jittered_retry(self):
        self.assertEqual(mc.check_retry(retry())['status'], 'valid_offline_configuration')
        for change in ({'retry_layers': ['sdk', 'outer']}, {'max_attempts': 0},
                       {'max_attempts': True}, {'max_attempts': 11}, {'jitter': 'none'},
                       {'max_backoff_seconds': '0'}, {'respect_retry_after': False}):
            value = retry(); value.update(change)
            with self.subTest(change=change), self.assertRaises(mc.ContractError): mc.check_retry(value)
        value = retry(); value.update(retry_layers=[], max_attempts=1)
        self.assertEqual(mc.check_retry(value)['status'], 'valid_offline_configuration')


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, timeout=10)

    def test_excessive_json_decimal_exponent_is_structured_error(self):
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp)/'bad.json'
            bad.write_text('{"x":1e999999999999999999999999999999999999}', encoding='utf-8')
            result = self.run_cli('retry', '--config', bad)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stderr)['status'], 'error')
            self.assertNotIn('Traceback', result.stderr)

    def test_each_command_help_success_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); p = root/'prices.json'; u = root/'usage.json'; b = root/'budget.json'; r = root/'retry.json'
            p.write_text(json.dumps(prices()), encoding='utf-8')
            row = request(price_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            u.write_text(json.dumps({'schema_version': 1, 'requests': [row]}), encoding='utf-8')
            value = ledger(); value['proposals'] = value['proposals'][:1]
            b.write_text(json.dumps(value), encoding='utf-8'); r.write_text(json.dumps(retry()), encoding='utf-8')
            for cmd, args in (('estimate', ('--usage', u, '--prices', p)),
                              ('budget', ('--ledger', b)), ('retry', ('--config', r))):
                with self.subTest(command=cmd):
                    self.assertEqual(self.run_cli(cmd, '--help').returncode, 0)
                    success = self.run_cli(cmd, *args)
                    self.assertEqual(success.returncode, 0, success.stderr)
                    self.assertIsInstance(json.loads(success.stdout), dict)
                    bad = root/'bad.json'; bad.write_text('{"schema_version":99}', encoding='utf-8')
                    failure = self.run_cli(cmd, args[0], bad, *(args[2:] if cmd == 'estimate' else ()))
                    self.assertEqual(failure.returncode, 2, failure.stdout)
                    self.assertEqual(json.loads(failure.stderr)['status'], 'error')


if __name__ == '__main__':
    unittest.main()
