# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

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

    def _update_role_model_access(self, perm_fields={}):
        """
        Synchronize the access rights from the associated user groups
        into the role's model access records.
        """
        default_perm_fields = {
            "perm_read": False, 
            "perm_write": False, 
            "perm_create": False, 
            "perm_unlink": False
        }
        if perm_fields:
            default_perm_fields.update(perm_fields)
        perm_fields = default_perm_fields

        # Invalidate the cache to avoid stale data from base_user_role's sudo() writes
        self.invalidate_recordset(["implied_ids"])
        self.mapped("group_id").invalidate_recordset(["implied_ids"])

        for role in self:
            access_records = role._get_implied_model_access_records()
            model_permissions = self.parse_model_access(access_records, perm_fields=perm_fields)
            
            role._clear_existing_model_access()
            
            ir_access_vals = role._prepare_model_access_vals(model_permissions)
            if ir_access_vals:
                self.env["ir.model.access"].create(ir_access_vals)

    def _get_implied_model_access_records(self):
        self.ensure_one()
        # Get all model access from the groups implied by this role using sudo()
        # to ensure we fetch the most up-to-date groups from the database.
        return self.sudo().implied_ids.mapped("model_access")

    def _clear_existing_model_access(self):
        self.ensure_one()
        # Clear existing standard ir.model.access records for this group
        self.env["ir.model.access"].search([("group_id", "=", self.group_id.id)]).unlink()

    def _prepare_model_access_vals(self, model_permissions):
        self.ensure_one()
        ir_access_vals = []
        for model_id, perms in model_permissions.items():
            model_rec = self.env["ir.model"].browse(model_id)
            vals = {
                "name": f"{model_rec.model}",
                "model_id": model_id,
                "group_id": self.group_id.id,
            }
            vals.update(perms)
            ir_access_vals.append(vals)
        return ir_access_vals

    def parse_model_access(self, model_access, perm_fields):
        model_permissions = {}
        for acc in model_access:
            model_id = acc.model_id.id
            if model_id not in model_permissions:
                model_permissions[model_id] = perm_fields
            for f in perm_fields:
                model_permissions[model_id][f] |= getattr(acc, f)
        return model_permissions

    def unlink(self):
        self.env["role.model.access"].search([("role_id", "in", self.ids)]).unlink()
        return super().unlink()
