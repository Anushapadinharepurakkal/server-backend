from odoo import fields, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    view_access_rule_ids = fields.One2many(
        comodel_name="view.access.rule",
        inverse_name="role_id",
        string="View Access Rules",
    )
