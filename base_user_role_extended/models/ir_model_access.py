# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, tools
from odoo.tools import SQL


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    @api.model
    @tools.ormcache("self.env.uid", "mode")
    def _get_allowed_models(self, mode="read"):
        """
        Override to enforce exclusive role-based model access.

        When the current user has active roles and is not a bypass user:
          - Query ir.model.access using ONLY the role-associated group IDs
            (populated by ResUsersRole._update_role_model_access).
          - This makes the role group's access rights the sole authority,
            superseding every other group the user belongs to.
          - Global access rules (group_id IS NULL) are still respected as the
            baseline, matching standard Odoo behaviour.

        For bypass users (admin/root) or users with no active roles:
          - Delegates to super() → standard all-groups resolution.
        """
        if self.env.user.bypass_role_policy:
            return super()._get_allowed_models(mode)

        # Collect the group_id of each active role for this user.
        user = self.env.user.sudo()
        roles = user.role_line_ids.filtered(
            lambda line: line.is_enabled
        ).mapped("role_id")

        if not roles:
            # No active roles → normal Odoo group-based access.
            return super()._get_allowed_models(mode)

        role_group_ids = tuple(roles.mapped("group_id")._ids)

        # Query ir.model.access restricted EXCLUSIVELY to the role group IDs.
        # No global (NULL group) fallback — if the role group's access record
        # for a model is deleted, that model becomes inaccessible immediately.
        self.flush_model()
        rows = self.env.execute_query(SQL(
            """
            SELECT m.model
              FROM ir_model_access a
              JOIN ir_model m ON (m.id = a.model_id)
             WHERE a.perm_%s
               AND a.active
               AND a.group_id IN %s
            GROUP BY m.model
            """,
            SQL(mode),
            role_group_ids,
        ))
        return frozenset(row[0] for row in rows)