"""Two-valued edge model. No HDL scheduling, analog reset or metastability."""
from dataclasses import dataclass
import argparse
import csv
from pathlib import Path


def bit(name, value):
    if type(value) is not bool:
        raise ValueError(f"{name} must be bool")
    return value


@dataclass(frozen=True)
class Edge:
    full_before: bool
    ready: bool
    valid: bool
    data: int
    push: bool
    pop: bool
    full_after: bool
    data_after: int


class Buffer:
    def __init__(self, width=8):
        if type(width) is not int or width < 1:
            raise ValueError("width must be positive integer")
        self.width = width
        self.full = False
        self.data = 0

    def reset(self):
        """Logical immediate flush; physical pulse timing is outside this model."""
        self.full, self.data = False, 0

    def step(self, s_valid, s_data, m_ready, rst_n=True):
        bit('s_valid', s_valid); bit('m_ready', m_ready); bit('rst_n', rst_n)
        if type(s_data) is not int or not 0 <= s_data < (1 << self.width):
            raise ValueError("s_data must fit the unsigned word, even when invalid")
        if not rst_n:
            self.reset()
        old_full, old_data = self.full, self.data
        ready = rst_n and (not old_full or m_ready)
        valid = rst_n and old_full
        push, pop = s_valid and ready, valid and m_ready
        if rst_n and ready:
            self.full = s_valid
            if push:
                self.data = s_data
        return Edge(old_full, ready, valid, old_data, push, pop, self.full, self.data)


def write_trace(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    b = Buffer()
    drives = [(False, 0, True, False), (True, 0xA1, True, True),
              (True, 0xB2, False, True), (True, 0xB2, False, True),
              (True, 0xB2, True, True), (False, 0, True, True),
              (False, 0, True, True)]
    with (output/'trace.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['edge', 'rst_n', 's_valid', 's_data', 'm_ready',
                    *Edge.__dataclass_fields__])
        for k, (sv, sd, mr, rn) in enumerate(drives):
            e = b.step(sv, sd, mr, rn)
            w.writerow([k, int(rn), int(sv), sd, int(mr),
                        *[int(getattr(e, n)) for n in Edge.__dataclass_fields__]])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    write_trace(p.parse_args().output)
