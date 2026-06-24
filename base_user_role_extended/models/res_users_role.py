# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class ResUsersRole(models.Model):
    _name = "res.users.role"
    _inherit = ["res.users.role"]

    role_model_access_ids = fields.One2many(
        "role.model.access", "role_id", string="Role Model Access"
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_role_model_access()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "implied_ids" in vals:
            self._update_role_model_access()
        return res

    def _update_role_model_access(self):
        """
        Synchronize the access rights from the associated user groups
        into the role's model access records.
        """
        for role in self:
            # Get all model access from the groups implied by this role
            access_records = role.implied_ids.mapped("model_access")
            
            # Combine permissions per model to prevent unique constraint violations
            model_permissions = {}
            for acc in access_records:
                model_id = acc.model_id.id
                if model_id not in model_permissions:
                    model_permissions[model_id] = {
                        "perm_read": False,
                        "perm_write": False,
                        "perm_create": False,
                        "perm_unlink": False,
                    }
                model_permissions[model_id]["perm_read"] |= acc.perm_read
                model_permissions[model_id]["perm_write"] |= acc.perm_write
                model_permissions[model_id]["perm_create"] |= acc.perm_create
                model_permissions[model_id]["perm_unlink"] |= acc.perm_unlink
            
            # Clear existing role model access records to keep it in sync
            role.role_model_access_ids.unlink()
            
            # Create the updated role model access records
            new_access_vals = []
            for model_id, perms in model_permissions.items():
                new_access_vals.append({
                    "role_id": role.id,
                    "model_id": model_id,
                    "perm_read": perms["perm_read"],
                    "perm_write": perms["perm_write"],
                    "perm_create": perms["perm_create"],
                    "perm_unlink": perms["perm_unlink"],
                })
            
            if new_access_vals:
                self.env["role.model.access"].create(new_access_vals)

    def unlink(self):
        self.env["role.model.access"].search([("role_id", "in", self.ids)]).unlink()