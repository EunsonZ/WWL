"""Deterministic boundary tests of the v2 teaching contracts, no external tools or I/O."""
from __future__ import annotations
import importlib
import math
import socket
import unittest
from unittest import mock
import reasoning_lab as lab
import generate_reasoning_fixtures as fixtures
import hashlib
import json
from pathlib import Path
import tempfile


def xml(ports: str = '', *, exit: str | None = 'success', extra: str = '', address: str = '127.0.0.1') -> bytes:
    finish = f'<runstats><finished exit="{exit}"/></runstats>' if exit is not None else ''
    return (f'<nmaprun><scaninfo protocol="tcp" services="22,8000"/>'
            f'<host><status state="up"/><address addrtype="ipv4" addr="{address}"/>'
            f'<ports>{ports}</ports></host>{finish}{extra}</nmaprun>').encode()


def port(n: int | str, state: str = 'open', protocol: str = 'tcp') -> str:
    return f'<port protocol="{protocol}" portid="{n}"><state state="{state}" reason="synthetic"/></port>'


class RouteTests(unittest.TestCase):
    def test_longest_prefix_precedes_metric(self):
        routes = [lab.Route('0.0.0.0/0','wan',0), lab.Route('192.168.56.0/24','lab',1),
                  lab.Route('192.168.56.32/27','narrow',999)]
        self.assertEqual(lab.choose_route('192.168.56.37',routes).interface,'narrow')
    def test_metric_breaks_equal_prefix(self):
        self.assertEqual(lab.choose_route('192.0.2.3',[lab.Route('192.0.2.0/24','a',9),
                         lab.Route('192.0.2.0/24','b',3)]).interface,'b')
    def test_equal_cost_is_not_input_order(self):
        with self.assertRaises(lab.InputError):
            lab.choose_route('192.0.2.3',[lab.Route('192.0.2.0/24','a'),lab.Route('192.0.2.0/24','b')])
    def test_no_route_is_none(self):
        self.assertIsNone(lab.choose_route('192.0.2.3',[lab.Route('198.51.100.0/24','other')]))
        self.assertIsNone(lab.choose_route('192.0.2.3',[]))
    def test_v4_default_does_not_match_v6(self):
        self.assertIsNone(lab.choose_route('2001:db8::1',[lab.Route('0.0.0.0/0','wan')]))
    def test_v6_longest(self):
        self.assertEqual(lab.choose_route('2001:db8:1::7',[lab.Route('::/0','default'),
                         lab.Route('2001:db8:1::/64','v6lab',8)]).interface,'v6lab')
    def test_prefix_has_no_host_bits(self):
        with self.assertRaises(lab.InputError): lab.Route('192.168.56.37/27','lab')
    def test_route_invalid_fields(self):
        for prefix,interface,metric in [('192.0.2.0/24','x',True),('192.0.2.0/24','x',-1),
                                       ('192.0.2.0/24','',0),('192.0.2.0/24','a b',0),('192.0.2.0','x',0)]:
            with self.subTest(prefix=prefix,interface=interface,metric=metric):
                with self.assertRaises(lab.InputError): lab.Route(prefix,interface,metric)
    def test_invalid_destination_and_collection(self):
        for address in ['example.com','192.0.2.0/24','fe80::1%eth0',None,1]:
            with self.assertRaises(lab.InputError): lab.choose_route(address,[])
        with self.assertRaises(lab.InputError): lab.choose_route('127.0.0.1',[{}])
    def test_observation_depends_on_probe(self):
        self.assertEqual(lab.infer_scan_state('tcp_syn','no_response'),'filtered')
        self.assertEqual(lab.infer_scan_state('udp','no_response'),'open|filtered')
        self.assertEqual(lab.infer_scan_state('udp','icmp_port_unreachable'),'closed')
        with self.assertRaises(lab.InputError): lab.infer_scan_state('udp','rst')


