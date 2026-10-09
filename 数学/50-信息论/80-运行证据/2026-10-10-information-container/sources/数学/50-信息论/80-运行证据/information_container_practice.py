"""Finite IC v1 teaching container; no files, services or hardware touched."""
import json

ALPHABET = "ABCD"
MESSAGE = "AAAABBCD"
PREFIX = dict(zip(ALPHABET, ("0", "10", "110", "111")))
FIXED = dict(zip(ALPHABET, ("00", "01", "10", "11")))
EXPECTED_P = bytes.fromhex(
    "49 43 01 04 08 0e 41 01 00 42 02 02 43 03 06 "
    "44 03 07 0a dc af"
)
EXPECTED_Q = bytes.fromhex(
    "49 43 01 04 08 10 41 02 00 42 02 01 43 02 02 "
    "44 02 03 00 5b 1c"
)


def validate_code(code):
    if set(code) != set(ALPHABET):
        raise ValueError("alphabet")
    words = [code[s] for s in ALPHABET]
    if any(not isinstance(w, str) or not 1 <= len(w) <= 8
           or set(w) - {"0", "1"} for w in words):
        raise ValueError("codeword")
    for i, a in enumerate(words):
        for b in words[i + 1:]:
            if a.startswith(b) or b.startswith(a):
                raise ValueError("prefix conflict")


def seal(body):
    return bytes(body) + bytes([sum(body) % 256])


def encode(message, code):
    validate_code(code)
    if not isinstance(message, str) or not 1 <= len(message) <= 255:
        raise ValueError("message length")
    if set(message) - set(ALPHABET):
        raise ValueError("message alphabet")
    bits = "".join(code[s] for s in message)
    if not 1 <= len(bits) <= 255:
        raise ValueError("payload length")
    header = b"IC" + bytes([1, 4, len(message), len(bits)])
    table = b"".join(
        bytes([ord(s), len(code[s]), int(code[s], 2)])
        for s in ALPHABET
    )
    padded = bits + "0" * ((-len(bits)) % 8)
    payload = int(padded, 2).to_bytes(len(padded) // 8, "big")
    return seal(header + table + payload)


def decode(blob):
    if not isinstance(blob, bytes) or not 20 <= len(blob) <= 51:
        raise ValueError("container length")
    if blob[:4] != b"IC\x01\x04":
        raise ValueError("magic or version")
    count, bit_count = blob[4], blob[5]
    if not count or not bit_count:
        raise ValueError("zero length")
    if len(blob) != 18 + (bit_count + 7) // 8 + 1:
        raise ValueError("declared or trailing length")
    if sum(blob[:-1]) % 256 != blob[-1]:
        raise ValueError("checksum")
    code = {}
    for i, symbol in enumerate(ALPHABET):
        stored, length, value = blob[6 + 3 * i:9 + 3 * i]
        if stored != ord(symbol) or not 1 <= length <= 8:
            raise ValueError("table order or length")
        if value >= 1 << length:
            raise ValueError("code value")
        code[symbol] = format(value, f"0{length}b")
    validate_code(code)
    packed = "".join(format(b, "08b") for b in blob[18:-1])
    if "1" in packed[bit_count:]:
        raise ValueError("nonzero padding")
    inverse = {word: symbol for symbol, word in code.items()}
    symbols, pending = [], ""
    for bit in packed[:bit_count]:
        pending += bit
        if pending in inverse:
            symbols.append(inverse[pending])
            pending = ""
            if len(symbols) > count:
                raise ValueError("too many symbols")
        elif not any(word.startswith(pending) for word in inverse):
            raise ValueError("invalid payload")
    if pending:
        raise ValueError("truncated codeword")
    if len(symbols) != count:
        raise ValueError("symbol count")
    return "".join(symbols)


def require_rejected(blob):
    try:
        decode(blob)
    except ValueError as exc:
        return str(exc)
    raise AssertionError("malformed container accepted")


def run():
    p, q = encode(MESSAGE, PREFIX), encode(MESSAGE, FIXED)
    assert p == EXPECTED_P and q == EXPECTED_Q
    assert decode(p) == decode(q) == MESSAGE

    damaged = bytearray(p)
    damaged[18] ^= 0x80
    pad = bytearray(p[:-1])
    pad[19] |= 1
    prefix_conflict = bytearray(p[:-1])
    prefix_conflict[11] = 0
    wrong_count = bytearray(p[:-1])
    wrong_count[4] = 7
    truncated = bytearray(p[:18])
    truncated[4:6] = bytes([1, 2])
    truncated.append(0xc0)  # effective bits "11", six zero padding bits

    rejections = {
        "unresealed_payload_flip": require_rejected(bytes(damaged)),
        "resealed_nonzero_padding": require_rejected(seal(pad)),
        "resealed_prefix_conflict": require_rejected(seal(prefix_conflict)),
        "resealed_wrong_count": require_rejected(seal(wrong_count)),
        "resealed_truncated_codeword": require_rejected(seal(truncated)),
        "trailing_byte": require_rejected(p + b"\x00"),
    }
    collision = bytearray(q)
    collision[18:20] = bytes([1, 0x5a])
    assert sum(collision[:-1]) % 256 == collision[-1]
    changed_message = decode(bytes(collision))
    assert changed_message == "AAABBBCC" and changed_message != MESSAGE

    rows = {}
    for label, blob in (("P", p), ("Q", q)):
        bits = blob[5]
        file_bits = len(blob) * 8
        repeated_bits = file_bits * 2
        data_symbols = repeated_bits // 2
        total_symbols = data_symbols + 8 + 4
        rows[label] = {
            "decoded": decode(blob),
            "hex": blob.hex(" "),
            "effective_bits": bits,
            "padding_bits": (-bits) % 8,
            "model_bytes": 12,
            "header_bytes": 6,
            "checksum_bytes": 1,
            "payload_bytes": (bits + 7) // 8,
            "file_bytes": len(blob),
            "file_bits": file_bits,
            "repeated_channel_bits": repeated_bits,
            "data_symbols": data_symbols,
            "sync_symbols": 8,
            "pilot_symbols": 4,
            "total_symbols": total_symbols,
            "symbol_rate_per_second": 1000,
            "transmit_seconds": total_symbols / 1000,
            "without_repeat_total_symbols": file_bits // 2 + 12,
        }
    return {
        "format": "IC v1, explicit four-symbol code, sum8",
        "message": MESSAGE,
        "rows": rows,
        "rejected_inputs": rejections,
        "accepted_sum8_collision": changed_message,
        "scope": "finite format and symbol accounting; no channel measurement",
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
