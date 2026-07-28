# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestBaseUserRoleExtended(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.user_root = cls.env.ref("base.user_root")
        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Test Role User",
                "login": "test_role_user",
            }
        )
        cls.model_res_partner = cls.env.ref("base.model_res_partner")
        cls.model_res_users = cls.env.ref("base.model_res_users")

        cls.group_partner_manager = cls.env["res.groups"].create(
            {"name": "Partner Manager"}
        )
        cls.env["ir.model.access"].create(
            {
                "name": "partner manager access",
                "model_id": cls.model_res_partner.id,
                "group_id": cls.group_partner_manager.id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
            }
        )

        cls.group_mixed = cls.env["res.groups"].create({"name": "Mixed Access"})
        cls.env["ir.model.access"].create(
            {
                "name": "mixed users access",
                "model_id": cls.model_res_users.id,
                "group_id": cls.group_mixed.id,
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        cls.env["ir.model.access"].create(
            {
                "name": "mixed partner access",
                "model_id": cls.model_res_partner.id,
                "group_id": cls.group_mixed.id,
                "perm_read": False,
                "perm_write": False,
                "perm_create": True,
                "perm_unlink": False,
            }
        )

    def test_compute_bypass_role_policy(self):
        """Test that user_admin and user_root bypass the role policy,
        but normal users don't."""
        self.assertTrue(self.user_admin.bypass_role_policy)
        self.assertTrue(self.user_root.bypass_role_policy)
        self.assertFalse(self.test_user.bypass_role_policy)

    def test_role_creation_and_access_sync(self):
        """Test creating a role and ensuring its model
        access rights are synced correctly."""
        # Create a role that implies our two groups
        role = self.env["res.users.role"].create(
            {
                "name": "Test Manager Role",
                "implied_ids": [
                    (4, self.group_partner_manager.id),
                    (4, self.group_mixed.id),
                ],
            }
        )
        # Check that the role's underlying group now has the merged access rights
        access_partner = self.env["ir.model.access"].search(
            [
                ("group_id", "=", role.group_id.id),
                ("model_id", "=", self.model_res_partner.id),
            ]
        )
        self.assertTrue(access_partner)
        # Should merge perm_read and perm_write from group_partner_manager,
        # and perm_create from group_mixed
        self.assertTrue(access_partner.perm_read)
        self.assertTrue(access_partner.perm_write)
        self.assertTrue(access_partner.perm_create)
        self.assertFalse(access_partner.perm_unlink)

        access_users = self.env["ir.model.access"].search(
            [
                ("group_id", "=", role.group_id.id),
                ("model_id", "=", self.model_res_users.id),
            ]
        )
        self.assertTrue(access_users)
        self.assertTrue(access_users.perm_read)
        self.assertFalse(access_users.perm_write)

        role.write({"name": "Renamed Role"})
        self.assertEqual(len(access_partner), 1)

        role.write({"implied_ids": [(3, self.group_mixed.id)]})
        # Users model access should be removed because it was only in group_mixed
        access_users = self.env["ir.model.access"].search(
            [
                ("group_id", "=", role.group_id.id),
                ("model_id", "=", self.model_res_users.id),
            ]
        )
        self.assertFalse(access_users)

    def test_ir_model_access_get_allowed_models(self):
        """Test the _get_allowed_models override using the test user and roles."""
        self.test_user.role_line_ids.unlink()

        # Test cache and standard behavior
        self.env.registry.clear_cache()
        allowed_models_no_role = (
            self.env["ir.model.access"]
            .with_user(self.test_user)
            ._get_allowed_models("read")
        )
        self.assertIn("res.partner", allowed_models_no_role)

        # Give the test user our role containing only group_mixed
        role = self.env["res.users.role"].create(
            {
                "name": "Read Users Role",
                "implied_ids": [(4, self.group_mixed.id)],
            }
        )
        self.env["res.users.role.line"].create(
            {
                "user_id": self.test_user.id,
                "role_id": role.id,
            }
        )

        self.env.registry.clear_cache()

        allowed_models_with_role = (
            self.env["ir.model.access"]
            .with_user(self.test_user)
            ._get_allowed_models("read")
        )

        # The user should have access to 'res.users' for read
        self.assertIn("res.users", allowed_models_with_role)
        # But 'res.partner' should NOT be in the allowed models for read!
        self.assertNotIn("res.partner", allowed_models_with_role)

        # Test bypass user (admin)
        self.env.registry.clear_cache()
        allowed_models_admin = (
            self.env["ir.model.access"]
            .with_user(self.user_admin)
            ._get_allowed_models("read")
        )
        self.assertIn("res.partner", allowed_models_admin)

        # Give admin the same role, but they should bypass it
        self.env["res.users.role.line"].create(
            {
                "user_id": self.user_admin.id,
                "role_id": role.id,
            }
        )
        self.env.registry.clear_cache()
        allowed_models_admin_bypassed = (
            self.env["ir.model.access"]
            .with_user(self.user_admin)
            ._get_allowed_models("read")
        )
        self.assertIn("res.partner", allowed_models_admin_bypassed)

    def test_user_role_add_remove_access(self):
        """Test adding a role with access and then,
        removing it to ensure access is lost."""

        self.test_user.role_line_ids.unlink()

        role = self.env["res.users.role"].create(
            {
                "name": "Dynamic Access Role",
                "implied_ids": [(4, self.group_partner_manager.id)],
            }
        )

        # Assign role to user
        self.env["res.users.role.line"].create(
            {
                "user_id": self.test_user.id,
                "role_id": role.id,
            }
        )

        self.env.registry.clear_cache()

        # Verify user initially has Read & Write access
        allowed_read = (
            self.env["ir.model.access"]
            .with_user(self.test_user)
            ._get_allowed_models("read")
        )
        allowed_write = (
            self.env["ir.model.access"]
            .with_user(self.test_user)
            ._get_allowed_models("write")
        )
        self.assertIn(
            "res.partner", allowed_read, "User should have read access initially."
        )
        self.assertIn(
            "res.partner", allowed_write, "User should have write access initially."
        )

        role.write({"implied_ids": [(3, self.group_partner_manager.id)]})

        self.env.registry.clear_cache()

        # Verify user lost access
        allowed_read_after = (
            self.env["ir.model.access"]
            .with_user(self.test_user)
            ._get_allowed_models("read")
        )
        allowed_write_after = (
            self.env["ir.model.access"]
            .with_user(self.test_user)
            ._get_allowed_models("write")
        )
        self.assertNotIn(
            "res.partner", allowed_read_after, "User should have lost read access."
        )
        self.assertNotIn(
            "res.partner", allowed_write_after, "User should have lost write access."
        )
