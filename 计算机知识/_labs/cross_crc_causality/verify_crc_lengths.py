"""Author's coefficient-array cross-check for the fixed seven/eight-bit inputs.

Reuses only coefficient_remainder from verify_crc.py, never imports crc.py.
Finite execution is not the general order proof or a non-author review.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import zlib

from verify_crc import coefficient_remainder


HERE = Path(__file__).resolve().parent


def position_cycle(generator: str) -> dict:
    """Multiply a coefficient array by x, then reduce, until one returns."""
    degree = len(generator) - 1
    current = '0' * (degree - 1) + '1'
    powers = [current]
    # Positive-degree binary divisor with constant 1 gives a finite unit group.
    for step in range(1, 2 ** degree):
        current = format(coefficient_remainder(current + '0', generator), f'0{degree}b')
        powers.append(current)
        if current == powers[0]:
            return {'order': step, 'powers_through_first_return': powers}
    raise AssertionError('unit did not return within the finite-ring bound')


def classify(rows: list[dict], key: str, width: int, generator: str) -> dict:
    degree = len(generator) - 1
    singles = [format(coefficient_remainder('1' + '0' * k, generator), f'0{degree}b')
               for k in range(width)]
    groups = defaultdict(list)
    for position, syndrome in enumerate(singles):
        groups[syndrome].append(position)
    doubles = [row for row in rows if row['error'].count('1') == 2]
    missed = [row['error'] for row in doubles if row[key] == 0]
    cycle = position_cycle(generator)
    assert singles == [cycle['powers_through_first_return'][k % cycle['order']]
                       for k in range(width)]
    missed_pairs = []
    for i in range(width):
        for j in range(i + 1, width):
            error = ''.join('1' if power in (i, j) else '0'
                            for power in reversed(range(width)))
            row = next(row for row in doubles if row['error'] == error)
            # Finite check of the proof's prediction, not its derivation.
            assert (row[key] == 0) == ((j - i) % cycle['order'] == 0)
            if row[key] == 0:
                missed_pairs.append([i, j])
    assert len(doubles) == width * (width - 1) // 2
    return {'generator': generator, **cycle, 'single_syndromes_x0_up': singles,
            'single_syndrome_collisions': {s: ps for s, ps in groups.items() if len(ps) > 1},
            'double_count': len(doubles), 'detected_double_count': len(doubles) - len(missed),
            'undetected_double_errors': missed, 'undetected_position_pairs': missed_pairs}


def verify(result: dict, expected: dict) -> dict:
    config = expected['input']
    assert result['schema'] == 'wwl-crc219-v1'
    assert result['input'] == config, 'fixed cross-check requires its matching published input'
    message = config['message']
    g, alt = config['generator'], config['alternate_generator']
    degree = len(g) - 1
    width = config['codeword_width']
    assert width in (7, 8) and width == len(message) + degree
    assert g == '1011' and alt == '1001' and degree == 3
    assert message == ('1101' if width == 7 else '01101')
    assert result['message_width'] == len(message) and result['generator_degree'] == degree
    remainder = coefficient_remainder(message + '0' * degree, g)
    check_bits = format(remainder, f'0{degree}b')
    codeword = message + check_bits
    assert result['message_remainder'] == remainder == 1
    assert result['check_bits'] == expected['check_bits'] == check_bits
    assert result['codeword'] == expected['codeword'] == codeword
    assert result['codeword_remainder'] == coefficient_remainder(codeword, g) == 0
    rows = result['errors']
    assert len(rows) == expected['error_count'] == (2 ** width - 1)
    assert [row['error'] for row in rows] == [format(i, f'0{width}b') for i in range(1, 2 ** width)]
    for row in rows:
        bits = row['error']
        assert row['span'] == bits.rfind('1') - bits.find('1') + 1
        assert row['remainder'] == coefficient_remainder(bits, g)
        assert row['alternate_remainder'] == coefficient_remainder(bits, alt)
        received = ''.join(str((int(a) + int(b)) % 2) for a, b in zip(codeword, bits))
        assert row['received'] == received
        assert row['received_remainder'] == coefficient_remainder(received, g) == row['remainder']
    short = [row for row in rows if row['span'] <= degree]
    assert len(short) == expected['short_burst_count']
    assert all(row['remainder'] and row['alternate_remainder'] for row in short)
    assert sum(row['remainder'] == 0 for row in rows) == expected['nonzero_undetected_count']
    by_bits = {row['error']: row for row in rows}
    for selection in expected['selected_errors']:
        assert all(by_bits[selection['error']][key] == value for key, value in selection.items())
    assert result['crc32_vectors'] == expected['crc32_vectors']
    for vector in result['crc32_vectors']:
        value = zlib.crc32(bytes.fromhex(vector['payload_hex'])) & 0xFFFFFFFF
        assert vector['checksum_hex'] == f'{value:08X}'
        assert vector['little_endian_hex'] == value.to_bytes(4, 'little').hex()
    primary = classify(rows, 'remainder', width, g)
    alternate = classify(rows, 'alternate_remainder', width, alt)
    assert primary['powers_through_first_return'] == ['001', '010', '100', '011', '110', '111', '101', '001']
    assert alternate['powers_through_first_return'] == ['001', '010', '100', '001']
    assert primary['undetected_position_pairs'] == ([] if width == 7 else [[0, 7]])
    assert len(alternate['undetected_double_errors']) == (5 if width == 7 else 7)
    return {'status': 'PASS', 'frame_width': width, 'errors_checked': len(rows),
            'short_bursts_checked': len(short), 'primary': primary, 'alternate': alternate,
            'crc32_vectors_checked': len(result['crc32_vectors']),
            'boundary': 'fixed finite instances; author cross-check, not independent review or channel probability'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('seven', type=Path)
    parser.add_argument('eight', type=Path)
    parser.add_argument('--seven-expected', type=Path, default=HERE / 'crc_expected.json')
    parser.add_argument('--eight-expected', type=Path, default=HERE / 'crc8_expected.json')
    args = parser.parse_args()
    reports = [verify(json.loads(output.read_text(encoding='utf-8')),
                      json.loads(expected.read_text(encoding='utf-8')))
               for output, expected in [(args.seven, args.seven_expected),
                                        (args.eight, args.eight_expected)]]
    assert [report['frame_width'] for report in reports] == [7, 8]
    print(json.dumps({'status': 'PASS', 'frames': reports}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
