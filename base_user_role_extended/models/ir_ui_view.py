import re

from lxml import etree

from odoo import api, models


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        """
        Override get_view to inject role-based view access rules.
        """
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        user = self.env.user
        if not user or self.env.context.get("install_mode") or user.bypass_role_policy:
            return result
        user_roles = user._get_enabled_roles().mapped("role_id")
        if not user_roles:
            return result
        actual_view_id = result.get("id")
        model_name = result.get("model")
        actual_view_type = view_type or _arch_root_tag(result.get("arch", ""))
        if not model_name or not actual_view_type:
            return result
        rule_domain = [
            ("role_id", "in", user_roles.ids),
            ("model_name", "=", model_name),
            ("view_type", "=", actual_view_type),
            "|",
            ("view_id", "=", actual_view_id),
            ("view_id", "=", False),
        ]
        active_rules = (
            self.env["view.access.rule"]
            .sudo()
            .search(rule_domain, order="sequence asc")
        )
        if not active_rules:
            return result
        node = etree.fromstring(result["arch"])
        for rule in active_rules:
            target_element = (
                rule.resolved_element or rule.target_element_ui or ""
            ).strip()
            if not target_element:
                continue
            xpath_expr = self._resolve_target_to_xpath(target_element)
            if not xpath_expr:
                continue
            try:
                matched_nodes = node.xpath(xpath_expr)
            except Exception:
                matched_nodes = []

            for matched_node in matched_nodes:
                self._apply_modifier_attributes(matched_node, rule, node)
        result = dict(result)
        result["arch"] = etree.tostring(node, encoding="unicode").replace("\t", "")
        return result

    def _resolve_target_to_xpath(self, target_element):
        """
        Converts a target_element_ui string into a valid XPath expression.
        Supported formats:
          - xpath expr="//page[@id='tab']"       → //page[@id='tab']
          - button name="action_confirm"         → //button[@name='action_confirm']
          - field name="company_id"              → //field[@name='company_id']
          - /form/sheet/group                    → /form/sheet/group  (raw path)
          - state                                → //field[@name='state']|
          //button[@name='state']
        """
        # Pattern 1: xpath expr="..."
        xpath_match = re.match(r'^xpath\s+expr=["\'](.*?)["\']$', target_element)
        if xpath_match:
            return xpath_match.group(1)
        # Pattern 2: tag name="..."  e.g.  button name="action_confirm"
        tag_name_match = re.match(r'^(\w+)\s+name=["\'](.*?)["\']$', target_element)
        if tag_name_match:
            tag, name = tag_name_match.groups()
            return f"//{tag}[@name='{name}']"

        # Pattern 3: raw XPath starting with / or xpath keyword
        if target_element.startswith("/") or target_element.startswith("xpath"):
            return target_element

        # Pattern 4: bare field/button name fallback
        return (
            f"//field[@name='{target_element}']"
            f" | //button[@name='{target_element}']"
        )

    def _apply_modifier_attributes(self, node, rule, arch_root):
        """
        Sets invisible / readonly / required attributes on the target XML node.

        - Completely overwrites any existing condition with the rule value.
        - Normalises "1"→"True", "0"→"False".
        - Automatically switches to column_invisible for fields inside list/tree views.
        - Mirrors invisible onto any <label for="..."> siblings of a field node.
        """
        modifiers = {
            "invisible": rule.rule_invisible,
            "readonly": rule.rule_readonly,
            "required": rule.rule_required,
        }

        for attr, raw_value in modifiers.items():
            if not raw_value:
                continue
            value_str = str(raw_value).strip()
            if value_str == "1":
                value_str = "True"
            elif value_str == "0":
                value_str = "False"
            target_attr = attr
            if attr == "invisible" and node.tag == "field":
                parent = node.getparent()
                while parent is not None:
                    if parent.tag in ("list", "tree"):
                        target_attr = "column_invisible"
                        break
                    parent = parent.getparent()
            node.set(target_attr, value_str)
            if node.tag == "field" and target_attr in ("invisible", "column_invisible"):
                field_name = node.get("name")
                if field_name and arch_root is not None:
                    for label_node in arch_root.xpath(f"//label[@for='{field_name}']"):
                        label_node.set(target_attr, value_str)


def _arch_root_tag(arch_str):
    """Return the root tag of an arch XML string (e.g. 'form', 'list', 'kanban')."""
    if not arch_str:
        return None
    try:
        root = etree.fromstring(arch_str)
        return root.tag
    except Exception:
        return None


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
