from odoo import models, fields, api
from datetime import date

class SubscriptionBilling(models.Model):
    _inherit = 'subscription.subscription'

    last_invoiced_date = fields.Date(
        string="Last Invoiced Date", 
        help="Tracks the date an invoice was last generated to prevent duplicate billing."
    )
    invoice_ids = fields.One2many(
        'account.move', 
        'computed_subscription_id', 
        string="Invoices"
    )

    @api.model
    def _cron_generate_subscription_invoices(self):
        """Automated daily cron to generate invoices for active subscriptions without duplicate billing."""
        today = date.today()
        
        # Search for active subscriptions that haven't been invoiced yet today
        active_subs = self.search([
            ('state', '=', 'active'),
            '|', ('last_invoiced_date', '<', today), ('last_invoiced_date', '=', False)
        ])

        for sub in active_subs:
            # Build invoice values
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': sub.customer_id.id if hasattr(sub, 'customer_id') else False,
                'invoice_date': today,
                'invoice_line_ids': [(0, 0, {
                    'name': f"Subscription Billing - Plan: {sub.plan_id.name if hasattr(sub, 'plan_id') else 'Standard'} ",
                    'quantity': 1.0,
                    'price_unit': sub.plan_id.price if hasattr(sub, 'plan_id') else 0.0,
                })],
            }
            
            # Create the account.move invoice record
            invoice = self.env['account.move'].create(invoice_vals)
            
            # Update the last invoiced date to completely block duplicate billing runs
            sub.write({'last_invoiced_date': today})
