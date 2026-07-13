# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Base User Role Archive",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "summary": "Extends user roles for archive access in model access",
    "author": "CIT Services, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/server-backend",
    "license": "AGPL-3",
    "depends": ["base_user_role_extended"],
    "assets": {
        "web.assets_backend": [
            "base_user_role_archive/static/src/js/archive_access_patch.esm.js",
        ],
    },
    "installable": True,
}
