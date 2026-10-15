import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config_checks import check_codex_config, WWL_ROLES


class ConfigChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / ".codex/config.toml"
        self.config.parent.mkdir()
        self.config.write_text('[agents]\nmax_concurrent_threads_per_session = 32\ndefault_subagent_model = "gpt-5.6-terra"\ndefault_subagent_reasoning_effort = "medium"\n')
        (self.root / ".codex/agents").mkdir()
        for role in WWL_ROLES:
            (self.root / f".codex/agents/{role}.toml").write_text(f'name = "{role}"\ndescription = "role"\ndeveloper_instructions = "read only"\nsandbox_mode = "read-only"\n')

    def codes(self):
        return {d["code"] for d in check_codex_config(self.root)}

    def test_required_roles_and_additional_user_role_coexist(self):
        extra = self.root / ".codex/agents/user.toml"
        extra.write_text('name = "user"\nmodel = "another-model"\n')
        self.assertEqual(self.codes(), set())

    def test_smaller_supported_capacity_and_legacy_alias(self):
        self.config.write_text(self.config.read_text().replace("max_concurrent_threads_per_session = 32", "max_threads = 8"))
        self.assertEqual(self.codes(), set())

    def test_conflicting_capacity_and_boolean(self):
        initial = self.config.read_text()
        self.config.write_text(initial + 'max_threads = 8\n')
        self.assertIn("agent_capacity_conflict", self.codes())
        self.config.write_text(initial.replace("= 32", "= true"))
        self.assertIn("agent_capacity", self.codes())

    def test_role_cannot_silently_fix_routing_or_expand_permissions(self):
        role = self.root / ".codex/agents/wwl_author.toml"
        original = role.read_text()
        role.write_text(original + 'model = "gpt-6-astra"\n')
        self.assertIn("role_fixed_routing", self.codes())
        role.write_text(original.replace('"read-only"', '"workspace-write"'))
        self.assertIn("role_permissions", self.codes())

    def test_missing_invalid_and_duplicate_keys(self):
        role = self.root / ".codex/agents/wwl_reviewer.toml"
        role.unlink()
        self.assertIn("config_missing", self.codes())
        role.write_text('name = "x"\nname = "y"\n')
        self.assertIn("config_parse", self.codes())

    def test_configuration_does_not_require_root_execution_sheet(self):
        self.assertFalse((self.root / "CHANGE.md").exists())
        self.assertEqual(self.codes(), set())
        (self.root / "CHANGE.md").write_text("historical task text")
        self.assertEqual(self.codes(), set())

    def test_external_configuration_symlink_is_not_read(self):
        role = self.root / ".codex/agents/wwl_expert.toml"
        role.unlink()
        role.symlink_to(self.root / "nonexistent-private-config.toml")
        self.assertIn("config_symlink", self.codes())


if __name__ == "__main__":
    unittest.main()
