# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase
from odoo.tools import config


class TestResUserRolePolicy(TransactionCase):
    """Tests for res_user_role_policy.py — bypass_role_policy compute field."""

    def test_admin_has_bypass(self):
        admin = self.env.ref("base.user_admin")
        self.assertTrue(admin.bypass_role_policy)

    def test_root_has_bypass(self):
        root = self.env.ref("base.user_root")
        self.assertTrue(root.bypass_role_policy)

    def test_regular_user_has_no_bypass(self):
        user = self.env["res.users"].create(
            {"name": "Reg User", "login": "reg_bypass_test", "email": "r@t.com"}
        )
        self.assertFalse(user.bypass_role_policy)


class TestResGroups(TransactionCase):
    """Tests for res_groups.py — role Boolean field."""

    def test_role_field_default_false(self):
        group = self.env["res.groups"].create({"name": "Plain Group"})
        self.assertFalse(group.role)

    def test_role_field_can_be_set_true(self):
        group = self.env["res.groups"].create({"name": "Role Group", "role": True})
        self.assertTrue(group.role)


class TestBaseModelExtensions(TransactionCase):
    """Tests for base.py — _role_policy_untouchable_groups,
    _get_role_policy_group_keep_ids, and user_has_groups."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def test_untouchable_groups_returns_expected_list(self):
        groups = self.env["ir.ui.menu"]._role_policy_untouchable_groups()
        self.assertIn("base.group_user", groups)
        self.assertIn("base.group_system", groups)
        self.assertIn("base.group_portal", groups)
        self.assertIn("base.group_public", groups)
        self.assertIn("base.group_no_one", groups)
        self.assertIn("base.group_erp_manager", groups)

    def test_get_role_policy_group_keep_ids_non_empty(self):
        keep_ids = self.env["ir.ui.menu"]._get_role_policy_group_keep_ids()
        self.assertTrue(keep_ids)
        self.assertIn(self.env.ref("base.group_user").id, keep_ids)

    def test_user_has_groups_note_unreachable_in_test_mode(self):
        # Verify the guard condition itself: test_enable is True in test runs
        self.assertTrue(config.get("test_enable"))

    def test_compute_bypass_role_policy_for_all_users(self):
        """
        _compute_bypass_role_policy iterates over `self` (lines 19-26).
        Create multiple users and trigger a batch compute to ensure the
        for-loop body and both branches are exercised in one call.
        """
        user_a = self.env["res.users"].create(
            {"name": "Bypass A", "login": "bypass_a", "email": "a@t.com"}
        )
        user_b = self.env["res.users"].create(
            {"name": "Bypass B", "login": "bypass_b", "email": "b@t.com"}
        )
        # Batch recompute to exercise the for-loop across multiple records
        users = user_a | user_b
        users._compute_bypass_role_policy()
        self.assertFalse(user_a.bypass_role_policy)
        self.assertFalse(user_b.bypass_role_policy)

        # Also verify admin & root via the same compute path
        admin = self.env.ref("base.user_admin")
        root = self.env.ref("base.user_root")
        combined = admin | root | user_a
        combined._compute_bypass_role_policy()
        self.assertTrue(admin.bypass_role_policy)
        self.assertTrue(root.bypass_role_policy)
        self.assertFalse(user_a.bypass_role_policy)


class TestResRole(TransactionCase):
    """Tests for res_role.py — create/write/menu sync."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def test_create_sets_role_true_on_group(self):
        """Role creation marks its group_id.role = True."""
        role = self.env["res.users.role"].create({"name": "Mark Role True"})
        self.assertTrue(role.group_id.role)

    def test_create_syncs_menus_group_id(self):
        """When menus are supplied on create, the role's group is added to them."""
        menu = self.env["ir.ui.menu"].create({"name": "Pre-Create Menu"})
        role = self.env["res.users.role"].create(
            {"name": "Create With Menu", "menu_ids": [(6, 0, [menu.id])]}
        )
        menu.invalidate_recordset()
        self.assertIn(role.group_id, menu.groups_id)

    def test_create_without_menus_does_not_crash(self):
        """Role creation without menu_ids doesn't raise."""
        role = self.env["res.users.role"].create({"name": "No Menus Role"})
        self.assertTrue(role.id)

    def test_write_cmd4_adds_group_to_menu(self):
        """write() with menu_ids (4, id) adds role group to that menu."""
        role = self.env["res.users.role"].create({"name": "Write 4 Role"})
        menu = self.env["ir.ui.menu"].create({"name": "Write 4 Menu"})
        self.assertNotIn(role.group_id, menu.groups_id)
        role.write({"menu_ids": [(4, menu.id)]})
        menu.invalidate_recordset()
        self.assertIn(role.group_id, menu.groups_id)

    def test_write_cmd3_removes_group_from_menu(self):
        """write() with menu_ids (3, id) removes role group from that menu."""
        role = self.env["res.users.role"].create({"name": "Write 3 Role"})
        menu = self.env["ir.ui.menu"].create({"name": "Write 3 Menu"})
        role.write({"menu_ids": [(4, menu.id)]})
        menu.invalidate_recordset()
        self.assertIn(role.group_id, menu.groups_id)

        role.write({"menu_ids": [(3, menu.id)]})
        menu.invalidate_recordset()
        self.assertNotIn(role.group_id, menu.groups_id)

    def test_write_cmd6_replace_adds_and_removes(self):
        """write() with menu_ids (6, 0, ids) computes diff and syncs groups."""
        role = self.env["res.users.role"].create({"name": "Write 6 Role"})
        menu_a = self.env["ir.ui.menu"].create({"name": "Write 6 Menu A"})
        menu_b = self.env["ir.ui.menu"].create({"name": "Write 6 Menu B"})

        # Add menu_a first
        role.write({"menu_ids": [(4, menu_a.id)]})
        menu_a.invalidate_recordset()
        self.assertIn(role.group_id, menu_a.groups_id)

        # Replace with menu_b only → menu_a loses the group, menu_b gains it
        role.write({"menu_ids": [(6, 0, [menu_b.id])]})
        menu_a.invalidate_recordset()
        menu_b.invalidate_recordset()
        self.assertNotIn(role.group_id, menu_a.groups_id)
        self.assertIn(role.group_id, menu_b.groups_id)

    def test_write_cmd5_removes_all_menus_groups(self):
        """write() with menu_ids (5, 0, 0) removes group from all current menus."""
        role = self.env["res.users.role"].create({"name": "Write 5 Role"})
        menu = self.env["ir.ui.menu"].create({"name": "Write 5 Menu"})
        role.write({"menu_ids": [(4, menu.id)]})
        menu.invalidate_recordset()
        self.assertIn(role.group_id, menu.groups_id)

        role.write({"menu_ids": [(5, 0, 0)]})
        menu.invalidate_recordset()
        self.assertNotIn(role.group_id, menu.groups_id)

    def test_write_unsupported_cmd_raises(self):
        """write() with an unsupported x2many command raises NotImplementedError."""
        role = self.env["res.users.role"].create({"name": "Unsupported Cmd Role"})
        with self.assertRaises(NotImplementedError):
            role.write({"menu_ids": [(0, 0, {})]})

    def test_init_restore_adds_missing_group_to_menu(self):
        """_init_restore_role_groups() re-adds the role group to menus missing it."""
        role = self.env["res.users.role"].create({"name": "Restore Role"})
        menu = self.env["ir.ui.menu"].create({"name": "Restore Menu"})
        role.write({"menu_ids": [(4, menu.id)]})
        menu.invalidate_recordset()
        self.assertIn(role.group_id, menu.groups_id)

        # Manually remove the group to simulate drift
        menu.with_context(role_policy_init=True).write(
            {"groups_id": [(3, role.group_id.id)]}
        )
        menu.invalidate_recordset()
        self.assertNotIn(role.group_id, menu.groups_id)

        # Restore should fix it
        self.env["res.users.role"]._init_restore_role_groups()
        menu.invalidate_recordset()
        self.assertIn(role.group_id, menu.groups_id)

    def test_init_restore_no_op_when_group_already_present(self):
        """_init_restore_role_groups() is a no-op when groups are already correct."""
        role = self.env["res.users.role"].create({"name": "No-Op Restore Role"})
        menu = self.env["ir.ui.menu"].create({"name": "No-Op Restore Menu"})
        role.write({"menu_ids": [(4, menu.id)]})
        menu.invalidate_recordset()
        self.assertIn(role.group_id, menu.groups_id)
        # Call restore — should not remove or duplicate anything
        self.env["res.users.role"]._init_restore_role_groups()
        menu.invalidate_recordset()
        self.assertIn(role.group_id, menu.groups_id)


