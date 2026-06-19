{
    "name": "Base User Role Extended",
    "version": "18.0.1.0.0",
    "summary": "Extends user roles with additional access control features",
    "author": "CIT Services, Odoo Community Association (OCA)",
    "company": "CIT Services",
    "license": "LGPL-3",
    "website": "https://github.com/OCA/server-backend",
    "depends": [
        "base_user_role",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/view_access_rule_views.xml",
        "views/res_users_views.xml",
    ],
    "installable": True,
}
