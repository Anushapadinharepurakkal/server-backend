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

    def _update_role_model_access(self, perm_fields=None):
        """
        Synchronize the access rights from the associated user groups
        into the role's model access records.
        """
        all_perm_fields = self.collect_all_perm_fields(perm_fields)
        self.invalidate_recordset(["implied_ids"])
        self.mapped("group_id").invalidate_recordset(["implied_ids"])
        for role in self:
            role._clear_existing_model_access()

            access_records = role.model_access_ids
            model_permissions = self.parse_model_access(
                access_records, perm_fields=all_perm_fields
            )

            ir_access_vals = role._prepare_model_access_vals(model_permissions)
            if ir_access_vals:
                self.env["ir.model.access"].create(ir_access_vals)
    
    def collect_all_perm_fields(self, perm_fields=None):
        default_perm_fields = {
            "perm_read": False,
            "perm_write": False,
            "perm_create": False,
            "perm_unlink": False,
        }
        if perm_fields:
            default_perm_fields.update(perm_fields)
        perm_fields = default_perm_fields
        return perm_fields
    
    @api.depends("implied_ids", "implied_ids.model_access")
    def _compute_model_access_ids(self):
        super()._compute_model_access_ids()
        for rec in self:
            rec.model_access_ids = rec.sudo().trans_implied_ids.model_access
            rec.model_access_count = len(rec.model_access_ids)

    def _clear_existing_model_access(self):
        self.ensure_one()
        self.env["ir.model.access"].search(
            [("group_id", "=", self.group_id.id)]
        ).unlink()

    def _prepare_model_access_vals(self, model_permissions):
        self.ensure_one()
        ir_access_vals = []
        for model_rec, perms in model_permissions.items():
            vals = {
                "name": f"{model_rec.model}",
                "model_id": model_rec.id,
                "group_id": self.group_id.id,
            }
            vals.update(perms)
            ir_access_vals.append(vals)
        return ir_access_vals

    def parse_model_access(self, model_access, perm_fields):
        model_permissions = {}
        for access in model_access:
            model_rec = access.model_id
            if model_rec not in model_permissions:
                model_permissions[model_rec] = perm_fields.copy()
            for field_name in perm_fields:
                model_permissions[model_rec][field_name] |= getattr(access, field_name)
        return model_permissions
