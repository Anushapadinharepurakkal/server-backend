# Copyright 2026 CIT Services
# License LGPL-3.0  or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    def _update_role_model_access(self, perm_fields=None):
        if perm_fields is None:
            perm_fields = {}
        perm_fields.setdefault("perm_duplicate", False)
        return super()._update_role_model_access(perm_fields)
