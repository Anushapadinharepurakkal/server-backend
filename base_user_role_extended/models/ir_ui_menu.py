# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools
from odoo.tools import config


class IrUiMenu(models.Model):
    _name = "ir.ui.menu"
    _inherit = ["ir.ui.menu", "role.menu.action.common"]

    role_ids = fields.Many2many(
        comodel_name="res.users.role",
        relation="res_role_menu_rel",
        column1="menu_id",
        column2="role_id",
        string="Roles",
    )

    @api.model
    @tools.ormcache("frozenset(self.env.user.groups_id.ids)", "debug")
    def _visible_menu_ids(self, debug=False):
        """
        Hide menus that are explicitly restricted by the user's roles.
        """
        if self.env.user.bypass_role_policy or config.get("test_enable"):
            return self._visible_menu_ids_user_admin(debug=debug)

        user_roles = self.env.user.role_line_ids.filtered(
            lambda lines: lines.is_enabled
        ).mapped("role_id")
        user_role_groups = user_roles.mapped("group_id")

        return self._get_visible_menus_core(debug=debug, deny_groups=user_role_groups)

    @api.model
    @tools.ormcache("frozenset(self.env.user.groups_id.ids)", "debug")
    def _visible_menu_ids_user_admin(self, debug=False):
        """
        Same logic as base but we ignore the role groups for user_root and user_admin.
        """
        return self._get_visible_menus_core(
            debug=debug, deny_groups=self.env["res.groups"]
        )

    def _get_visible_menus_core(self, debug=False, deny_groups=None):
        """
        Core logic to evaluate menu visibility:
        1. Treat role groups as transparent for standard Odoo ALLOW checks.
        2. Apply deny_groups to explicitly hide restricted menus.
        """
        context = {"ir.ui.menu.full_list": True}
        menus = self.with_context(**context).search([]).sudo()

        groups = self.env.user.groups_id
        if not debug:
            groups = groups - self.env.ref("base.group_no_one")

        # 1. Base visibility: Must have standard groups (if any non-role groups exist)
        menus = menus.filtered(
            lambda menu: not menu.groups_id.filtered(lambda r: not r.role)
            or menu.groups_id & groups
        )

        # 2. Apply Role Restrictions: 
        # HIDE if the menu has a role group that the user has
        if deny_groups:
            menus = menus.filtered(lambda menu: not (menu.groups_id & deny_groups))

        # 3. take apart menus that have an action
        action_menus = menus.filtered(lambda m: m.action and m.action.exists())
        folder_menus = menus - action_menus
        visible = self.browse()

        # 4. process action menus, check whether their action is allowed
        access = self.env["ir.model.access"]
        MODEL_BY_TYPE = {
            "ir.actions.act_window": "res_model",
            "ir.actions.report": "model",
            "ir.actions.server": "model_name",
        }
        for menu in action_menus:
            action = menu.action
            model_name = (
                action._name in MODEL_BY_TYPE and action[MODEL_BY_TYPE[action._name]]
            )
            if not model_name or access.check(model_name, "read", False):
                # make menu visible, and its folder ancestors, too
                visible += menu
                menu = menu.parent_id
                while menu and menu in folder_menus and menu not in visible:
                    visible += menu
                    menu = menu.parent_id

        return set(visible.ids)
