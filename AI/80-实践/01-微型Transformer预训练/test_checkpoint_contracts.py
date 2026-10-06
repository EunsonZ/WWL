"""AST-isolated checkpoint contracts; these tests do not import real PyTorch."""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path
import types
import unittest
from unittest.mock import Mock


SOURCE = Path(__file__).resolve().parent / "tiny_transformer.py"


def isolated_checkpoint_functions() -> dict[str, object]:
    """Compile only pure metric/loading functions with a mocked torch object."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    selected_names = {"load_checkpoint", "metrics_from_nll"}
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in selected_names
    ]
    if {node.name for node in selected} != selected_names:
        raise AssertionError("expected checkpoint contract functions are missing")
    namespace = {
        "math": math,
        "Any": object,
        "Path": Path,
        "torch": types.SimpleNamespace(load=Mock()),
    }
    isolated_module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            *selected,
        ],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(isolated_module), str(SOURCE), "exec"), namespace)
    return namespace


class CheckpointContracts(unittest.TestCase):
    def test_restricted_checkpoint_load_fails_closed(self) -> None:
        namespace = isolated_checkpoint_functions()
        load_checkpoint = namespace["load_checkpoint"]
        loader = namespace["torch"].load
        loader.return_value = {"step": 1}
        self.assertEqual(load_checkpoint(Path("synthetic.pt")), {"step": 1})
        loader.assert_called_once_with(
            Path("synthetic.pt"), map_location="cpu", weights_only=True
        )

        for reason in ("unsupported parameter", "other type error"):
            loader.reset_mock()
            loader.side_effect = TypeError(reason)
            with self.assertRaises(RuntimeError):
                load_checkpoint(Path("synthetic.pt"))
            loader.assert_called_once_with(
                Path("synthetic.pt"), map_location="cpu", weights_only=True
            )

    def test_ppl_has_no_silent_cap_and_is_strict_json(self) -> None:
        metrics_from_nll = isolated_checkpoint_functions()["metrics_from_nll"]
        for nll in (0.0, 1.0, 25.0, 1000.0):
            metrics = metrics_from_nll(nll, 2)
            json.dumps(metrics, allow_nan=False)
            self.assertEqual(metrics["log_ppl"], nll)
            if nll < 1000.0:
                self.assertAlmostEqual(metrics["ppl"], math.exp(nll))
                self.assertEqual(metrics["ppl_status"], "finite")
            else:
                self.assertIsNone(metrics["ppl"])
                self.assertEqual(metrics["ppl_status"], "overflow")
        with self.assertRaises(ValueError):
            metrics_from_nll(1.0, 0)


if __name__ == "__main__":
    unittest.main()