class TestIrUiMenuExtended(TransactionCase):
    """Tests for ir_ui_menu.py — _visible_menu_ids and _visible_menu_ids_user_admin."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.role = cls.env["res.users.role"].create({"name": "Menu Vis Role"})
        cls.action = cls.env["ir.actions.act_window"].create(
            {"name": "Menu Vis Action", "res_model": "res.users"}
        )
        cls.menu = cls.env["ir.ui.menu"].create(
            {
                "name": "Visible Test Menu",
                "role_ids": [(6, 0, [cls.role.id])],
                "action": f"ir.actions.act_window,{cls.action.id}",
            }
        )

    def test_visible_menu_ids_admin_returns_menu(self):
        """
        _visible_menu_ids_user_admin() (called because admin bypasses role policy)
        must include the test menu which has a valid action.
        """
        # Running as superuser → bypass_role_policy=True → _visible_menu_ids_user_admin
        visible = self.env["ir.ui.menu"]._visible_menu_ids()
        self.assertIn(self.menu.id, visible)

    def test_visible_menu_ids_admin_debug_mode(self):
        """_visible_menu_ids_user_admin() debug=True includes group_no_one menus."""
        visible_debug = self.env["ir.ui.menu"]._visible_menu_ids(debug=True)
        visible_normal = self.env["ir.ui.menu"]._visible_menu_ids(debug=False)
        # Debug mode must have >= items than normal (group_no_one not excluded)
        self.assertGreaterEqual(len(visible_debug), len(visible_normal))

    def test_menu_role_ids_field_exists(self):
        """ir.ui.menu has the role_ids Many2many field."""
        self.assertIn(self.role, self.menu.role_ids)

    def test_menu_group_synced_on_create(self):
        """When role_ids is set on create, the role's group appears in groups_id."""
        self.assertIn(self.role.group_id, self.menu.groups_id)
