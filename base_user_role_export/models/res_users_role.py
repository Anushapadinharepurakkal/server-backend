from odoo import api, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    def _update_role_model_access(self, perm_fields={"perm_export": False}):
        super()._update_role_model_access(perm_fields)