class ScanTests(unittest.TestCase):
    def test_explicit_change(self):
        rows = lab.compare_scans(lab.parse_scan_xml(xml(port(8000))),lab.parse_scan_xml(xml(port(8000,'closed'))))
        self.assertEqual((rows[0]['before'],rows[0]['after'],rows[0]['relation']),('open','closed','explicit_change'))
    def test_missing_is_not_closed(self):
        rows=lab.compare_scans(lab.parse_scan_xml(xml(port(22))),lab.parse_scan_xml(xml('')))
        self.assertEqual((rows[0]['after'],rows[0]['relation']),('not_observed','coverage_gap'))
    def test_new_observation_preserves_missing_before(self):
        rows=lab.compare_scans(lab.parse_scan_xml(xml('')),lab.parse_scan_xml(xml(port(443))))
        self.assertEqual(rows[0]['before'],'not_observed')
    def test_incomplete_status_survives_comparison(self):
        rows=lab.compare_scans(lab.parse_scan_xml(xml(port(22))),lab.parse_scan_xml(xml(port(22,'closed'),exit='error')))
        self.assertEqual(rows[0]['after_finished'],'error')
    def test_missing_finished_is_unknown(self):
        self.assertEqual(lab.parse_scan_xml(xml(exit=None)).finished,'unknown')
    def test_aggregate_does_not_create_individual_ports(self):
        snapshot=lab.parse_scan_xml(xml('<extraports state="closed" count="100"/>'))
        self.assertEqual(snapshot.ports,())
        self.assertEqual(snapshot.aggregates,(('127.0.0.1','closed',100),))
    def test_protocol_is_part_of_identity(self):
        snapshot=lab.parse_scan_xml(xml(port(53,'open','tcp')+port(53,'closed','udp')))
        self.assertEqual(len(snapshot.ports),2)
    def test_plain_nmap_doctype_is_accepted(self):
        snapshot=lab.parse_scan_xml(b'<?xml version="1.0"?><!DOCTYPE nmaprun>'+xml(port(22)))
        self.assertEqual(snapshot.ports[0].port,22)
    def test_internal_entities_are_rejected(self):
        raw=b'<!DOCTYPE nmaprun [<!ENTITY x "nested">]>'+xml(port(22))
        with self.assertRaises(lab.InputError): lab.parse_scan_xml(raw)
    def test_external_doctype_is_rejected(self):
        raw=b'<!DOCTYPE nmaprun SYSTEM "file:///synthetic-not-opened">'+xml('')
        with self.assertRaises(lab.InputError): lab.parse_scan_xml(raw)
    def test_utf16_and_declared_encoding_rejected(self):
        with self.assertRaises(lab.InputError): lab.parse_scan_xml(xml('').decode().encode('utf-16'))
        with self.assertRaises(lab.InputError): lab.parse_scan_xml(b'<?xml version="1.0" encoding="iso-8859-1"?>'+xml(''))
    def test_duplicates_are_not_last_wins(self):
        with self.assertRaises(lab.InputError): lab.parse_scan_xml(xml(port(22)+port(22,'closed')))
        host='<host><address addrtype="ipv4" addr="127.0.0.1"/></host>'
        with self.assertRaises(lab.InputError): lab.parse_scan_xml(xml(extra=host))
    def test_invalid_state_and_port(self):
        for content in [port(22,'vulnerable'),port(-1),port(65536),port('２２')]:
            with self.assertRaises(lab.InputError): lab.parse_scan_xml(xml(content))
    def test_huge_decimal_is_controlled_input_error(self):
        with self.assertRaises(lab.InputError): lab.parse_scan_xml(xml(port('9'*5000)))
        with self.assertRaises(lab.InputError): lab.parse_scan_xml(xml('<extraports state="closed" count="'+'9'*5000+'"/>'))
    def test_malformed_and_size_bounds(self):
        for raw in [b'',b'<nmaprun>',b'<other/>',b'x'*1_048_577]:
            with self.assertRaises(lab.InputError): lab.parse_scan_xml(raw)
    def test_depth_limit(self):
        with self.assertRaises(lab.InputError):
            lab.parse_scan_xml(b'<nmaprun>'+b'<x>'*65+b'</x>'*65+b'</nmaprun>')
    def test_address_family_is_checked(self):
        with self.assertRaises(lab.InputError): lab.parse_scan_xml(xml(address='2001:db8::1'))
        snapshot=lab.parse_scan_xml(xml(address='2001:db8::1').replace(b'addrtype="ipv4"',b'addrtype="ipv6"'))
        self.assertEqual(snapshot.hosts[0][0],'2001:db8::1')
    def test_empty_scan_does_not_invent_failure_or_success(self):
        snapshot=lab.parse_scan_xml(b'<nmaprun/>')
        self.assertEqual(snapshot.finished,'unknown')
        self.assertEqual(lab.compare_scans(snapshot,snapshot),[])


