
from odoo import api, fields, models


class SubscriptionDashboard(models.TransientModel):
    _name = 'subscription.dashboard'
    _description = 'Subscription Dashboard'

    active_subscription_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_dashboard'
    )

    total_revenue = fields.Monetary(
        string='Total Revenue',
        currency_field='currency_id',
        compute='_compute_dashboard'
    )

    outstanding_amount = fields.Monetary(
        string='Outstanding Amount',
        currency_field='currency_id',
        compute='_compute_dashboard'
    )

    overdue_count = fields.Integer(
        string='Overdue Invoices',
        compute='_compute_dashboard'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends()
    def _compute_dashboard(self):
        Subscription = self.env['subscription.subscription']
        active_count = Subscription.search_count([('state', '=', 'active')])
        stats = Subscription.get_billing_dashboard_stats()

        for dashboard in self:
            dashboard.active_subscription_count = active_count
            dashboard.total_revenue = stats['total_revenue']
            dashboard.outstanding_amount = stats['total_outstanding']
            dashboard.overdue_count = stats['overdue_count']
