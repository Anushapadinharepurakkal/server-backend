# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    bypass_role_policy = fields.Boolean(
        compute="_compute_bypass_role_policy",
        store=True,
        help="If checked, this record bypasses role-based view combination \
              valuation checks (e.g., for Super-Administrators).",
    )

    def _compute_bypass_role_policy(self):
        for user in self:
            if user in (
                self.env.ref("base.user_admin"),
                self.env.ref("base.user_root"),
            ):
                user.bypass_role_policy = True
            else:
                user.bypass_role_policy = False
