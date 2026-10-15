import unittest

from tensor_lowering import (
    Graph,
    GuardFailure,
    Op,
    Tensor,
    TensorMeta,
    infer_metadata,
    lower_graph,
    run_lowered,
    run_reference,
)


def two_op_graph(
    shape: tuple[int | None, ...] = (2, 2),
    *,
    layout: str = "contiguous",
    output_alias_group: str | None = None,
    side_effect: bool = False,
) -> Graph:
    meta = TensorMeta(shape, layout)
    return Graph(
        {"x": meta, "y": meta},
        (
            Op("add", "sum", ("x", "y"), side_effect, output_alias_group),
            Op("relu", "out", ("sum",)),
        ),
        ("out",),
    )


class MetadataTests(unittest.TestCase):
    def test_shape_propagation_preserves_dynamic_dimension(self) -> None:
        metadata = infer_metadata(two_op_graph((None, 4)))
        self.assertEqual(metadata["sum"].shape, (None, 4))
        self.assertEqual(metadata["out"].shape, (None, 4))

    def test_incompatible_static_shapes_are_rejected(self) -> None:
        graph = Graph(
            {"x": TensorMeta((2, 4)), "y": TensorMeta((3, 4))},
            (Op("add", "out", ("x", "y")),),
            ("out",),
        )
        with self.assertRaisesRegex(ValueError, r"shape mismatch: \(2, 4\) vs \(3, 4\)"):
            infer_metadata(graph)


class FusionTests(unittest.TestCase):
    def test_static_fusion_matches_reference_values(self) -> None:
        graph = two_op_graph()
        lowered = lower_graph(graph)
        feeds = {
            "x": Tensor((2, 2), (-4.0, 2.0, 3.0, -1.0)),
            "y": Tensor((2, 2), (1.0, 1.0, -5.0, 4.0)),
        }
        self.assertEqual([op.kind for op in lowered.ops], ["fused_add_relu"])
        self.assertEqual(run_lowered(lowered, feeds), run_reference(graph, feeds))
        self.assertEqual(run_lowered(lowered, feeds)[0].data, (0.0, 3.0, 0.0, 3.0))

    def test_dynamic_specialization_emits_and_checks_guards(self) -> None:
        graph = two_op_graph((None, 4))
        lowered = lower_graph(graph, {"x": (2, 4), "y": (2, 4)})
        self.assertEqual(
            [(guard.value, guard.expected) for guard in lowered.guards],
            [("x", (2, 4)), ("y", (2, 4))],
        )
        bad_feeds = {
            "x": Tensor((3, 4), (1.0,) * 12),
            "y": Tensor((3, 4), (1.0,) * 12),
        }
        with self.assertRaisesRegex(
            GuardFailure,
            r"shape guard failed for x: expected \(2, 4\), got \(3, 4\)",
        ):
            run_lowered(lowered, bad_feeds)

    def test_dynamic_shape_without_specialization_stays_unfused(self) -> None:
        lowered = lower_graph(two_op_graph((None, 4)))
        self.assertEqual([op.kind for op in lowered.ops], ["add", "relu"])
        self.assertEqual(lowered.decisions[0].reason, "dynamic-shape-needs-guard")

    def test_layout_alias_and_side_effect_each_block_fusion(self) -> None:
        cases = (
            (two_op_graph(layout="strided"), "layout-not-contiguous"),
            (two_op_graph(output_alias_group="buffer-x"), "alias-not-proven-independent"),
            (two_op_graph(side_effect=True), "side-effect-barrier"),
        )
        for graph, reason in cases:
            with self.subTest(reason=reason):
                lowered = lower_graph(graph)
                self.assertEqual([op.kind for op in lowered.ops], ["add", "relu"])
                self.assertEqual(lowered.decisions[0].reason, reason)


if __name__ == "__main__":
    unittest.main()
