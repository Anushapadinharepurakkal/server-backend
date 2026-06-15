from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ViewAccessRule(models.Model):
    _name = "view.access.rule"
    _description = "View Access Rule"
    _order = "role_id, model_id, view_id"

    role_id = fields.Many2one(
        "res.users.role",
        string="Role",
        required=True,
        ondelete="cascade",
        help="The role to which this view access rule applies.",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        help="The model (e.g. Sale Order, Invoice) this rule applies to.",
    )
    model_name = fields.Char(
        related="model_id.model", string="Model Name", store=True, readonly=True
    )
    view_id = fields.Many2one(
        "ir.ui.view",
        string="View",
        domain="[('model', '=', model_name)]",
        ondelete="cascade",
        help="The specific view. Leave empty to apply to all views of the model.",
    )
    view_xml_id = fields.Char(
        string="View External Identifier", related="view_id.xml_id", store=True
    )
    view_type = fields.Selection(
        [
            ("form", "Form"),
            ("list", "List"),
            ("kanban", "Kanban"),
        ],
        string="View Type",
        required=True,
        default="form",
    )
    element = fields.Char(
        string="Element",
        required=True,
        help="Technical name of the field or button "
        "(e.g. amount_total, action_confirm).",
    )

    # Access rule flags
    rule_invisible = fields.Char(string="Invisible", help="Invisible Condition")
    rule_readonly = fields.Char(string="Readonly", help="Readonly Condition .")
    rule_required = fields.Char(string="Required", help="Required Condition .")

    _sql_constraints = [
        (
            "unique_rule",
            "UNIQUE(role_id, model_id, view_id, view_type,element)",
            "A rule for this Role + Model + View + Element already exists.",
        )
    ]

    @api.constrains("rule_invisible", "rule_readonly", "rule_required")
    def _check_at_least_one_rule(self):
        for rec in self:
            if not any((rec.rule_invisible, rec.rule_readonly, rec.rule_required)):
                raise ValidationError(
                    _(
                        "At least one access rule (Invisible, Readonly, or Required) "
                        "must be set."
                    )
                )
