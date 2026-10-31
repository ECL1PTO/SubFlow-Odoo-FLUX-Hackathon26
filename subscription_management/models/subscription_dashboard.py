from odoo import fields, models


class SubscriptionDashboard(models.TransientModel):
    _name = 'subscription.dashboard'
    _description = 'Subscription Dashboard'

    active_subscription_count = fields.Integer(string='Active Subscriptions', readonly=True)
    total_revenue = fields.Monetary(
        string='Total Revenue', currency_field='currency_id', readonly=True,
    )
    outstanding_amount = fields.Monetary(
        string='Outstanding Amount', currency_field='currency_id', readonly=True,
    )
    overdue_count = fields.Integer(string='Overdue Invoices', readonly=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )

    def default_get(self, fields_list):
        """Fill the figures when the dashboard is opened.

        The values are read rather than computed, because a computed field
        with no dependencies never refreshes on the empty record the form
        opens with.
        """
        values = super().default_get(fields_list)
        values.update(self._dashboard_values())
        return values

    def action_refresh(self):
        self.ensure_one()
        self.write(self._dashboard_values())
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'inline',
        }

    def _dashboard_values(self):
        Subscription = self.env['subscription.subscription']
        stats = Subscription.get_billing_dashboard_stats()
        return {
            'active_subscription_count': Subscription.search_count([('state', '=', 'active')]),
            'total_revenue': stats['total_revenue'],
            'outstanding_amount': stats['total_outstanding'],
            'overdue_count': stats['overdue_count'],
        }
