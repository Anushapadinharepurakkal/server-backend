# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class RolePolicyMenuActionCommon(models.AbstractModel):
    _name = "role.menu.action.common"
    _description = "Role Policy - common code for ir.ui.menu and ir.actions.actions"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "role_ids" in vals:
                roles = self.env["res.users.role"].browse(vals["role_ids"][0][2])
                vals.setdefault("groups_id", []).extend(
                    [(4, x.id) for x in roles.mapped("group_id")]
                )
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "role_ids" in vals:
            for o in self:
                group_cmds = [(4, x.id) for x in o.role_ids.mapped("group_id")]
                if group_cmds:
                    o.write({"groups_id": group_cmds})
        return res