class PolicyTests(unittest.TestCase):
    def test_owner_draft_actions(self):
        for action in ['read','edit','submit']:
            self.assertTrue(lab.allowed('alice',17,action))
        self.assertFalse(lab.allowed('alice',17,'approve'))
    def test_read_permission_does_not_imply_edit(self):
        self.assertTrue(lab.allowed('bob',17,'read'))
        self.assertFalse(lab.allowed('bob',17,'edit'))
    def test_reviewer_approval(self):
        self.assertTrue(lab.allowed('bob',18,'approve'))
        self.assertFalse(lab.allowed('bob',17,'approve'))
    def test_self_approval_is_denied(self):
        self.assertFalse(lab.allowed('bob',20,'approve'))
        self.assertFalse(lab.allowed('carol',19,'approve'))
    def test_cross_tenant_role_does_not_bypass_scope(self):
        self.assertFalse(lab.allowed('carol',18,'read'))
        self.assertFalse(lab.allowed('carol',18,'approve'))
    def test_closed_lifecycle_states(self):
        self.assertFalse(lab.allowed('alice',18,'edit'))
        self.assertFalse(lab.allowed('alice',21,'submit'))
        self.assertFalse(lab.allowed('bob',21,'approve'))
    def test_field_projection(self):
        self.assertEqual(set(lab.project_report('bob',18)),{'id','status','title'})
        self.assertIn('private_note',lab.project_report('alice',18))
    def test_projection_cannot_mutate_registry(self):
        result=lab.project_report('alice',17);result['title']='modified';result['private_note']='modified'
        self.assertEqual(lab.project_report('alice',17)['title'],'Report A')
        self.assertNotEqual(lab.project_report('alice',17)['private_note'],'modified')
    def test_unknowns_fail_closed(self):
        for args in [('unknown',17,'read'),('alice',999,'read'),('alice',17,'delete'),
                     ({'identity':'bob','role':'reviewer'},18,'approve'),('alice',True,'read'),
                     ('alice','17','read'),('alice',17,None),([],17,'read')]:
            self.assertFalse(lab.allowed(*args))
    def test_denied_projection_is_not_empty_success(self):
        with self.assertRaises(PermissionError):lab.project_report('carol',17)


class TimeMetricTests(unittest.TestCase):
    def test_same_instant_different_offsets(self):
        self.assertEqual(lab.utc_timestamp('2026-09-05T16:00:00+08:00'),lab.utc_timestamp('2026-09-05T08:00:00Z'))
    def test_fractional_seconds_preserved(self):
        self.assertEqual(lab.utc_timestamp('2026-09-05T08:00:00.123456Z').microsecond,123456)
    def test_naive_invalid_and_unknown_offset_rejected(self):
        for text in ['2026-09-05T08:00:00','2026-02-30T08:00:00Z','2026-09-05T08:00:60Z',
                     '2026-09-05T08:00:00-00:00','2026-09-05 08:00:00Z',None]:
            with self.assertRaises(lab.InputError):lab.utc_timestamp(text)
    def test_offset_minutes_not_silently_normalized(self):
        for text in ['2026-09-05T08:00:00+01:60','2026-09-05T08:00:00+00:99']:
            with self.assertRaises(lab.InputError):lab.utc_timestamp(text)
    def test_overlap_and_touch_are_not_definite_order(self):
        self.assertFalse(lab.definitely_before('2026-09-05T08:00:00Z',3,'2026-09-05T08:00:02Z',1))
        self.assertFalse(lab.definitely_before('2026-09-05T08:00:00Z',1,'2026-09-05T08:00:02Z',1))
    def test_disjoint_intervals(self):
        self.assertTrue(lab.definitely_before('2026-09-05T08:00:00Z',1,'2026-09-05T08:00:03Z',1))
    def test_invalid_uncertainty(self):
        for error in [-1,True,1.5,86401]:
            with self.assertRaises(lab.InputError):lab.definitely_before('2026-09-05T08:00:00Z',error,'2026-09-05T08:00:03Z',0)
    def test_base_rate_worked_example(self):
        result=lab.detection_metrics(900,9990,989010,100)
        self.assertAlmostEqual(result['precision'],10/121,places=14)
        self.assertEqual(result['recall'],0.9)
        self.assertEqual(result['fpr'],0.01)
    def test_zero_denominators_are_missing(self):
        self.assertEqual(lab.detection_metrics(0,0,0,0),{'precision':None,'recall':None,'fpr':None})
        self.assertEqual(lab.detection_metrics(0,0,10,0)['fpr'],0)
    def test_invalid_counts_rejected(self):
        for invalid in [-1,True,1.5,'1',None]:
            with self.assertRaises(lab.InputError):lab.detection_metrics(invalid,0,0,0)
    def test_entropy_boundaries_and_order_invariance(self):
        self.assertEqual(lab.byte_entropy(b'A'*256),0)
        self.assertEqual(lab.byte_entropy(bytes(range(256))),8)
        self.assertEqual(lab.byte_entropy(b'ABAB'),lab.byte_entropy(b'AABB'))
        self.assertEqual(lab.byte_entropy(b'AB'),1)
    def test_entropy_empty_and_type_contract(self):
        for value in [b'', 'AB', bytearray(b'AB'), b'x'*1_048_577]:
            with self.assertRaises(lab.InputError):lab.byte_entropy(value)


