from odoo.tests.common import TransactionCase


class TestViewAccessRule(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.role = cls.env["res.users.role"].create(
            {
                "name": "Test View Access Role",
                "implied_ids": [(4, cls.env.ref("base.group_user").id)],
            }
        )

        cls.model_partner = cls.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )
        cls.view_partner_form = cls.env["ir.ui.view"].search(
            [("model", "=", "res.partner"), ("type", "=", "form")], limit=1
        )
        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Test Access Rule User",
                "login": "test_access_rule_user",
                "email": "test@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.role.write(
            {
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "user_id": cls.test_user.id,
                        },
                    )
                ]
            }
        )

    def test_01_view_type_computation_and_persistence(self):
        """Test that view_type is correctly computed from view_id
        and persisted on save."""
        rule = self.env["view.access.rule"].create(
            {
                "role_id": self.role.id,
                "model_id": self.model_partner.id,
                "view_id": self.view_partner_form.id,
                "target_element_ui": 'field name="email"',
                "rule_invisible": "True",
            }
        )
        self.assertEqual(
            rule.view_type, "form", "view_type should be computed as 'form'"
        )
        rule.invalidate_model(["view_type"])
        stored_rule = self.env["view.access.rule"].browse(rule.id)
        self.assertEqual(
            stored_rule.view_type,
            "form",
            "view_type must be persisted as 'form' after save",
        )

    def test_02_manual_view_type_without_view_id(self):
        """Test that view_type can be manually selected when view_id is
        False and is persisted."""
        rule = self.env["view.access.rule"].create(
            {
                "role_id": self.role.id,
                "model_id": self.model_partner.id,
                "view_id": False,
                "view_type": "list",
                "target_element_ui": 'field name="email"',
                "rule_invisible": "True",
            }
        )

        self.assertEqual(rule.view_type, "list", "view_type should remain 'list'")

        rule.invalidate_model(["view_type"])
        stored_rule = self.env["view.access.rule"].browse(rule.id)
        self.assertEqual(
            stored_rule.view_type, "list", "view_type 'list' must be persisted"
        )

    def test_03_resolved_element_computation(self):
        """Test that resolved_element is correctly computed based on
        target_element_ui."""
        rule = self.env["view.access.rule"].create(
            {
                "role_id": self.role.id,
                "model_id": self.model_partner.id,
                "view_id": self.view_partner_form.id,
                "target_element_ui": 'button name="action_some_action"',
                "rule_invisible": "True",
            }
        )
        self.assertEqual(rule.resolved_element, 'button name="action_some_action"')

    def test_04_get_view_modifier_injection(self):
        """Test that the get_view override correctly injects modifiers to the arch."""
        self.env["view.access.rule"].create(
            {
                "role_id": self.role.id,
                "model_id": self.model_partner.id,
                "view_id": self.view_partner_form.id,
                "target_element_ui": "email",
                "rule_invisible": "True",
            }
        )
        PartnerModel = self.env["res.partner"].with_user(self.test_user)
        res = PartnerModel.get_view(view_id=self.view_partner_form.id, view_type="form")
        arch = res.get("arch", "")
        self.assertIn('name="email"', arch, "Email field should be present in the view")
        self.assertIn(
            'invisible="True"',
            arch,
            "invisible='True' should be injected on the field or its label",
        )
