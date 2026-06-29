# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    def _update_role_model_access(self, perm_fields=None):
        if perm_fields is None:
            perm_fields = {}
        perm_fields.update(
            {
                "perm_archive": False,
                "perm_unarchive": False,
            }
        )
        return super()._update_role_model_access(perm_fields)
