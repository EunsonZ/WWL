"""Fixed independent oracle: coefficient arrays, plus zlib for real CRC32.

Does not import crc.py. Input/expected defaults are relative to this file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zlib


def coefficient_remainder(bits: str, divisor: str) -> int:
    if (not bits or not divisor or any(c not in '01' for c in bits + divisor)
            or not divisor.startswith('1') or len(divisor) < 2):
        raise ValueError('binary strings and positive-degree monic divisor required')
    coefficients = [int(bit) for bit in bits]
    polynomial = [int(bit) for bit in divisor]
    for position in range(len(coefficients) - len(polynomial) + 1):
        if coefficients[position]:
            for offset, coefficient in enumerate(polynomial):
                coefficients[position + offset] = (coefficients[position + offset] + coefficient) % 2
    residue = coefficients[-(len(polynomial) - 1):]
    return sum(coefficient * 2 ** power for power, coefficient in enumerate(reversed(residue)))


def verify(result: dict, expected: dict) -> dict:
    assert result['schema'] == 'wwl-crc219-v1'
    assert result['input'] == expected['input'], 'fixed oracle requires the published input'
    g = expected['input']['generator']
    alt = expected['input']['alternate_generator']
    width = expected['input']['codeword_width']
    assert result['message_width'] == 4 and result['generator_degree'] == 3
    assert result['check_bits'] == expected['check_bits']
    assert result['codeword'] == expected['codeword']
    assert result['message_remainder'] == coefficient_remainder('1101000', g) == 1
    assert result['codeword_remainder'] == coefficient_remainder(result['codeword'], g) == 0
    rows = result['errors']
    assert len(rows) == expected['error_count']
    assert {row['error'] for row in rows} == {format(i, f'0{width}b') for i in range(1, 1 << width)}
    for row in rows:
        bits = row['error']
        assert row['span'] == bits.rfind('1') - bits.find('1') + 1
        assert row['remainder'] == coefficient_remainder(bits, g)
        assert row['alternate_remainder'] == coefficient_remainder(bits, alt)
        received = ''.join(str((int(a) + int(b)) % 2)
                           for a, b in zip(result['codeword'], bits))
        assert row['received'] == received
        assert row['received_remainder'] == coefficient_remainder(received, g) == row['remainder']
    short = [row for row in rows if row['span'] <= 3]
    assert len(short) == expected['short_burst_count']
    assert all(row['remainder'] and row['alternate_remainder'] for row in short)
    assert sum(row['remainder'] == 0 for row in rows) == expected['nonzero_undetected_count']
    by_bits = {row['error']: row for row in rows}
    for row in expected['selected_errors']:
        actual = by_bits[row['error']]
        assert all(actual[key] == value for key, value in row.items())
    assert coefficient_remainder('1001', alt) == 0
    assert result['crc32_vectors'] == expected['crc32_vectors']
    for vector in result['crc32_vectors']:
        value = zlib.crc32(bytes.fromhex(vector['payload_hex'])) & 0xFFFFFFFF
        assert vector['checksum_hex'] == f'{value:08X}'
        assert vector['little_endian_hex'] == value.to_bytes(4, 'little').hex()
    return {'status': 'PASS', 'errors_checked': len(rows), 'short_bursts_checked': len(short),
            'undetected_nonzero': sum(row['remainder'] == 0 for row in rows),
            'crc32_vectors_checked': len(result['crc32_vectors']),
            'boundary': 'finite fixed model only; not a general-proof or authenticity result'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    parser.add_argument('--expected', type=Path,
                        default=Path(__file__).with_name('crc_expected.json'))
    args = parser.parse_args()
    report = verify(json.loads(args.result.read_text(encoding='utf-8')),
                    json.loads(args.expected.read_text(encoding='utf-8')))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
