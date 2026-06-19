# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase

from odoo.addons.base_user_role_extended.models.helpers import (
    diff_to_odoo_x2many_commands,
    filter_odoo_x2many_commands,
    play_odoo_x2x_commands_on_ids,
)


class TestFilterOdooX2manyCommands(TransactionCase):
    """Unit tests for filter_odoo_x2many_commands()."""

    def test_empty_commands_returns_empty(self):
        """False / empty list → empty result."""
        self.assertEqual(filter_odoo_x2many_commands(False, [1, 2]), [])
        self.assertEqual(filter_odoo_x2many_commands([], [1, 2]), [])

    def test_non_list_non_tuple_returns_empty(self):
        """A scalar (not list/tuple) → empty result."""
        self.assertEqual(filter_odoo_x2many_commands(42, [1, 2]), [])
        self.assertEqual(filter_odoo_x2many_commands("bad", [1, 2]), [])

    def test_cmd1_kept_when_id_in_keep(self):
        """Command 1 (update) is kept when its id is in keep_ids."""
        result = filter_odoo_x2many_commands([(1, 5, {"name": "x"})], [5])
        self.assertEqual(result, [(1, 5, {"name": "x"})])

    def test_cmd1_discarded_when_id_not_in_keep(self):
        """Command 1 (update) is dropped when its id is NOT in keep_ids."""
        result = filter_odoo_x2many_commands([(1, 99, {"name": "x"})], [5])
        self.assertEqual(result, [])

    def test_cmd2_kept_when_id_in_keep(self):
        """Command 2 (delete) kept when id is in keep_ids."""
        result = filter_odoo_x2many_commands([(2, 5)], [5])
        self.assertEqual(result, [(2, 5)])

    def test_cmd2_discarded_when_id_not_in_keep(self):
        result = filter_odoo_x2many_commands([(2, 99)], [5])
        self.assertEqual(result, [])

    def test_cmd3_kept_when_id_in_keep(self):
        """Command 3 (unlink) kept when id is in keep_ids."""
        result = filter_odoo_x2many_commands([(3, 5)], [5])
        self.assertEqual(result, [(3, 5)])

    def test_cmd3_discarded_when_id_not_in_keep(self):
        result = filter_odoo_x2many_commands([(3, 99)], [5])
        self.assertEqual(result, [])

    def test_cmd4_kept_when_id_in_keep(self):
        """Command 4 (link) kept when id is in keep_ids."""
        result = filter_odoo_x2many_commands([(4, 5)], [5])
        self.assertEqual(result, [(4, 5)])

    def test_cmd4_discarded_when_id_not_in_keep(self):
        result = filter_odoo_x2many_commands([(4, 99)], [5])
        self.assertEqual(result, [])

    def test_cmd6_filters_ids(self):
        """Command 6 (replace) keeps only ids that are in keep_ids."""
        result = filter_odoo_x2many_commands([(6, 0, [1, 2, 99])], [1, 2])
        self.assertEqual(result, [(6, 0, [1, 2])])

    def test_cmd6_returns_nothing_when_no_overlap(self):
        """Command 6 with no overlap → nothing appended."""
        result = filter_odoo_x2many_commands([(6, 0, [99, 100])], [1, 2])
        self.assertEqual(result, [])

    def test_cmd5_with_keep_ids_converts_to_cmd6(self):
        """Command 5 (clear) converts to cmd-6 with keep_ids when keep_ids is non-empty."""
        result = filter_odoo_x2many_commands([(5,)], [1, 2])
        self.assertEqual(result, [(6, 0, [1, 2])])

    def test_cmd5_without_keep_ids_passes_through(self):
        """Command 5 with empty keep_ids passes through unchanged."""
        result = filter_odoo_x2many_commands([(5,)], [])
        self.assertEqual(result, [(5,)])

    def test_unknown_cmd_passes_through(self):
        """Any command code other than 1-6 is passed through unchanged."""
        result = filter_odoo_x2many_commands([(7, 1)], [])
        self.assertEqual(result, [(7, 1)])

    def test_mixed_commands(self):
        """Mixed batch: only keep-ids survive cmd1-4; cmd6 filtered; cmd5 → cmd6."""
        keep = [1, 2, 3]
        cmds = [
            (1, 1, {"x": 1}),   # keep
            (2, 99),             # discard
            (3, 2),             # keep
            (4, 3),             # keep
            (4, 50),            # discard
            (6, 0, [1, 99]),    # → (6,0,[1])
            (5,),               # → (6,0,[1,2,3])
        ]
        result = filter_odoo_x2many_commands(cmds, keep)
        self.assertIn((1, 1, {"x": 1}), result)
        self.assertNotIn((2, 99), result)
        self.assertIn((3, 2), result)
        self.assertIn((4, 3), result)
        self.assertNotIn((4, 50), result)
        self.assertIn((6, 0, [1]), result)
        self.assertIn((6, 0, list(keep)), result)


