"""Finite GF(2) CRC and CRC-32/ISO-HDLC contrast; standard library only.

No writes or network. Bit integers are coefficient vectors, not arithmetic values.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def bits_value(bits: str, name: str) -> int:
    if not isinstance(bits, str) or not bits or any(c not in '01' for c in bits):
        raise ValueError(f'{name} must be a nonempty binary string')
    return int(bits, 2)


def remainder(value: int, generator: int) -> int:
    """Polynomial remainder: top set bit is the leading monomial."""
    if type(value) is not int or value < 0:
        raise ValueError('dividend must be a nonnegative coefficient integer')
    if type(generator) is not int or generator < 2:
        raise ValueError('generator must have positive degree')
    while value.bit_length() >= generator.bit_length():
        value ^= generator << (value.bit_length() - generator.bit_length())
    return value


def burst_span(error: int) -> int:
    if type(error) is not int or error < 0:
        raise ValueError('error must be a nonnegative coefficient integer')
    if error == 0:
        return 0
    return error.bit_length() - ((error & -error).bit_length() - 1)


def crc32_iso_hdlc(data: bytes) -> int:
    """Right-shifting reflected register already represents reflected output."""
    if not isinstance(data, bytes):
        raise ValueError('CRC-32 input must be bytes')
    register = 0xFFFFFFFF
    for byte in data:
        register ^= byte
        for _ in range(8):
            register = ((register >> 1) ^ 0xEDB88320
                        if register & 1 else register >> 1)
    return register ^ 0xFFFFFFFF


def run(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValueError('input must be an object')
    m = bits_value(config['message'], 'message')
    generators = [bits_value(config[key], key)
                  for key in ('generator', 'alternate_generator')]
    if any(g < 2 or not g & 1 for g in generators):
        raise ValueError('generators need positive degree and constant term one')
    if any(not config[key].startswith('1')
           for key in ('generator', 'alternate_generator')):
        raise ValueError('generator representation must start with one')
    g, alt = generators
    degree = g.bit_length() - 1
    width = config['codeword_width']
    if type(width) is not int or not 2 <= width <= 16:
        raise ValueError('bounded enumeration requires codeword width 2..16')
    if width != len(config['message']) + degree:
        raise ValueError('codeword width must equal message width plus generator degree')
    if alt.bit_length() != g.bit_length():
        raise ValueError('comparison generators must have equal degree')
    shifted = m << degree
    residue = remainder(shifted, g)
    codeword = shifted ^ residue
    rows = []
    for error in range(1, 1 << width):
        received = codeword ^ error
        rows.append({'error': format(error, f'0{width}b'),
                     'span': burst_span(error),
                     'received': format(received, f'0{width}b'),
                     'remainder': remainder(error, g),
                     'received_remainder': remainder(received, g),
                     'alternate_remainder': remainder(error, alt)})
    real = []
    for vector in config['crc32_vectors']:
        payload = bytes.fromhex(vector['payload_hex'])
        value = crc32_iso_hdlc(payload)
        real.append({'name': vector['name'], 'payload_hex': payload.hex(),
                     'checksum_hex': f'{value:08X}',
                     'little_endian_hex': value.to_bytes(4, 'little').hex()})
    return {'schema': 'wwl-crc219-v1', 'input': config,
            'message_width': len(config['message']), 'generator_degree': degree,
            'message_remainder': residue,
            'check_bits': format(residue, f'0{degree}b'),
            'codeword': format(codeword, f'0{width}b'),
            'codeword_remainder': remainder(codeword, g),
            'errors': rows, 'crc32_vectors': real}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path,
                        default=Path(__file__).with_name('crc_inputs.json'))
    args = parser.parse_args()
    print(json.dumps(run(json.loads(args.input.read_text(encoding='utf-8'))),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
