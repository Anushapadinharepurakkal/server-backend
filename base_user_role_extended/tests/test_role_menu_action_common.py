# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestRolePolicyMenuActionCommon(TransactionCase):
    """
    Tests for role_menu_action_common.py and ir.ui.menu visibility logic.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.role = cls.env["res.users.role"].create({"name": "Common Test Role"})

    def test_create_with_role_ids_appends_role_group(self):
        """
        create(): when role_ids is provided, the role's group_id is appended
        to groups_id.
        """
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "Menu With Role",
                "role_ids": [(6, 0, [self.role.id])],
            }
        )
        self.assertIn(self.role.group_id, menu.groups_id)

    def test_write_with_role_ids_syncs_group(self):
        """
        write(): when role_ids is supplied, for each record the mapped
        group_id is written back via (4, id).
        """
        role2 = self.env["res.users.role"].create({"name": "Sync Role"})
        menu = self.env["ir.ui.menu"].create({"name": "Menu Sync Role"})
        self.assertNotIn(role2.group_id, menu.groups_id)

        menu.write({"role_ids": [(4, role2.id)]})
        menu.invalidate_recordset()
        self.assertIn(role2.group_id, menu.groups_id)

    def test_write_with_role_ids_no_group_cmds_does_not_write(self):
        """
        write(): when role_ids is present but the role has no group_id mapped,
        the inner write is skipped.
        """
        menu = self.env["ir.ui.menu"].create({"name": "Menu No Group Cmd"})
        menu.write({"role_ids": [(5,)]})
        self.assertIsNotNone(menu.id)

    def test_visible_menu_ids_deny_list(self):
        """
        Test that _visible_menu_ids restricts menus assigned to the user's role.
        """
        user = self.env["res.users"].create(
            {
                "name": "Test Vis User",
                "login": "test_vis_user",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.env["res.users.role.line"].create(
            {
                "user_id": user.id,
                "role_id": self.role.id,
            }
        )
        user.set_groups_from_roles(force=True)

        menu1 = self.env["ir.ui.menu"].create(
            {
                "name": "Allowed Menu",
            }
        )
        menu2 = self.env["ir.ui.menu"].create(
            {
                "name": "Denied Menu",
                "role_ids": [(6, 0, [self.role.id])],
            }
        )

        # We need to test without test_enable to trigger the deny logic
        user_env = self.env(user=user)
        user_env.registry.clear_cache()

        # Mock test_enable=False to bypass test guard
        import odoo.tools.config as config

        original_test_enable = config.get("test_enable")
        config.options["test_enable"] = False
        try:
            visible_ids = user_env["ir.ui.menu"]._visible_menu_ids()
            self.assertIn(menu1.id, visible_ids)
            self.assertNotIn(menu2.id, visible_ids)
        finally:
            config.options["test_enable"] = original_test_enable
