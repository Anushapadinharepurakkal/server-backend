# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrActionsActions(models.Model):
    _inherit = "ir.actions.actions"

    @api.model
    def get_bindings(self, model_name):
        result = super().get_bindings(model_name)

        # Bypass checks for the superuser
        if self.env.is_superuser():
            return result

        current_user = self.env.user
        active_role_lines = current_user._get_enabled_roles()
        if not active_role_lines:
            return result

        active_roles = active_role_lines.mapped("role_id")
        operations = (
            self.env["role.model.operations"]
            .sudo()
            .search(
                [
                    ("role_id", "in", active_roles.ids),
                    ("model_id.model", "=", model_name),
                ]
            )
        )
        if not operations:
            return result

        allowed_report_ids = operations.mapped("report_ids").ids
        allowed_action_ids = operations.mapped("action_ids").ids

        # Get all server actions bound to this model
        server_action_ids = (
            self.env["ir.actions.server"]
            .sudo()
            .search([("binding_model_id.model", "=", model_name)])
            .ids
        )

        filtered_result = dict(result)

        if "report" in filtered_result:
            filtered_result["report"] = [
                act
                for act in filtered_result["report"]
                if act.get("id") in allowed_report_ids
            ]
            if not filtered_result["report"]:
                filtered_result.pop("report")

        if "action" in filtered_result:
            filtered_result["action"] = [
                act
                for act in filtered_result["action"]
                if act.get("id") not in server_action_ids
                or act.get("id") in allowed_action_ids
            ]
            if not filtered_result["action"]:
                filtered_result.pop("action")

        return filtered_result