class IsolationTests(unittest.TestCase):
    def test_demo_without_socket_calls(self):
        with mock.patch.object(socket,'socket',side_effect=AssertionError('network forbidden')):
            result=lab.run_demo()
        self.assertFalse(result['network_io'])
        self.assertEqual(result['route']['prefix'],'192.168.56.32/27')
    def test_repeatable_demo(self):
        self.assertEqual(lab.run_demo(),lab.run_demo())



class FixtureV2Tests(unittest.TestCase):
    def test_deterministic_without_network(self):
        with mock.patch.object(socket,'socket',side_effect=AssertionError('network forbidden')):
            self.assertEqual(fixtures.contents(),fixtures.contents())
    def test_manifest_members_and_hashes(self):
        data=fixtures.contents();manifest=json.loads(data['expected-v2.json'])
        self.assertEqual(set(manifest['sha256']),set(data)-{'expected-v2.json'})
        for name,digest in manifest['sha256'].items():
            self.assertEqual(hashlib.sha256(data[name]).hexdigest(),digest)
    def test_generate_existing_target_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'new';fixtures.generate(target)
            with self.assertRaises(FileExistsError):fixtures.generate(target)
            self.assertEqual((target/'scan-before.xml').read_bytes(),fixtures.contents()['scan-before.xml'])
    def test_generate_rejects_observed_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'actual').mkdir();(root/'link').symlink_to(root/'actual',target_is_directory=True)
            with self.assertRaises(ValueError):fixtures.generate(root/'link'/'new')
    def test_route_cases_and_prefix_boundaries(self):
        data=json.loads(fixtures.contents()['route-cases.json'])
        routes=[lab.Route(**item) for item in data['routes']]
        for case in data['cases']:
            result=lab.choose_route(case['destination'],routes)
            self.assertEqual(result.prefix if result else None,case['expected_prefix'])
        for host,prefix in [(31,'192.168.56.0/24'),(32,'192.168.56.32/27'),(63,'192.168.56.32/27'),(64,'192.168.56.0/24')]:
            self.assertEqual(lab.choose_route(f'192.168.56.{host}',routes).prefix,prefix)
    def test_authorization_cases(self):
        data=json.loads(fixtures.contents()['authorization-cases.json'])
        for case in data['cases']:
            self.assertEqual(lab.allowed(case['identity'],case['report_id'],case['action']),case['expected'])
    def test_scan_fixture_retains_uncertainty(self):
        data=fixtures.contents()
        before=lab.parse_scan_xml(data['scan-before.xml']);after=lab.parse_scan_xml(data['scan-after.xml'])
        rows={(r['protocol'],r['port']):r for r in lab.compare_scans(before,after)}
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[('tcp',22)]['after'],'not_observed')
        self.assertEqual(rows[('tcp',8000)]['relation'],'explicit_change')
        self.assertTrue(all(row['after_finished']=='error' for row in rows.values()))
        aggregate=lab.parse_scan_xml(data['scan-aggregate.xml'])
        self.assertEqual([p.port for p in aggregate.ports],[8000])
    def test_time_and_metric_fixture(self):
        files=fixtures.contents();data=json.loads(files['timeline.json']);a,b=data['events']
        self.assertEqual(lab.definitely_before(a['time'],a['uncertainty_seconds'],b['time'],b['uncertainty_seconds']),data['expected_definitely_before'])
        counts=json.loads(files['metrics.json']);metrics=lab.detection_metrics(*(counts[k] for k in ('tp','fp','tn','fn')))
        self.assertAlmostEqual(metrics['precision'],10/121,places=14)
        self.assertEqual(sum(counts[k] for k in ('tp','fp','tn','fn')),counts['population'])
    def test_hand_specified_record_oracle(self):
        cases=json.loads(fixtures.contents()['records.json'])['cases']
        abc=next(c for c in cases if c['name']=='AB')
        self.assertEqual(bytes.fromhex(abc['hex']),b'L\x02AB')
        self.assertEqual(abc['stdout'],'131\n')
        empty=next(c for c in cases if c['name']=='empty-payload')
        self.assertEqual((empty['exit'],empty['stdout']),(0,'0\n'))


if __name__ == '__main__':
    unittest.main(verbosity=2)