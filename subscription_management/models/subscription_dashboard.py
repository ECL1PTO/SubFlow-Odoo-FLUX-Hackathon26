
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
        Move = self.env['account.move']

        active_count = Subscription.search_count([
            ('state', '=', 'active')
        ])

        invoice_domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted')
        ]

        paid_data = Move._read_group(
            invoice_domain + [
                ('payment_state', '=', 'paid')
            ],
            [],
            ['amount_total_signed:sum']
        )

        unpaid_data = Move._read_group(
            invoice_domain + [
                ('amount_residual', '>', 0)
            ],
            [],
            ['amount_residual_signed:sum']
        )

        overdue_count = Move.search_count(
            invoice_domain + [
                ('amount_residual', '>', 0),
                ('invoice_date_due', '<', fields.Date.today())
            ]
        )

        revenue = paid_data[0][0] or 0.0 if paid_data else 0.0
        outstanding = unpaid_data[0][0] or 0.0 if unpaid_data else 0.0

        for dashboard in self:
            dashboard.active_subscription_count = active_count
            dashboard.total_revenue = revenue
            dashboard.outstanding_amount = outstanding
            dashboard.overdue_count = overdue_count
