This module extends the `base_user_role` module to enforce strict
role-based access control.

It overrides the access rights evaluation to ensure that for model
access rights, Odoo ignores standard user group assignments and
considers only those groups associated with the user's active, enabled
roles.

This ensures a robust separation of concerns where role configurations
supersede implicit or overlapping group permissions.
