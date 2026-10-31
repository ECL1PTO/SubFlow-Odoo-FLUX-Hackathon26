from odoo import api, fields, models


class SubscriptionPlan(models.Model):
    _name = 'subscription.plan'
    _description = 'Subscription Billing Plan'
    _order = 'name'

    name = fields.Char(string='Plan Name', required=True, index=True)
    billing_period = fields.Selection(
        [
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        string='Billing Period',
        required=True,
        default='monthly',
    )
    billing_interval = fields.Integer(string='Billing Interval', default=1)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    price = fields.Monetary(string='Price', currency_field='currency_id')

    min_quantity = fields.Float(string='Minimum Quantity', default=1.0)
    quotation_validity_days = fields.Integer(
        string='Quotation Validity (Days)',
        default=30,
        help='How long a quotation for this plan stays valid. 0 means it never expires.',
    )
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')

    # Per-plan policy flags that gate the subscription lifecycle actions.
    auto_close = fields.Boolean(string='Auto-Close on Expiry', default=True)
    allow_close_early = fields.Boolean(string='Allow Early Closure', default=False)
    allow_pause = fields.Boolean(string='Allow Pause', default=True)
    allow_renew = fields.Boolean(string='Allow Renewal', default=True)
    active = fields.Boolean(string='Active', default=True)