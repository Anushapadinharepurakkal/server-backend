# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    def _postprocess_access_rights(self, tree):
        """
        Dynamically inject UI restrictions based on the active user's roles.
        Accepts only 'tree' (the XML node architecture element).
        """
        # Bypass checks for the superuser
        if self.env.is_superuser():
            return
        target_model = tree.get("model_access_rights")
        tree = super()._postprocess_access_rights(tree)
        if target_model and tree.tag in ("form", "list", "kanban"):
            current_user = self.env.user
            active_role_lines = current_user._get_enabled_roles()

            if active_role_lines:
                active_roles = active_role_lines.mapped("role_id")
                operations = (
                    self.env["res.users.role.model.operations"]
                    .sudo()
                    .search(
                        [
                            ("role_id", "in", active_roles.ids),
                            ("model_id.model", "=", target_model),
                        ]
                    )
                )
                if operations:
                    if not any(op.perm_duplicate for op in operations):
                        tree.set("duplicate", "0")

                    if not any(op.perm_export for op in operations):
                        tree.set("export_xlsx", "0")

                    if not any(op.perm_import for op in operations):
                        tree.set("import", "0")

                    if not any(op.perm_archive for op in operations):
                        tree.set("archive", "0")
        return tree
