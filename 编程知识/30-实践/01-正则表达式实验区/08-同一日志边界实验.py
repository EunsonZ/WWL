"""Strict LF-framed UTF-8 teaching log, versions mapped to one domain record.
Standard library only. Import defines functions; default execution prints JSON.
"""
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import json
from pathlib import Path
import platform
import re

MAX_FRAME = 256  # bytes, including exactly one final LF
PATTERN = re.compile(
    r'(?P<version>v[0-9]{1,2})\|'
    r'(?P<timestamp>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)\|'
    r'level=(?P<level>INFO|WARN|ERROR)\|code=(?P<code>[A-Z][0-9]{3})\|'
    r'latency=(?P<amount>0|[1-9][0-9]{0,7})(?P<fraction>\.[0-9]{1,3})?'
    r'(?P<unit>us|ms)\|message=(?P<message>[^\x00-\x1f\x7f|=]{1,64})'
)
TEXT_V1 = 'v1|2026-10-07T08:09:10Z|level=INFO|code=I200|latency=1250us|message=中文'
TEXT_V2 = 'v2|2026-10-07T08:09:10Z|level=INFO|code=I200|latency=1.250ms|message=中文'


class LogError(ValueError):
    def __init__(self, stage, detail):
        self.stage = stage
        super().__init__(stage+': '+detail)


@dataclass(frozen=True)
class Record:
    timestamp: datetime
    level: str
    code: str
    latency_us: Decimal
    message: str


@dataclass(frozen=True)
class Parsed:
    raw: bytes
    text: str
    fields: dict
    spans: dict
    record: Record


def parse_frame(raw: bytes) -> Parsed:
    # Type hints alone do not reject a str argument.
    if not isinstance(raw, bytes):
        raise LogError('type', 'bytes required')
    if not 1 <= len(raw) <= MAX_FRAME:
        raise LogError('limit', 'frame must contain 1..256 bytes')
    if not raw.endswith(b'\n') or raw.count(b'\n') != 1 or b'\r' in raw:
        raise LogError('framing', 'one final LF; no CR or interior LF')
    try:
        text = raw[:-1].decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        raise LogError('encoding', f'invalid UTF-8 bytes [{exc.start},{exc.end})') from exc
    match = PATTERN.fullmatch(text)
    if match is None:
        raise LogError('shape', 'fixed order, no missing/duplicate/extra fields')
    fields = match.groupdict()
    version = fields['version']
    if version not in ('v1', 'v2'):
        raise LogError('version', 'unsupported version')
    # Shape alone allows two digits such as 24 or 60. Enforce our stricter
    # clock contract before a date API can normalize end-of-day notation.
    timestamp_text = fields['timestamp']
    hour, minute, second = (int(timestamp_text[a:b]) for a, b in ((11, 13), (14, 16), (17, 19)))
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        raise LogError('date', 'clock must be hour 0..23, minute/second 0..59')
    try:
        timestamp = datetime.fromisoformat(timestamp_text[:-1]+'+00:00')
    except ValueError as exc:
        raise LogError('date', 'invalid calendar or clock') from exc
    if fields['code'][0] != fields['level'][0]:
        raise LogError('code', 'code prefix must agree with level')
    if fields['unit'] != {'v1': 'us', 'v2': 'ms'}[version]:
        raise LogError('unit', 'version/unit mismatch')
    if version == 'v1' and fields['fraction'] is not None:
        raise LogError('unit', 'v1 requires whole microseconds')
    # Local context avoids a caller's low Decimal precision silently rounding.
    with localcontext() as context:
        context.prec = 32
        amount = Decimal(fields['amount']+(fields['fraction'] or ''))
        microseconds = amount*(1000 if version == 'v2' else 1)
        if not Decimal(0) <= microseconds <= Decimal(60000000):
            raise LogError('range', 'duration must be 0..60 seconds')
        microseconds = microseconds.quantize(Decimal(1))
    spans = {}
    for name in ('timestamp', 'level', 'code', 'amount', 'unit', 'message'):
        start, end = match.span(name)
        spans[name] = {'codepoints': (start, end),
                       'bytes': (len(text[:start].encode('utf-8')), len(text[:end].encode('utf-8')))}
    return Parsed(raw, text, fields, spans,
                  Record(timestamp, fields['level'], fields['code'], microseconds, fields['message']))


