# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError
from odoo.tools import SQL


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    perm_archive = fields.Boolean("Archive Access", default=True)
    perm_unarchive = fields.Boolean("Unarchive Access", default=True)

    @api.model
    @tools.ormcache("self.env.uid", "mode")
    def _get_allowed_models(self, mode="read"):
        """Extend to support archive/unarchive access modes.

        For users with active roles: replicates the role-group SQL query from
        base_user_role_extended using the perm_archive / perm_unarchive columns
        added by this module, WITHOUT calling super() (which would invoke Odoo
        core and crash for non-standard modes).

        For bypass users or users with no active roles: falls back to a
        standard all-groups query against the new permission columns.

        For all other modes: delegates entirely to super().
        """
        if mode not in ("archive", "unarchive"):
            return super()._get_allowed_models(mode)

        self.flush_model()

        # Role users: query restricted to role-group IDs only
        # (mirrors base_user_role_extended logic for standard modes).
        user = self.env.user.sudo()
        if not user.bypass_role_policy:
            roles = user.role_line_ids.filtered(lambda line: line.is_enabled).mapped(
                "role_id"
            )
            if roles:
                role_group_ids = tuple(roles.mapped("group_id")._ids)
                rows = self.env.execute_query(
                    SQL(
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
                    )
                )
                return frozenset(row[0] for row in rows)

        # Bypass users or users with no active roles: all groups.
        rows = self.env.execute_query(
            SQL(
                """
            SELECT m.model
              FROM ir_model_access a
              JOIN ir_model m ON (m.id = a.model_id)
              JOIN res_groups_users_rel gu ON (gu.gid = a.group_id)
             WHERE a.perm_%s
               AND a.active
               AND gu.uid = %s
            GROUP BY m.model
            """,
                SQL(mode),
                self.env.uid,
            )
        )
        return frozenset(row[0] for row in rows)

    @api.model
    @tools.ormcache("self.env.uid", "model", "mode")
    def check(self, model, mode="read", raise_exception=True):
        """Extend to enforce archive/unarchive access rights."""
        if mode not in ("archive", "unarchive"):
            return super().check(model, mode=mode, raise_exception=raise_exception)
        if self.env.su:
            return True
        has_access = model in self._get_allowed_models(mode)
        if not has_access and raise_exception:
            raise AccessError(
                _(
                    "You do not have %(mode)s access for %(model)s",
                    mode=mode,
                    model=model,
                )
            )
        return has_access

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
