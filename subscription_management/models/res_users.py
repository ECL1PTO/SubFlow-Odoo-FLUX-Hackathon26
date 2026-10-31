import re
from odoo import _, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _set_password(self):
        for user in self:
            password = user.password

            if not password:
                continue

            if len(password) <= 8:
                raise ValidationError(
                    _('Password must be longer than 8 characters.')
                )

            if not re.search(r'[A-Z]', password):
                raise ValidationError(
                    _('Password must contain an uppercase letter.')
                )

            if not re.search(r'[a-z]', password):
                raise ValidationError(
                    _('Password must contain a lowercase letter.')
                )

            if not re.search(r'[^A-Za-z0-9]', password):
                raise ValidationError(
                    _('Password must contain a special character.')
                )

        return super()._set_password()