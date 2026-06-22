# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ResUsersRoleModelOperations(models.Model):
    _name = "role.model.operations"
    _description = "Role Model Operations"

    role_id = fields.Many2one(
        comodel_name="res.users.role",
        string="Role",
        required=True,
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
    )
    perm_duplicate = fields.Boolean(string="Duplicate")
    perm_export = fields.Boolean(string="Export")
    perm_import = fields.Boolean(string="Import")
    perm_archive = fields.Boolean(string="Archive")
    report_ids = fields.Many2many(
        comodel_name="ir.actions.report",
        string="Reports",
        domain="['|', ('model_id', '=', model_id), "
        "('binding_model_id', '=', model_id)]",
    )
    action_ids = fields.Many2many(
        comodel_name="ir.actions.server",
        relation="res_users_role_model_ops_action_server_rel_new",
        column1="operation_id",
        column2="action_server_id",
        string="Actions",
        domain="['|', ('model_id', '=', model_id), "
        "('binding_model_id', '=', model_id)]",
    )

    _sql_constraints = [
        (
            "role_model_uniq",
            "unique(role_id, model_id)",
            "Model level operations must be unique per model and role!",
        )
    ]

    def _update_role_groups(self):
        """Update the implied_ids (groups) of the affected
        roles based on the perm_export flag."""
        allow_export_group = self.env.ref(
            "base.group_allow_export", raise_if_not_found=False
        )
        if not allow_export_group:
            return

        roles = self.mapped("role_id")
        for role in roles:
            has_export_enabled = (
                self.env["role.model.operations"]
                .sudo()
                .search_count(
                    [
                        ("role_id", "=", role.id),
                        ("perm_export", "=", True),
                    ]
                )
                > 0
            )
            if has_export_enabled:
                if allow_export_group not in role.implied_ids:
                    role.write({"implied_ids": [(4, allow_export_group.id)]})
            else:
                if allow_export_group in role.implied_ids:
                    role.write({"implied_ids": [(3, allow_export_group.id)]})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_role_groups()
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._update_role_groups()
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        roles = self.mapped("role_id")
        res = super().unlink()

        allow_export_group = self.env.ref(
            "base.group_allow_export", raise_if_not_found=False
        )
        if allow_export_group:
            for role in roles:
                has_export_enabled = (
                    self.env["role.model.operations"]
                    .sudo()
                    .search_count(
                        [
                            ("role_id", "=", role.id),
                            ("perm_export", "=", True),
                        ]
                    )
                    > 0
                )
                if not has_export_enabled:
                    if allow_export_group in role.implied_ids:
                        role.write({"implied_ids": [(3, allow_export_group.id)]})
        self.env.registry.clear_cache()
        return res
