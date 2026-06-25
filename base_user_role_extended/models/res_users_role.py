# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, tools

class ResUsersRole(models.Model):
    _name = "res.users.role"
    _inherit = ["res.users.role"]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_role_model_access()
        return records

    def write(self, vals):
        update_access = "implied_ids" in vals
        res = super().write(vals)
        if update_access:
            self._update_role_model_access()
        return res

    def _update_role_model_access(self):
        """
        Synchronize the access rights from the associated user groups
        into the role's model access records.
        """
        # Invalidate the cache to avoid stale data from base_user_role's sudo() writes
        self.invalidate_recordset(["implied_ids"])
        self.mapped("group_id").invalidate_recordset(["implied_ids"])

        for role in self:
            # Get all model access from the groups implied by this role using sudo()
            # to ensure we fetch the most up-to-date groups from the database.
            access_records = role.sudo().implied_ids.mapped("model_access")
            
            # Combine permissions per model to prevent unique constraint violations
            model_permissions = self.parse_model_access(access_records)
            
            # Also clear existing standard ir.model.access records for this group
            self.env["ir.model.access"].search([("group_id", "=", role.group_id.id)]).unlink()
            
            # Create the updated role model access records and ir.model.access records
            ir_access_vals = []
            for model_id, perms in model_permissions.items():
                model_rec = self.env["ir.model"].browse(model_id)
                ir_access_vals.append({
                    "name": f"{model_rec.model}",
                    "model_id": model_id,
                    "group_id": role.group_id.id,
                    "perm_read": perms["perm_read"],
                    "perm_write": perms["perm_write"],
                    "perm_create": perms["perm_create"],
                    "perm_unlink": perms["perm_unlink"],
                })
            
            if ir_access_vals:
                self.env["ir.model.access"].create(ir_access_vals)

    def parse_model_access(self, model_access):
        model_permissions = {}
        for acc in model_access:
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
        return model_permissions

    def unlink(self):
        self.env["role.model.access"].search([("role_id", "in", self.ids)]).unlink()
        return super().unlink()
