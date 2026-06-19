# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    role_model_operations_ids = fields.One2many(
        comodel_name="res.users.role.model.operations",
        inverse_name="role_id",
        string="Model Operations",
    )

    view_access_rule_ids = fields.One2many(
        comodel_name="view.access.rule",
        inverse_name="role_id",
        string="View Access Rules",
    )
