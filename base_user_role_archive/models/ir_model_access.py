# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models, tools
from odoo.tools import SQL


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    @api.model
    @tools.ormcache("self.env.uid", "mode")
    def _get_allowed_models(self, mode="read"):
        """Extend to support archive/unarchive access modes."""
        if mode not in ("archive", "unarchive"):
            return super()._get_allowed_models(mode)

        # Role users: query restricted to role-group IDs + global rules
        user = self.env.user.sudo()
        if not user.bypass_role_policy:
            roles = user.role_line_ids.filtered(lambda line: line.is_enabled).mapped(
                "role_id"
            )
            if roles:
                role_group_ids = tuple(roles.mapped("group_id")._ids)
                return self._get_archive_allowed_models_with_groups(mode, role_group_ids)

        # Bypass users or users with no active roles: all groups + global rules
        return super()._get_allowed_models(mode)

    @api.model
    def get_archive_access(self, model):
        """Return archive/unarchive permission for the current user and model.
        Called by the JS layer to decide whether to show Archive/Unarchive
        action menu items.
        """
        return {
            "can_archive": self.check(model, "archive", raise_exception=False),
            "can_unarchive": self.check(model, "unarchive", raise_exception=False),
        }
