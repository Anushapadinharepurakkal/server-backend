# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def post_init_hook(env):
    """
    Remove groups from menuitems, views, actions and users since the standard groups
    are replaced by role groups when installing this module.
    """
    env = env(context=dict(env.context, active_test=False, role_policy_init=True))
    menus = env["ir.ui.menu"].search([])
    menus.write({"groups_id": [(5,)]})
