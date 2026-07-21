# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    bypass_role_policy = fields.Boolean(
        compute="_compute_bypass_role_policy",
        help="If checked, this record bypasses role-based"
        "view combination evaluation checks",
    )

    def _compute_bypass_role_policy(self):
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        root = self.env.ref("base.user_root", raise_if_not_found=False)
        for user in self:
            user.bypass_role_policy = user in (admin, root)
