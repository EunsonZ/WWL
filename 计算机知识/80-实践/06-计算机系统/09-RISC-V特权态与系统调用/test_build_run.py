from __future__ import annotations

import unittest

import build_run


GOOD_TRACE = "\n".join(
    (
        "MODE M: boot hart=0, delegate causes 2 and 8",
        "MODE S: stvec/sscratch installed, preparing sret",
        "MODE U: entered by sret",
        "TRAP kind=ecall scause=8 sepc=0x80001000 stval=0x0 origin.SPP=0 saved.SPIE=1",
        "SYSCALL number=1 arg0=41 return=42",
        "TRAP kind=ecall scause=8 sepc=0x80001004 stval=0x0",
        "CHECK registers=PASS",
        "TRAP kind=ecall scause=8 sepc=0x80001008 stval=0x0",
        "SYSCALL number=99 arg0=7 return=-38 status=unknown",
        "TRAP kind=ecall scause=8 sepc=0x8000100c stval=0x0",
        "CHECK unknown-return=PASS",
        "TRAP kind=illegal scause=2 sepc=0x80001010 stval=0x10002573 origin.SPP=0 saved.SPIE=1",
        "ILLEGAL instruction=csrr-a0-sstatus action=skip return=-2",
        "TRAP kind=ecall scause=8 sepc=0x80001014 stval=0x0",
        "CHECK illegal-recovery=PASS",
        "TRAP kind=ecall scause=8 sepc=0x80001018 stval=0x0",
        "RESULT PASS",
    )
) + "\n"


class TraceContractTests(unittest.TestCase):
    def test_accepts_full_ordered_trace_and_zero_exit(self) -> None:
        build_run.verify_output(0, GOOD_TRACE)

    def test_rejects_nonzero_emulator_exit(self) -> None:
        with self.assertRaisesRegex(build_run.LabError, "exited with 7"):
            build_run.verify_output(7, GOOD_TRACE)

    def test_rejects_guest_failure_even_if_pass_text_is_present(self) -> None:
        with self.assertRaisesRegex(build_run.LabError, "guest reported failure"):
            build_run.verify_output(0, GOOD_TRACE + "RESULT FAIL: late failure\n")

    def test_each_semantic_checkpoint_is_required(self) -> None:
        checkpoints = {
            "normal return": "SYSCALL number=1 arg0=41 return=42",
            "register restoration": "CHECK registers=PASS",
            "unknown syscall": "SYSCALL number=99 arg0=7 return=-38 status=unknown",
            "illegal CSR cause": "TRAP kind=illegal scause=2",
            "illegal CSR recovery": "CHECK illegal-recovery=PASS",
        }
        for label, checkpoint in checkpoints.items():
            with self.subTest(label=label):
                damaged = GOOD_TRACE.replace(checkpoint, "REMOVED", 1)
                with self.assertRaises(build_run.LabError):
                    build_run.verify_output(0, damaged)

    def test_rejects_out_of_order_trace(self) -> None:
        first = "CHECK registers=PASS"
        second = "SYSCALL number=99 arg0=7 return=-38 status=unknown"
        damaged = GOOD_TRACE.replace(first, "TEMP", 1).replace(second, first, 1)
        damaged = damaged.replace("TEMP", second, 1)
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(0, damaged)


if __name__ == "__main__":
    unittest.main()
