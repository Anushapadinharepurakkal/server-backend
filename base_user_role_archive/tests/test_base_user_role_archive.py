# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestBaseUserRoleArchive(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.user_root = cls.env.ref("base.user_root")

        # Test User
        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Test Archive User",
                "login": "test_archive_user",
            }
        )

        cls.model_res_partner = cls.env.ref("base.model_res_partner")

        # Create a group that grants archive and unarchive access
        cls.group_archive_manager = cls.env["res.groups"].create(
            {"name": "Archive Manager"}
        )
        cls.env["ir.model.access"].create(
            {
                "name": "partner archive manager",
                "model_id": cls.model_res_partner.id,
                "group_id": cls.group_archive_manager.id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
                "perm_archive": True,
                "perm_unarchive": True,
            }
        )

        # Create a group that grants read and write, but NO archive access
        cls.group_no_archive = cls.env["res.groups"].create(
            {"name": "No Archive Partner"}
        )
        cls.env["ir.model.access"].create(
            {
                "name": "partner no archive",
                "model_id": cls.model_res_partner.id,
                "group_id": cls.group_no_archive.id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
                "perm_archive": False,
                "perm_unarchive": False,
            }
        )

        # Create a partner to test archiving
        cls.test_partner = cls.env["res.partner"].create(
            {"name": "Test Archive Partner"}
        )

    def test_archive_access_with_role(self):
        """Test archive access is granted when user's role has the required group."""
        # 1. Create role with archive access
        role = self.env["res.users.role"].create(
            {
                "name": "Archive Role",
                "implied_ids": [(4, self.group_archive_manager.id)],
            }
        )
        self.env["res.users.role.line"].create(
            {
                "user_id": self.test_user.id,
                "role_id": role.id,
            }
        )

        # Clear ORM caches explicitly
        self.env.registry.clear_cache()

        # 2. Check get_archive_access (frontend API)
        archive_access = (
            self.env["ir.model.access"]
            .with_user(self.test_user)
            .get_archive_access("res.partner")
        )
        self.assertTrue(archive_access["can_archive"])
        self.assertTrue(archive_access["can_unarchive"])

        # 3. Test archiving action on the model (should succeed)
        test_partner = self.test_partner.with_user(self.test_user)
        test_partner.sudo().write({"active": False})
        self.assertFalse(test_partner.active)

        # Test unarchiving
        test_partner.write({"active": True})
        self.assertTrue(test_partner.active)

    def test_archive_access_revoked(self):
        """Test archive access is denied when group is removed from role."""
        # Clean roles
        self.test_user.role_line_ids.unlink()

        # 1. Create a role with NO archive access and assign it
        role = self.env["res.users.role"].create(
            {
                "name": "No Archive Role",
                "implied_ids": [(4, self.group_no_archive.id)],
            }
        )
        self.env["res.users.role.line"].create(
            {
                "user_id": self.test_user.id,
                "role_id": role.id,
            }
        )

        self.env.registry.clear_cache()

        # 2. Check get_archive_access (frontend API)
        archive_access = (
            self.env["ir.model.access"]
            .with_user(self.test_user)
            .get_archive_access("res.partner")
        )
        self.assertFalse(archive_access["can_archive"])
        self.assertFalse(archive_access["can_unarchive"])

        # 3. Test archiving action on the model (should raise AccessError)
        test_partner = self.test_partner.with_user(self.test_user)

        with self.assertRaises(AccessError):
            test_partner.write({"active": False})

    def test_archive_bypass_and_fallback(self):
        """Test archive access for admin and users without roles (fallback)."""
        # Test admin bypass
        self.env.registry.clear_cache()
        archive_access_admin = (
            self.env["ir.model.access"]
            .with_user(self.user_admin)
            .get_archive_access("res.partner")
        )
        self.assertTrue(archive_access_admin["can_archive"])

        # Test user with NO roles
        self.test_user.role_line_ids.unlink()
        # Explicitly assign group directly to the user (no role involved)
        self.test_user.write({"groups_id": [(4, self.group_archive_manager.id)]})
        self.env.registry.clear_cache()

        archive_access_fallback = (
            self.env["ir.model.access"]
            .with_user(self.test_user)
            .get_archive_access("res.partner")
        )
        self.assertTrue(archive_access_fallback["can_archive"])

        test_partner = self.test_partner.with_user(self.test_user)
        test_partner.write({"active": False})
        self.assertFalse(test_partner.active)
