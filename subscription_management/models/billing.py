from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PERIOD_DELTA = {
    'daily': lambda n: relativedelta(days=n),
    'weekly': lambda n: relativedelta(weeks=n),
    'monthly': lambda n: relativedelta(months=n),
    'yearly': lambda n: relativedelta(years=n),
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    subscription_id = fields.Many2one(
        'subscription.subscription', string='Subscription',
        index=True, ondelete='set null', copy=False,
    )
    payment_method = fields.Selection(
        [
            ('bank', 'Bank Transfer'),
            ('credit_card', 'Credit Card'),
            ('cash', 'Cash'),
            ('other', 'Other'),
        ],
        string='Payment Method', copy=False,
    )
    payment_date = fields.Date(copy=False)
    payment_note = fields.Text(copy=False)

    def action_register_subscription_payment(self):
        for move in self:
            if move.payment_state == 'paid':
                raise UserError(_('Invoice %s is already paid.') % move.name)
            if not move.payment_method:
                raise UserError(_('Choose a payment method before recording a payment on %s.') % move.name)
            if move.state == 'draft':
                move.action_post()
            payment_date = move.payment_date or fields.Date.context_today(move)
            amount = move.amount_residual or move.amount_total
            wizard = self.env['account.payment.register'].with_context(
                active_model='account.move', active_ids=move.ids,
            ).create({
                'payment_date': payment_date,
                'amount': amount,
                'communication': move.payment_note or move.name,
            })
            wizard.action_create_payments()
            move.message_post(
                body=_('Payment of %s recorded via %s on %s.') % (
                    amount, move.payment_method, payment_date,
                )
            )
        return True


class SubscriptionBilling(models.Model):
    _inherit = 'subscription.subscription'

    last_invoiced_date = fields.Date(readonly=True, copy=False)
    next_invoice_date = fields.Date(index=True, copy=False, tracking=True)
    invoice_ids = fields.One2many('account.move', 'subscription_id', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for subscription in self:
            subscription.invoice_count = len(subscription.invoice_ids)

    def _period_delta(self):
        self.ensure_one()
        plan = self.plan_id
        interval = max(plan.billing_interval or 1, 1)
        return PERIOD_DELTA[plan.billing_period](interval)

    def action_start(self):
        res = super().action_start()
        for subscription in self:
            if not subscription.next_invoice_date:
                subscription.next_invoice_date = subscription.start_date
        return res

    def _line_discount_percent(self, line, discounts):
        """Percentage discounts that apply to this line, capped at 100."""
        percent = sum(
            rule.discount_value for rule in discounts
            if rule.discount_type == 'percentage'
            and (rule.apply_on == 'subscription' or line.product_id in rule.product_ids)
        )
        return min(percent, 100.0)

    def _prepare_invoice_values(self, discounts):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Cannot invoice %s because it has no lines.') % self.name)

        invoice_lines = [
            (0, 0, {
                'product_id': line.product_id.id,
                'name': line.name or line.product_id.display_name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'discount': self._line_discount_percent(line, discounts),
                'tax_ids': [(6, 0, line.tax_ids.ids)],
            })
            for line in self.line_ids
        ]

        for rule in discounts.filtered(lambda r: r.discount_type == 'fixed'):
            amount = rule._calculate_discount_amount(self)
            if amount > 0:
                invoice_lines.append((0, 0, {
                    'name': _('Discount: %s') % rule.name,
                    'quantity': 1.0,
                    'price_unit': -amount,
                }))

        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'invoice_date': self.next_invoice_date or fields.Date.context_today(self),
            'invoice_payment_term_id': self.payment_term_id.id or False,
            'subscription_id': self.id,
            'invoice_line_ids': invoice_lines,
        }

    def generate_invoice(self):
        invoices = self.env['account.move']
        for subscription in self:
            discounts = self.env['discount.rule']._get_applicable_discounts(subscription)
            invoice = self.env['account.move'].create(
                subscription._prepare_invoice_values(discounts)
            )
            for rule in discounts:
                rule.current_usage += 1
            subscription.last_invoiced_date = invoice.invoice_date
            subscription.next_invoice_date = invoice.invoice_date + subscription._period_delta()
            subscription.message_post(
                body=_('Invoice %s generated for this subscription.') % invoice.name
            )
            invoices |= invoice
        return invoices

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_move_type': 'out_invoice', 'default_subscription_id': self.id},
        }

    @api.model
    def _cron_generate_subscription_invoices(self):
        today = fields.Date.context_today(self)
        due = self.search([
            ('state', '=', 'active'),
            ('next_invoice_date', '!=', False),
            ('next_invoice_date', '<=', today),
        ])
        for subscription in due:
            if subscription.expiry_date and subscription.expiry_date < today:
                if subscription.plan_id.auto_close:
                    subscription.action_close()
                continue
            try:
                subscription.generate_invoice()
            except UserError:
                continue
        return True

class SubscriptionDashboardMetrics(models.Model):
    _inherit = 'subscription.subscription'

    @api.model
    def get_billing_dashboard_stats(self):
        """Uses read_group to compute total revenue, outstanding amount, and overdue count cleanly."""
        Move = self.env['account.move']
        today = fields.Date.today()

        # 1. Total Revenue (Paid Invoices)
        paid_data = Move.read_group(
            domain=[('move_type', '=', 'out_invoice'), ('payment_state', '=', 'paid')],
            fields=['amount_total:sum'],
            groupby=[]
        )
        total_revenue = paid_data[0]['amount_total'] if paid_data and paid_data[0]['amount_total'] else 0.0

        # 2. Outstanding Amount (Unpaid / Partial Invoices)
        outstanding_data = Move.read_group(
            domain=[('move_type', '=', 'out_invoice'), ('payment_state', '!=', 'paid'), ('state', '=', 'posted')],
            fields=['amount_total:sum'],
            groupby=[]
        )
        total_outstanding = outstanding_data[0]['amount_total'] if outstanding_data and outstanding_data[0]['amount_total'] else 0.0

        # 3. Overdue Invoices Count
        overdue_count = Move.search_count([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', '!=', 'paid'),
            ('invoice_date_due', '<', today)
        ])

        return {
            'total_revenue': total_revenue,
            'total_outstanding': total_outstanding,
            'overdue_count': overdue_count,
        }
