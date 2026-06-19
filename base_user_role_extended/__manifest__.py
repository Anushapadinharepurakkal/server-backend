{
    "name": "Base User Role Extended",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "summary": "Extends user roles with additional access control features",
    "author": "CIT Services, Odoo Community Association (OCA)",
    "company": "CIT Services",
    "website": "https://github.com/OCA/server-backend",
    "license": "LGPL-3",
    "depends": ["base_user_role", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_users_role.xml",
        "views/view_access_rule_views.xml",
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "base_user_role_extended/static/src/views/form/form_controller.esm.js",
            "base_user_role_extended/static/src/views/list/list_controller.esm.js",
        ],
    },
    "installable": True,
}
