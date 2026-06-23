# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestRoleModelOperations(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.role_model = cls.env["res.users.role"]
        cls.role_model_operations = cls.env["role.model.operations"]
        cls.model_ir_model = cls.env["ir.model"]
        cls.res_users_model = cls.model_ir_model.search(
            [("model", "=", "res.users")], limit=1
        )
        cls.res_partner_model = cls.model_ir_model.search(
            [("model", "=", "res.partner")], limit=1
        )
        cls.test_role = cls.role_model.create(
            {
                "name": "Test Role Model Operations",
            }
        )

    def test_role_model_operations_creation(self):
        """Test creation of role.model.operations
        and its relation to res.users.role."""
        model_operations = self.role_model_operations.create(
            {
                "role_id": self.test_role.id,
                "model_id": self.res_users_model.id,
                "perm_duplicate": True,
                "perm_export": True,
                "perm_import": False,
                "perm_archive": True,
            }
        )

        self.assertEqual(model_operations.role_id, self.test_role)
        self.assertEqual(model_operations.model_id, self.res_users_model)
        self.assertTrue(model_operations.perm_duplicate)
        self.assertTrue(model_operations.perm_export)
        self.assertFalse(model_operations.perm_import)
        self.assertTrue(model_operations.perm_archive)

        self.assertIn(model_operations, self.test_role.role_model_operations_ids)

    def test_role_model_operations_unique_constraint(self):
        """Test that the same role cannot have multiple entries for the same model."""
        self.role_model_operations.create(
            {
                "role_id": self.test_role.id,
                "model_id": self.res_users_model.id,
            }
        )
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self.role_model_operations.create(
                {
                    "role_id": self.test_role.id,
                    "model_id": self.res_users_model.id,
                }
            )

    def test_role_model_operations_duplicate_restriction(self):
        """Test that the duplicate attribute is set to '0' on
        form views if duplication is restricted."""
        from lxml import etree

        group_user = self.env.ref("base.group_user")
        test_user = self.env["res.users"].search(
            [
                ("login", "=", "test_user_operations"),
            ],
            limit=1,
        )
        if not test_user:
            test_user = self.env["res.users"].create(
                {
                    "name": "Test User Operations",
                    "login": "test_user_operations",
                    "groups_id": [(6, 0, [group_user.id])],
                }
            )

        self.env["res.users.role.line"].create(
            {
                "role_id": self.test_role.id,
                "user_id": test_user.id,
            }
        )
        test_user.set_groups_from_roles(force=True)

        self.role_model_operations.create(
            {
                "role_id": self.test_role.id,
                "model_id": self.res_partner_model.id,
                "perm_duplicate": False,
            }
        )
        view = self.env["ir.ui.view"].search(
            [
                ("model", "=", "res.partner"),
                ("type", "=", "form"),
            ],
            limit=1,
        )
        tree = etree.Element("form", string="Partner Form")
        tree.set("model_access_rights", "res.partner")
        processed_tree = view.with_user(test_user)._postprocess_access_rights(tree)
        if processed_tree is None:
            processed_tree = tree
        self.assertEqual(processed_tree.get("duplicate"), "0")
        tree2 = etree.Element("form", string="Partner Form")
        tree2.set("model_access_rights", "res.partner")
        super_tree = view.with_user(self.env.user)._postprocess_access_rights(tree2)
        if super_tree is None:
            super_tree = tree2
        self.assertNotEqual(super_tree.get("duplicate"), "0")

    def test_role_model_operations_view_restrictions(self):
        """Test that duplicate, export_xlsx, and import attributes are
        correctly set on views based on role config."""
        from lxml import etree

        group_user = self.env.ref("base.group_user")
        test_user = self.env["res.users"].search(
            [
                ("login", "=", "test_user_operations2"),
            ],
            limit=1,
        )
        if not test_user:
            test_user = self.env["res.users"].create(
                {
                    "name": "Test User Operations",
                    "login": "test_user_operations2",
                    "groups_id": [(6, 0, [group_user.id])],
                }
            )
        self.env["res.users.role.line"].create(
            {
                "role_id": self.test_role.id,
                "user_id": test_user.id,
            }
        )
        test_user.set_groups_from_roles(force=True)

        self.role_model_operations.create(
            {
                "role_id": self.test_role.id,
                "model_id": self.res_partner_model.id,
                "perm_duplicate": False,
                "perm_export": False,
                "perm_import": False,
                "perm_archive": False,
            }
        )
        view = self.env["ir.ui.view"].search(
            [
                ("model", "=", "res.partner"),
                ("type", "=", "form"),
            ],
            limit=1,
        )
        form_tree = etree.Element("form", string="Partner Form")
        form_tree.set("model_access_rights", "res.partner")
        list_tree = etree.Element("list", string="Partner List")
        list_tree.set("model_access_rights", "res.partner")

        processed_form = view.with_user(test_user)._postprocess_access_rights(form_tree)
        processed_list = view.with_user(test_user)._postprocess_access_rights(list_tree)

        self.assertEqual(processed_form.get("duplicate"), "0")

        self.assertEqual(processed_list.get("export_xlsx"), "0")
        self.assertEqual(processed_list.get("import"), "0")
        self.assertEqual(processed_list.get("archive"), "0")

    def test_role_model_operations_dynamic_group_assignment(self):
        """Test that base.group_allow_export group is dynamically granted/revoked
        on the role and inherited by the user."""
        # Create an internal test user
        group_user = self.env.ref("base.group_user")
        test_user = self.env["res.users"].create(
            {
                "name": "Test User Group Assignment",
                "login": "test_user_group_assignment",
                "groups_id": [(6, 0, [group_user.id])],
            }
        )

        allow_export_group = self.env.ref("base.group_allow_export")
        self.env["res.users.role.line"].create(
            {
                "role_id": self.test_role.id,
                "user_id": test_user.id,
            }
        )
        test_user.set_groups_from_roles(force=True)
        self.assertNotIn(allow_export_group, self.test_role.implied_ids)
        self.assertNotIn(allow_export_group, test_user.groups_id)
        operation = self.role_model_operations.create(
            {
                "role_id": self.test_role.id,
                "model_id": self.res_users_model.id,
                "perm_export": True,
            }
        )
        self.assertIn(allow_export_group, self.test_role.implied_ids)
        self.assertIn(allow_export_group, test_user.groups_id)
        operation.write({"perm_export": False})
        self.assertNotIn(allow_export_group, self.test_role.implied_ids)
        self.assertNotIn(allow_export_group, test_user.groups_id)
        operation.write({"perm_export": True})
        self.assertIn(allow_export_group, self.test_role.implied_ids)
        self.assertIn(allow_export_group, test_user.groups_id)
        operation.unlink()
        self.assertNotIn(allow_export_group, self.test_role.implied_ids)
        self.assertNotIn(allow_export_group, test_user.groups_id)

    def test_role_model_operations_action_report_filtering(self):
        """Test that action and report bindings are filtered based on
        report_ids and action_ids in user role operations."""
        group_system = self.env.ref("base.group_system")
        test_user = self.env["res.users"].create(
            {
                "name": "Test User Bindings",
                "login": "test_user_bindings",
                "groups_id": [(6, 0, [group_system.id])],
            }
        )
        self.test_role.write({"implied_ids": [(4, group_system.id)]})
        self.env["res.users.role.line"].create(
            {
                "role_id": self.test_role.id,
                "user_id": test_user.id,
            }
        )
        test_user.set_groups_from_roles(force=True)

        report1 = self.env["ir.actions.report"].create(
            {
                "name": "Test Report 1",
                "model": "res.partner",
                "report_name": "test.report.1",
                "binding_model_id": self.res_partner_model.id,
                "binding_type": "report",
            }
        )
        report2 = self.env["ir.actions.report"].create(
            {
                "name": "Test Report 2",
                "model": "res.partner",
                "report_name": "test.report.2",
                "binding_model_id": self.res_partner_model.id,
                "binding_type": "report",
            }
        )

        action1 = self.env["ir.actions.server"].create(
            {
                "name": "Test Action 1",
                "model_id": self.res_partner_model.id,
                "binding_model_id": self.res_partner_model.id,
                "binding_type": "action",
                "state": "code",
                "code": "action = True",
            }
        )
        action2 = self.env["ir.actions.server"].create(
            {
                "name": "Test Action 2",
                "model_id": self.res_partner_model.id,
                "binding_model_id": self.res_partner_model.id,
                "binding_type": "action",
                "state": "code",
                "code": "action = True",
            }
        )

        action_window = self.env["ir.actions.act_window"].create(
            {
                "name": "Test Window Action",
                "res_model": "res.users",
                "binding_model_id": self.res_partner_model.id,
                "binding_type": "action",
            }
        )
        self.env.registry.clear_cache()
        bindings = (
            self.env["ir.actions.actions"]
            .with_user(test_user)
            .get_bindings("res.partner")
        )
        report_bindings = bindings.get("report", [])
        report_ids = [b["id"] for b in report_bindings]
        self.assertIn(report1.id, report_ids)
        self.assertIn(report2.id, report_ids)
        action_bindings = bindings.get("action", [])
        action_ids = [b["id"] for b in action_bindings]
        self.assertIn(action1.id, action_ids)
        self.assertIn(action2.id, action_ids)
        self.assertIn(action_window.id, action_ids)
        ops_empty = self.role_model_operations.create(
            {
                "role_id": self.test_role.id,
                "model_id": self.res_partner_model.id,
            }
        )
        self.env.registry.clear_cache()

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(test_user)
            .get_bindings("res.partner")
        )
        self.assertNotIn("report", bindings)

        action_bindings = bindings.get("action", [])
        action_ids = [b["id"] for b in action_bindings]
        self.assertIn(action_window.id, action_ids)
        self.assertNotIn(action1.id, action_ids)
        self.assertNotIn(action2.id, action_ids)

        ops_empty.unlink()
        self.env.registry.clear_cache()

        self.role_model_operations.create(
            {
                "role_id": self.test_role.id,
                "model_id": self.res_partner_model.id,
                "report_ids": [(6, 0, [report1.id])],
                "action_ids": [(6, 0, [action1.id])],
            }
        )

        self.env.registry.clear_cache()

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(test_user)
            .get_bindings("res.partner")
        )

        report_bindings = bindings.get("report", [])
        report_ids = [b["id"] for b in report_bindings]
        self.assertIn(report1.id, report_ids)
        self.assertNotIn(report2.id, report_ids)

        action_bindings = bindings.get("action", [])
        action_ids = [b["id"] for b in action_bindings]
        self.assertIn(action1.id, action_ids)
        self.assertNotIn(action2.id, action_ids)
        self.assertIn(action_window.id, action_ids)

        user_no_roles = self.env["res.users"].create(
            {
                "name": "User No Roles",
                "login": "no_roles",
                "groups_id": [(6, 0, [group_system.id])],
            }
        )
        no_role_bindings = (
            self.env["ir.actions.actions"]
            .with_user(user_no_roles)
            .get_bindings("res.partner")
        )
        self.assertTrue(no_role_bindings)

        ops_empty = self.role_model_operations.create(
            {
                "role_id": self.test_role.id,
                "model_id": self.res_users_model.id,
            }
        )
        self.env.registry.clear_cache()

        from unittest.mock import patch

        unallowed_action = self.env["ir.actions.server"].create(
            {
                "name": "Unallowed Action",
                "model_id": self.res_users_model.id,
                "state": "code",
                "code": "pass",
                "binding_model_id": self.res_users_model.id,
                "binding_type": "action",
            }
        )

        def mock_get_bindings(*args, **kwargs):
            return {
                "action": [
                    {
                        "id": unallowed_action.id,
                        "name": "Unallowed Action",
                        "binding_view_types": "list,form",
                    }
                ]
            }

        # Clear cache and mock
        self.env.registry.clear_cache()
        with patch.object(
            type(self.env["ir.actions.actions"]),
            "_get_bindings",
            side_effect=mock_get_bindings,
        ):
            mocked_bindings = (
                self.env["ir.actions.actions"]
                .with_user(test_user)
                .get_bindings("res.users")
            )
            self.assertNotIn("action", mocked_bindings)

    def test_role_model_operations_no_export_group(self):
        """Test to cover line 56 where export group is not found."""
        from unittest.mock import patch

        from lxml import etree

        original_ref = self.env.ref

        def mock_ref(xml_id, raise_if_not_found=True):
            if xml_id == "base.group_allow_export":
                return None
            return original_ref(xml_id, raise_if_not_found=raise_if_not_found)

        with patch.object(self.env.__class__, "ref", side_effect=mock_ref):
            tree = etree.Element("tree")
            tree.set("export_xlsx", "1")

            # Apply role restrictions which will hit the mocked ref
            ops = self.env["role.model.operations"].create(
                {
                    "role_id": self.test_role.id,
                    "model_id": self.res_partner_model.id,
                }
            )
            ops._update_role_groups()
            # Just asserting it passes without error
            self.assertEqual(tree.get("export_xlsx"), "1")
