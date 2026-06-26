# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models



class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def fetch_export_models(self):
        """
        Enforces exclusive role-based access for export models.
        """
        if not hasattr(super(), "fetch_export_models"):
            return []

        if self.env.user.bypass_role_policy:
            return super().fetch_export_models()

        user = self.env.user.sudo()
        roles = user.role_line_ids.filtered(lambda line: line.is_enabled).mapped(
            "role_id"
        )

        if not roles:
            return super().fetch_export_models()

        role_group_ids = tuple(roles.mapped("group_id").ids)
        accessobj = self.env["ir.model.access"].sudo()

        if "perm_export" not in accessobj._fields:
            return super().fetch_export_models()

        accessobj_ids = accessobj.search(
            [("perm_export", "=", True), ("group_id", "in", role_group_ids)]
        )
        return list(set(accessobj_ids.mapped("model_id.model")))