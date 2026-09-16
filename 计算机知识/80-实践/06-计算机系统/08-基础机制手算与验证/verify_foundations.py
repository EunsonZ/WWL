"""Pure toy models used by the WWL computer-systems foundation lessons.

These functions intentionally model only the assumptions stated in their
docstrings.  They do not probe or simulate the current machine.
"""

from __future__ import annotations

from collections import deque
from typing import Iterable, Mapping


def detect_101(bits: str) -> list[dict[str, int | str]]:
    """Trace an overlapping Moore detector for the bit pattern ``101``.

    State names are the longest input suffix that is also a prefix of 101.
    The output is 1 in state ``101``, so a hit appears after consuming the
    third bit.  The next transition preserves an overlapping suffix.
    """

    if any(bit not in "01" for bit in bits):
        raise ValueError("bits must contain only '0' and '1'")

    transitions = {
        ("", "0"): "",
        ("", "1"): "1",
        ("1", "0"): "10",
        ("1", "1"): "1",
        ("10", "0"): "",
        ("10", "1"): "101",
        ("101", "0"): "10",
        ("101", "1"): "1",
    }
    state = ""
    trace: list[dict[str, int | str]] = []
    for cycle, bit in enumerate(bits, start=1):
        previous = state
        state = transitions[(state, bit)]
        trace.append(
            {
                "cycle": cycle,
                "bit": bit,
                "previous": previous or "empty",
                "state": state or "empty",
                "output": int(state == "101"),
            }
        )
    return trace


def ripple_add(a: int, b: int, width: int, *, subtract: bool = False) -> dict[str, object]:
    """Perform one unsigned bit-level add/subtract in exactly ``width`` bits.

    Subtraction uses ``a + (~b) + 1``.  ``carry_out`` is the final adder
    carry; for subtraction it must not be renamed "borrow" without applying
    the chosen ISA's convention.  Signed overflow is derived from the operand
    and result sign bits in the fixed-width two's-complement interpretation.
    """

    if width <= 0:
        raise ValueError("width must be positive")
    limit = 1 << width
    if not (0 <= a < limit and 0 <= b < limit):
        raise ValueError("operands must fit the declared unsigned width")

    effective_b = b ^ (limit - 1) if subtract else b
    carry = int(subtract)
    carry_chain = [carry]
    result = 0
    for index in range(width):
        a_bit = (a >> index) & 1
        b_bit = (effective_b >> index) & 1
        sum_bit = a_bit ^ b_bit ^ carry
        carry = (a_bit & b_bit) | (a_bit & carry) | (b_bit & carry)
        result |= sum_bit << index
        carry_chain.append(carry)

    sign = 1 << (width - 1)
    a_negative = bool(a & sign)
    b_negative = bool(b & sign)
    result_negative = bool(result & sign)
    if subtract:
        overflow = (a_negative != b_negative) and (result_negative != a_negative)
    else:
        overflow = (a_negative == b_negative) and (result_negative != a_negative)

    return {
        "result": result,
        "carry_out": carry,
        "signed_overflow": overflow,
        "carry_chain": carry_chain,
    }


def trace_lru_cache(
    addresses: Iterable[int], *, sets: int = 4, ways: int = 2, line_size: int = 16
) -> list[dict[str, object]]:
    """Trace a set-associative cache with true LRU within each set.

    Each deque is ordered least-recently-used to most-recently-used.  The
    function models neither dirty data nor timing; all accesses are reads.
    """

    if sets <= 0 or ways <= 0:
        raise ValueError("sets and ways must be positive")
    if line_size <= 0 or line_size & (line_size - 1):
        raise ValueError("line_size must be a positive power of two")

    contents = [deque() for _ in range(sets)]
    trace: list[dict[str, object]] = []
    for address in addresses:
        if address < 0:
            raise ValueError("addresses must be non-negative")
        block = address // line_size
        set_index = block % sets
        tag = block // sets
        offset = address % line_size
        current = contents[set_index]
        hit = tag in current
        evicted = None
        if hit:
            current.remove(tag)
        elif len(current) == ways:
            evicted = current.popleft()
        current.append(tag)
        trace.append(
            {
                "address": address,
                "tag": tag,
                "set": set_index,
                "offset": offset,
                "hit": hit,
                "evicted": evicted,
                "lru_to_mru": list(current),
            }
        )
    return trace


def decode_toy_dram(address: int) -> dict[str, int]:
    """Decode the lesson's 16-bit row/bank/column/offset toy mapping."""

    if not 0 <= address <= 0xFFFF:
        raise ValueError("address must fit in the lesson's 16-bit model")
    return {
        "row": address >> 8,
        "bank": (address >> 6) & 0x3,
        "column": (address >> 3) & 0x7,
        "offset": address & 0x7,
    }


def translate_two_stage(
    gva: int,
    guest_map: Mapping[int, int],
    stage2_map: Mapping[int, int],
    *,
    address_bits: int = 8,
    page_bits: int = 4,
) -> dict[str, int]:
    """Translate a toy GVA through guest and stage-2 page-number mappings."""

    if not 0 < page_bits < address_bits:
        raise ValueError("page_bits must lie between zero and address_bits")
    if not 0 <= gva < (1 << address_bits):
        raise ValueError("gva must fit address_bits")

    offset_mask = (1 << page_bits) - 1
    offset = gva & offset_mask
    guest_vpn = gva >> page_bits
    try:
        guest_pn = guest_map[guest_vpn]
    except KeyError as error:
        raise KeyError(f"unmapped guest VPN {guest_vpn:#x}") from error

    page_number_bits = address_bits - page_bits
    page_number_limit = 1 << page_number_bits
    if not 0 <= guest_pn < page_number_limit:
        raise ValueError("guest physical page number does not fit toy address")

    try:
        host_pn = stage2_map[guest_pn]
    except KeyError as error:
        raise KeyError(f"unmapped stage-2 GPN {guest_pn:#x}") from error

    if not 0 <= host_pn < page_number_limit:
        raise ValueError("host physical page number does not fit toy address")

    return {
        "gva": gva,
        "guest_vpn": guest_vpn,
        "offset": offset,
        "gpa": (guest_pn << page_bits) | offset,
        "hpa": (host_pn << page_bits) | offset,
    }


def _demo() -> None:
    """Print the fixed examples used by the accompanying lessons."""

    print("101 detector:", [row["output"] for row in detect_101("10101")])
    print("4-bit 7 + 1:", ripple_add(0b0111, 0b0001, 4))
    print("cache hits:", [row["hit"] for row in trace_lru_cache([0x00, 0x10, 0x40, 0x00, 0x80, 0x40])])
    print("DRAM 0x1234:", decode_toy_dram(0x1234))
    print("two-stage 0xAC:", translate_two_stage(0xAC, {0xA: 0x5}, {0x5: 0x9}))


if __name__ == "__main__":
    _demo()
