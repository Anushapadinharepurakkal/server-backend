import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ViewAccessRule(models.Model):
    _name = "view.access.rule"
    _description = "View Access Rule"
    _order = "sequence, role_id, model_id, view_id"

    sequence = fields.Integer(
        default=10,
        help="Gives the sequence order when applying rules."
        "Higher sequence rules override lower ones.",
    )
    role_id = fields.Many2one(
        "res.users.role",
        string="Role",
        required=True,
        ondelete="cascade",
        help="The role to which this view access rule applies.",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        help="The model (e.g. Sale Order, Invoice) this rule applies to.",
    )
    model_name = fields.Char(
        related="model_id.model", string="Model Name", store=True, readonly=True
    )
    view_id = fields.Many2one(
        "ir.ui.view",
        string="View",
        domain="[('model', '=', model_name)]",
        ondelete="cascade",
        help="The specific view. Leave empty to apply to all views of the model.",
    )
    view_xml_id = fields.Char(
        string="View External Identifier", related="view_id.xml_id", store=True
    )
    view_type = fields.Selection(
        [
            ("list", "List"),
            ("form", "Form"),
            ("graph", "Graph"),
            ("pivot", "Pivot"),
            ("calendar", "Calendar"),
            ("kanban", "Kanban"),
            ("search", "Search"),
            ("qweb", "QWeb"),
        ],
        compute="_compute_view_type",
        store=True,
        readonly=False,
    )
    rule_invisible = fields.Char(string="Invisible", help="Invisible Condition")
    rule_readonly = fields.Char(string="Readonly", help="Readonly Condition .")
    rule_required = fields.Char(string="Required", help="Required Condition .")

    target_element_ui = fields.Char(
        string="Element",
        help="Specify the view element. E.g.\n"
        'button name="button_cancel"\n'
        "xpath expr=\"//page[@id='invoice_tab']\"",
    )

    resolved_element = fields.Char(
        string="Element (internal)",
        compute="_compute_resolved_element",
        store=True,
        help="Technical field containing the element after XML_ID resolution",
    )

    _sql_constraints = [
        (
            "unique_rule",
            "UNIQUE(role_id, model_id, view_id, view_type,target_element_ui)",
            "A rule for this Role + Model + View + Element already exists.",
        )
    ]

    @api.depends("target_element_ui")
    def _compute_resolved_element(self):
        errors = []
        for rule in self:
            rule_errors = []
            rule.resolved_element = rule._process_element_ui(rule_errors)
            if rule_errors:
                error_msg = _("Error while processing rule %s", rule.display_name)
                rule_errors.insert(0, error_msg)
                errors.append("\n".join(rule_errors))

        if errors:
            raise UserError("\n\n".join(errors))

    @api.depends("view_id")
    def _compute_view_type(self):
        for rule in self:
            if rule.view_id:
                rule.view_type = rule.view_id.type
            elif not rule.view_type:
                rule.view_type = False

    @api.constrains("rule_invisible", "rule_readonly", "rule_required")
    def _check_at_least_one_rule(self):
        for rec in self:
            if not any((rec.rule_invisible, rec.rule_readonly, rec.rule_required)):
                raise ValidationError(
                    _(
                        "At least one access rule (Invisible, Readonly, or Required) "
                        "must be set."
                    )
                )

    @api.onchange("model_id")
    def _onchange_model_id(self):
        if self.model_id:
            if self.view_id and self.view_id.model != self.model_name:
                self.view_id = False
        else:
            self.view_id = False

    def _process_element_ui(self, line_errors):
        """Processes target_element_ui and replaces XML IDs with DB IDs
        for action buttons."""
        self.ensure_one()
        element_str = element_ui = self.target_element_ui
        if not element_str:
            return element_str

        if element_ui.startswith("xpath"):
            to_update = False
            if "button" in element_ui:
                parts = element_ui.split("button[")
                for i, part in enumerate(parts[1:], start=1):
                    if "]" not in part:
                        continue
                    attribs, remaining = part.split("]", 1)
                    pos = attribs.find("@name=")
                    if pos < 0:
                        break
                    name_start = pos + 7
                    quote_char = attribs[pos + 6]
                    pos = attribs[name_start:].find(quote_char)
                    if pos < 0:
                        break
                    name_stop = name_start + pos
                    name = attribs[name_start:name_stop]
                    name2 = self._parse_button_identifier(name, line_errors)
                    if name2 != name:
                        to_update = True
                        name_attrib = f"@name={quote_char}{name2}{quote_char}"
                        attribs = attribs[: pos + 6] + name_attrib + attribs[name_stop:]
                        parts[i] = "]".join([attribs, remaining])
                if to_update:
                    element_str = "button[".join(parts)
        elif element_ui.startswith("button "):
            parts = element_ui.split("name=")
            if len(parts) != 2:
                return element_str
            quote_char = parts[1][0]
            name = parts[1].strip(quote_char)
            name2 = self._parse_button_identifier(name, line_errors)
            if name2 != name:
                element_str = f"button name={quote_char}{name2}{quote_char}"
        return element_str

    def _parse_button_identifier(self, name, line_errors):
        """Resolves external XML IDs or validates standard names."""
        self.ensure_one()
        if name.startswith("%(") and name.endswith(")d"):
            xml_id = name[2:-2]
            try:
                record = self.env.ref(xml_id, raise_if_not_found=False)
                if not record:
                    raise ValueError()
                res_model, res_id = record._name, record.id
            except Exception:
                res_model, res_id = False, False

            if res_model not in [
                "ir.actions.act_window",
                "ir.actions.server",
                "ir.actions.report",
            ]:
                line_errors.append(
                    _(
                        "Incorrect value '%s' for button name in field 'Element'.",
                        self.target_element_ui,
                    )
                )
            else:
                name = str(res_id)
        else:
            self._validate_button_syntax(name, line_errors)
        return name

    def _validate_button_syntax(self, name, line_errors):
        """Ensures database integer IDs are not hardcoded directly
        without an External ID wrapper."""
        self.ensure_one()
        try:
            name = int(safe_eval(name))
        except Exception:
            _logger.debug("Unable to evaluate button name %s", name)

        if isinstance(name, int):
            err = _(
                "Syntax Error in field Element '%(element)s'\n"
                "Use the External Identifier for action buttons.\n"
                'e.g. name="%%(sale.act_res_partner_2_sale_order)d"',
                element=self.target_element_ui,
            )
            line_errors.append(err)