class TestDiffToOdooX2manyCommands(TransactionCase):
    """Unit tests for diff_to_odoo_x2many_commands()."""

    def test_add_and_remove(self):
        """IDs in target but not current → add (4); current not in target → remove (3)."""
        diff = diff_to_odoo_x2many_commands([1, 2, 3], [2, 3, 4])
        self.assertIn((4, 4), diff)
        self.assertIn((3, 1), diff)

    def test_no_change(self):
        """Same sets → empty diff."""
        diff = diff_to_odoo_x2many_commands([1, 2], [1, 2])
        self.assertEqual(diff, [])

    def test_accepts_sets(self):
        """Accepts sets directly without conversion."""
        diff = diff_to_odoo_x2many_commands({10}, {20})
        self.assertIn((4, 20), diff)
        self.assertIn((3, 10), diff)

    def test_empty_current(self):
        """All target ids are additions."""
        diff = diff_to_odoo_x2many_commands([], [5, 6])
        add_ids = [cmd[1] for cmd in diff if cmd[0] == 4]
        self.assertIn(5, add_ids)
        self.assertIn(6, add_ids)

    def test_empty_target(self):
        """All current ids are removals."""
        diff = diff_to_odoo_x2many_commands([5, 6], [])
        remove_ids = [cmd[1] for cmd in diff if cmd[0] == 3]
        self.assertIn(5, remove_ids)
        self.assertIn(6, remove_ids)


class TestPlayOdooX2xCommandsOnIds(TransactionCase):
    """Unit tests for play_odoo_x2x_commands_on_ids()."""

    def test_cmd3_removes_id(self):
        result = play_odoo_x2x_commands_on_ids([1, 2, 3], [(3, 1)])
        self.assertEqual(result, {2, 3})

    def test_cmd4_adds_id(self):
        result = play_odoo_x2x_commands_on_ids([1, 2], [(4, 3)])
        self.assertEqual(result, {1, 2, 3})

    def test_cmd5_clears_all(self):
        result = play_odoo_x2x_commands_on_ids([1, 2, 3], [(5,)])
        self.assertEqual(result, set())

    def test_cmd6_replaces_all(self):
        result = play_odoo_x2x_commands_on_ids([1, 2, 3], [(6, 0, [4, 5])])
        self.assertEqual(result, {4, 5})

    def test_raises_on_unsupported_command(self):
        """Commands 0, 1, 2 raise NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            play_odoo_x2x_commands_on_ids([1], [(0, 0, {})])
        with self.assertRaises(NotImplementedError):
            play_odoo_x2x_commands_on_ids([1], [(1, 1, {})])
        with self.assertRaises(NotImplementedError):
            play_odoo_x2x_commands_on_ids([1], [(2, 1)])

    def test_chained_commands(self):
        """Multiple commands applied sequentially."""
        cmds = [(4, 4), (3, 1), (4, 5)]
        result = play_odoo_x2x_commands_on_ids([1, 2, 3], cmds)
        self.assertEqual(result, {2, 3, 4, 5})