class LFFramer:
    """Buffer bytes until LF; a chunk is not a line or a Unicode character."""
    def __init__(self):
        self.buffer = bytearray()
        self.failed = False

    def feed(self, chunk):
        if self.failed:
            raise LogError('framing', 'failed framer must be replaced')
        if not isinstance(chunk, bytes):
            self.failed = True
            raise LogError('type', 'byte chunks required')
        if len(chunk) > 4096:
            self.failed = True
            raise LogError('limit', 'teaching chunk limit is 4096 bytes')
        result = []
        try:
            for value in chunk:
                self.buffer.append(value)
                if len(self.buffer) > MAX_FRAME:
                    raise LogError('limit', 'unframed line exceeds 256 bytes')
                if value == 10:
                    result.append(parse_frame(bytes(self.buffer)))
                    self.buffer.clear()
        except LogError:
            self.failed = True
            raise
        return result

    def finish(self):
        if self.failed or self.buffer:
            self.failed = True
            raise LogError('framing', 'failed or unterminated stream')


def report():
    one = parse_frame((TEXT_V1+'\n').encode('utf-8'))
    two = parse_frame((TEXT_V2+'\n').encode('utf-8'))
    expected = Record(datetime(2026, 10, 7, 8, 9, 10, tzinfo=timezone.utc),
                      'INFO', 'I200', Decimal(1250), '中文')
    assert one.record == two.record == expected
    assert len(one.text) == 70 and len(one.raw) == 75
    assert one.spans['message'] == {'codepoints': (68, 70), 'bytes': (68, 74)}
    assert one.raw[68:74] == bytes.fromhex('e4 b8 ad e6 96 87')
    # Every single split, including splits inside Chinese UTF-8 sequences.
    split_checks = 0
    for split in range(len(one.raw)+1):
        framer = LFFramer()
        parsed = framer.feed(one.raw[:split])+framer.feed(one.raw[split:])
        framer.finish()
        assert [item.record for item in parsed] == [expected]
        split_checks += 1
    framer = LFFramer()
    assert [p.record for p in framer.feed(one.raw+two.raw)] == [expected, expected]
    framer.finish()
    cases = {
        'unknown_version': (TEXT_V1.replace('v1|', 'v3|')+'\n').encode(),
        'duplicate_field': (TEXT_V1.replace('|code=', '|level=INFO|code=')+'\n').encode(),
        'invalid_utf8': one.raw.replace(bytes.fromhex('e4 b8 ad'), b'\xff'),
        'truncated_utf8': one.raw[:69]+b'\n',
        'prefix': b'xx'+one.raw,
        'suffix_field': one.raw[:-1]+b'|extra=1\n',
        'invalid_date': (TEXT_V1.replace('10-07', '02-30')+'\n').encode(),
        'invalid_clock': (TEXT_V1.replace('T08:', 'T25:')+'\n').encode(),
        'hour24_zero': (TEXT_V1.replace('2026-10-07T08:09:10Z', '2026-01-01T24:00:00Z')+'\n').encode(),
        'hour24_nonzero': (TEXT_V1.replace('2026-10-07T08:09:10Z', '2026-01-01T24:00:01Z')+'\n').encode(),
        'minute60': (TEXT_V1.replace('T08:09:10Z', 'T08:60:10Z')+'\n').encode(),
        'second60': (TEXT_V1.replace('T08:09:10Z', 'T08:09:60Z')+'\n').encode(),
        'too_precise': (TEXT_V2.replace('1.250ms', '1.2501ms')+'\n').encode(),
        'wrong_unit': (TEXT_V1.replace('1250us', '1250ms')+'\n').encode(),
        'v1_fraction': (TEXT_V1.replace('1250us', '1.250us')+'\n').encode(),
        'range': (TEXT_V1.replace('1250us', '60000001us')+'\n').encode(),
        'too_large': b'x'*257,
        'missing_lf': one.raw[:-1],
        'crlf': one.raw[:-1]+b'\r\n',
        'fullwidth_code': (TEXT_V1.replace('I200', 'I２００')+'\n').encode(),
        'level_code_mismatch': (TEXT_V1.replace('I200', 'E200')+'\n').encode(),
        'nul_message': one.raw[:-1]+b'\0\n',
        'bom': bytes.fromhex('efbbbf')+one.raw,
    }
    rejected = {}
    for name, raw in cases.items():
        try:
            parse_frame(raw)
        except LogError as exc:
            rejected[name] = exc.stage
        else:
            raise AssertionError('accepted '+name)
    # Independently declared negative expectations, not inferred from parser output.
    for name in ('invalid_clock', 'hour24_zero', 'hour24_nonzero', 'minute60', 'second60'):
        assert rejected[name] == 'date'
    last_second = parse_frame((TEXT_V1.replace('T08:09:10Z', 'T23:59:59Z')+'\n').encode())
    assert last_second.record.timestamp == datetime(2026, 10, 7, 23, 59, 59, tzinfo=timezone.utc)
    try:
        parse_frame(TEXT_V1)
    except LogError as exc:
        assert exc.stage == 'type'
    else:
        raise AssertionError('type hints alone accepted str')
    # No default normalization: canonically equivalent messages remain distinct.
    nfc = parse_frame((TEXT_V1.replace('中文', 'é')+'\n').encode())
    nfd = parse_frame((TEXT_V1.replace('中文', 'e\u0301')+'\n').encode())
    assert nfc.raw != nfd.raw and nfc.record.message != nfd.record.message
    assert parse_frame((TEXT_V2.replace('1.250ms', '0.125ms')+'\n').encode()).record.latency_us == Decimal(125)
    for amount in ('0us', '60000000us'):
        parse_frame((TEXT_V1.replace('1250us', amount)+'\n').encode())
    stream_cases = {}
    for name, chunk, finish in (('unterminated', one.raw[:-1], True),
                                ('oversized_line', b'x'*257, False),
                                ('oversized_chunk', b'x'*4097, False)):
        framer = LFFramer()
        try:
            framer.feed(chunk)
            if finish:
                framer.finish()
        except LogError as exc:
            stream_cases[name] = exc.stage
        else:
            raise AssertionError('accepted stream '+name)
        try:
            framer.feed(one.raw)
        except LogError:
            pass
        else:
            raise AssertionError('reused failed framer')
    # Low caller precision does not change duration conversion.
    with localcontext() as context:
        context.prec = 2
        assert parse_frame((TEXT_V2+'\n').encode()).record == expected
    pattern = r'\b([A-Za-z]+)[ \t]+\1\b'
    regex_results = []
    for text in ('K K', 'İ İ', 'ſ ſ', 'The the', '中文The the中文'):
        unicode_match = re.search(pattern, text, re.I)
        ascii_match = re.search(pattern, text, re.I | re.ASCII)
        regex_results.append({'text': text, 'I': bool(unicode_match), 'I_ASCII': bool(ascii_match)})
    assert [r['I_ASCII'] for r in regex_results] == [False, False, False, True, True]
    assert [r['I'] for r in regex_results] == [True, True, True, True, False]
    return {'python': platform.python_version(), 'raw_hex': one.raw.hex(' '),
            'codepoints_without_lf': len(one.text), 'bytes_with_lf': len(one.raw),
            'message_spans': one.spans['message'], 'fields': one.fields,
            'canonical': {'timestamp': expected.timestamp.isoformat(), 'level': expected.level,
                          'code': expected.code, 'latency_us': str(expected.latency_us), 'message': expected.message},
            'v1_v2_equal': one.record == two.record, 'split_checks': split_checks,
            'rejected': rejected, 'stream_rejections': stream_cases, 'normalization_preserved': True, 'regex_flags': regex_results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='explicit JSON output outside the vault')
    args = parser.parse_args()
    encoded = json.dumps(report(), ensure_ascii=False, indent=2)+'\n'
    if args.output is None:
        print(encoded, end='')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding='utf-8')


if __name__ == '__main__':
    main()
