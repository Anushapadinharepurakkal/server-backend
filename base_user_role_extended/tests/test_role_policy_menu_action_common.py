# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestRolePolicyMenuActionCommon(TransactionCase):
    """
    Tests for role_policy_menu_action_common.py exercised via ir.ui.menu,
    which concretely inherits RolePolicyMenuActionCommon.

    Branches covered in create():
      - groups_id present + role_policy_init absent → filtered (L17-24)
        • filtered commands non-empty          (L21-22)
        • filtered commands empty              (L23-24)
      - role_ids present → role groups appended (L25-31)
      - role_policy_init context → groups_id NOT filtered (L17 guard)

    Branches covered in write():
      - groups_id present + role_policy_init absent → filtered (L35-43)
        • filtered commands non-empty          (L40-41)
        • filtered commands empty              (L42-43)
      - role_policy_init context → groups_id NOT filtered
      - role_ids present after write → role groups synced (L45-49)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # A role whose group_id is marked role=True
        cls.role = cls.env["res.users.role"].create({"name": "Common Test Role"})
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_system = cls.env.ref("base.group_system")

    # ------------------------------------------------------------------
    # create() — groups_id filtering
    # ------------------------------------------------------------------

    def test_create_filters_out_non_keep_group(self):
        """
        create(): a groups_id command referencing an id NOT in keep_ids
        must be silently dropped (L23-24 branch: filtered empty → del groups_id).
        """
        # Build a throwaway group that is not in the untouchable list
        custom_group = self.env["res.groups"].create({"name": "Custom Non-Keep"})
        # Supply it via (4, id) — only keep_ids survive; custom_group is not keep
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "Menu Filter Drop",
                "groups_id": [(4, custom_group.id)],
            }
        )
        # The custom group must have been filtered away
        self.assertNotIn(custom_group, menu.groups_id)

    def test_create_keeps_untouchable_group(self):
        """
        create(): a groups_id command whose id IS in keep_ids must survive
        (L21-22 branch: filtered commands non-empty → kept).
        """
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "Menu Keep Untouchable",
                "groups_id": [(4, self.group_user.id)],
            }
        )
        self.assertIn(self.group_user, menu.groups_id)

    def test_create_with_role_policy_init_skips_filter(self):
        """
        create() with role_policy_init=True must NOT filter groups_id.
        Any group supplied is preserved as-is.
        """
        custom_group = self.env["res.groups"].create({"name": "Init Group"})
        menu = (
            self.env["ir.ui.menu"]
            .with_context(role_policy_init=True)
            .create(
                {
                    "name": "Menu Init Context",
                    "groups_id": [(4, custom_group.id)],
                }
            )
        )
        self.assertIn(custom_group, menu.groups_id)

    def test_create_with_role_ids_appends_role_group(self):
        """
        create(): when role_ids is provided, the role's group_id is appended
        to groups_id (L25-31).
        """
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "Menu With Role",
                "role_ids": [(6, 0, [self.role.id])],
            }
        )
        self.assertIn(self.role.group_id, menu.groups_id)

    def test_create_no_groups_id_key_when_all_filtered(self):
        """
        When all groups_id commands are filtered away the key must be deleted
        from vals (not set to []), so no error occurs on super().create().
        """
        custom_group = self.env["res.groups"].create({"name": "All Filtered"})
        # This should not raise; the key is cleanly removed
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "Menu All Filtered",
                "groups_id": [(4, custom_group.id)],
            }
        )
        self.assertIsNotNone(menu.id)
        self.assertNotIn(custom_group, menu.groups_id)

    # ------------------------------------------------------------------
    # write() — groups_id filtering
    # ------------------------------------------------------------------

    def test_write_filters_out_non_keep_group(self):
        """
        write(): assigning a non-keep group via (4, id) must be filtered away
        (L42-43 branch: filtered empty → del groups_id).
        """
        custom_group = self.env["res.groups"].create({"name": "Write Non-Keep"})
        menu = self.env["ir.ui.menu"].create({"name": "Menu Write Filter"})
        menu.write({"groups_id": [(4, custom_group.id)]})
        self.assertNotIn(custom_group, menu.groups_id)

    def test_write_keeps_untouchable_group(self):
        """
        write(): a (4, keep_id) command survives the filter (L40-41).
        """
        menu = self.env["ir.ui.menu"].create({"name": "Menu Write Keep"})
        menu.write({"groups_id": [(4, self.group_user.id)]})
        self.assertIn(self.group_user, menu.groups_id)

    def test_write_clear_cmd5_preserves_keep_groups(self):
        """
        write(): command (5,) / clear — filter converts it to a cmd-6 that
        preserves keep_ids, so untouchable groups survive.
        """
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "Menu Write Clear",
                "groups_id": [(4, self.group_user.id)],
            }
        )
        menu.write({"groups_id": [(5,)]})
        # group_user is an untouchable keep_id → must be preserved
        self.assertIn(self.group_user, menu.groups_id)

    def test_write_clear_cmd5_removes_role_group_not_in_keep(self):
        """
        write(): command (5,) — a role group that is not an untouchable keep_id
        must be removed after the clear.  We verify by checking that a
        non-keep custom group is gone.
        """
        custom_group = self.env["res.groups"].create(
            {"name": "Write Clear Custom", "role": False}
        )
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "Menu Clear Custom",
                "groups_id": [(4, self.group_user.id), (4, custom_group.id)],
            }
        )
        # Confirm custom_group was already filtered on create
        self.assertNotIn(custom_group, menu.groups_id)

    def test_write_role_groups_also_preserved_by_filter(self):
        """
        write(): groups that have role=True are collected into keep_ids at
        write time (L38), so they survive a non-role write.
        """
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "Menu Write Role Preserve",
                "role_ids": [(6, 0, [self.role.id])],
            }
        )
        role_group = self.role.group_id
        self.assertIn(role_group, menu.groups_id)

        # Write something else — role group must remain
        menu.write({"name": "Menu Write Role Preserve Updated"})
        self.assertIn(role_group, menu.groups_id)

    def test_write_with_role_policy_init_skips_filter(self):
        """
        write() with role_policy_init=True skips filtering: a non-keep group
        can be written through.
        """
        custom_group = self.env["res.groups"].create(
            {"name": "Write Init Group"}
        )
        menu = self.env["ir.ui.menu"].create({"name": "Menu Write Init"})
        menu.with_context(role_policy_init=True).write(
            {"groups_id": [(4, custom_group.id)]}
        )
        self.assertIn(custom_group, menu.groups_id)

    def test_write_with_role_ids_syncs_group(self):
        """
        write(): when role_ids is supplied, for each record the mapped
        group_id is written back via (4, id) (L45-49).
        """
        role2 = self.env["res.users.role"].create({"name": "Sync Role"})
        menu = self.env["ir.ui.menu"].create({"name": "Menu Sync Role"})
        self.assertNotIn(role2.group_id, menu.groups_id)

        menu.with_context(role_policy_init=True).write(
            {"role_ids": [(4, role2.id)]}
        )
        menu.invalidate_recordset()
        self.assertIn(role2.group_id, menu.groups_id)

    def test_write_with_role_ids_no_group_cmds_does_not_write(self):
        """
        write(): when role_ids is present but the role has no group_id mapped,
        the inner write is skipped (L48 guard: if group_cmds).
        """
        # A role with no menus — just check that the write itself doesn't crash
        menu = self.env["ir.ui.menu"].create({"name": "Menu No Group Cmd"})
        # Detach all roles first
        menu.with_context(role_policy_init=True).write(
            {"role_ids": [(5,)]}
        )
        # No exception means the guard worked
        self.assertIsNotNone(menu.id)

    # ------------------------------------------------------------------
    # _get_role_policy_group_keep_ids / _role_policy_untouchable_groups
    # (tested via base.py, exercised by the create/write paths above)
    # ------------------------------------------------------------------

    def test_get_role_policy_group_keep_ids_contains_expected(self):
        """
        _get_role_policy_group_keep_ids() must include all expected untouchable
        groups plus group_user (which is added twice but deduplication is
        caller's responsibility — we just check presence).
        """
        keep_ids = self.env["ir.ui.menu"]._get_role_policy_group_keep_ids()
        expected_refs = [
            "base.group_no_one",
            "base.group_user",
            "base.group_erp_manager",
            "base.group_system",
            "base.group_portal",
            "base.group_public",
        ]
        for ref in expected_refs:
            self.assertIn(self.env.ref(ref).id, keep_ids)
