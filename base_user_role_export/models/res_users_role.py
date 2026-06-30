# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    def _update_role_model_access(self, perm_fields=None):
        """Override to include perm_export in the default permission fields."""
        if perm_fields is None:
            perm_fields = {"perm_export": False}
        return super()._update_role_model_access(perm_fields)

    @api.model
    def default_get(self, fields_list):
        """Pre-populate implied_ids with the 'Access to export feature' group.

        The group ``base.group_allow_export`` (labelled **Access to export
        feature** in the UI) **must** be present in a role's implied groups
        for the export feature to work for users assigned that role.  This
        default makes it impossible to forget: every new role starts with the
        group already linked so administrators only need to remove it when
        export access is explicitly unwanted.
        """
        res = super().default_get(fields_list)
        if "implied_ids" in fields_list:
            group_allow_export = self.env.ref(
                "base.group_allow_export", raise_if_not_found=False
            )
            if group_allow_export:
                res["implied_ids"] = [Command.link(group_allow_export.id)]
        return res
