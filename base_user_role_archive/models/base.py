# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class Base(models.AbstractModel):
    _inherit = "base"

    def write(self, vals):
        """Enforce archive/unarchive access rights when toggling the active field."""
        if "active" in vals:
            mode = "unarchive" if vals.get("active") else "archive"
            self.env["ir.model.access"].check(self._name, mode)
        return super().write(vals)
