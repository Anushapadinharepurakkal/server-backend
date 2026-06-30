# Copyright 2026 CIT Services
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    perm_duplicate = fields.Boolean("Duplicate Access", default=True)

    @api.model
    def check_duplicate(self, model_name, raise_exception=True):
        """Check if the current user has permission to duplicate
        for model.
        """
        if self.env.su or self.env.user.bypass_role_policy:
            return True
        user = self.env.user.sudo()
        roles = user.role_line_ids.filtered(lambda line: line.is_enabled).mapped(
            "role_id"
        )
        group_ids = roles.mapped("group_id").ids if roles else user.groups_id.ids

        domain = [
            ("model_id.model", "=", model_name),
            ("active", "=", True),
            ("perm_duplicate", "=", True),
            "|",
            ("group_id", "=", False),
            ("group_id", "in", group_ids),
        ]
        has_duplicate = self.sudo().search_count(domain) > 0

        if not has_duplicate and raise_exception:
            raise AccessError(
                _("You are not allowed to duplicate records of model %s.") % model_name
            )
        return has_duplicate
