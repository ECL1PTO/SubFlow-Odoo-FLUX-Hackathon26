from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SubscriptionSubscription(models.Model):
    _name = 'subscription.subscription'
    _description = 'Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New')
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, index=True, tracking=True
    )
    plan_id = fields.Many2one(
        'subscription.plan', string='Plan', required=True, index=True, tracking=True
    )
    start_date = fields.Date(required=True, index=True, default=fields.Date.context_today, tracking=True)
    expiry_date = fields.Date(index=True, tracking=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    line_ids = fields.One2many('subscription.line', 'subscription_id', string='Lines', copy=True)

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('quotation', 'Quotation'),
            ('confirmed', 'Confirmed'),
            ('active', 'Active'),
            ('paused', 'Paused'),
            ('closed', 'Closed'),
        ],
        default='draft', required=True, index=True, tracking=True, copy=False,
    )

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)

    amount_untaxed = fields.Monetary(compute='_compute_amounts', store=True)
    amount_tax = fields.Monetary(compute='_compute_amounts', store=True)
    amount_total = fields.Monetary(compute='_compute_amounts', store=True)

    @api.depends('line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.price_total')
    def _compute_amounts(self):
        for subscription in self:
            lines = subscription.line_ids
            subscription.amount_untaxed = sum(lines.mapped('price_subtotal'))
            subscription.amount_tax = sum(lines.mapped('price_tax'))
            subscription.amount_total = sum(lines.mapped('price_total'))

    @api.constrains('start_date', 'expiry_date')
    def _check_dates(self):
        for subscription in self:
            if subscription.expiry_date and subscription.expiry_date < subscription.start_date:
                raise ValidationError(_('The expiry date cannot be earlier than the start date.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('subscription.subscription') or _('New')
        return super().create(vals_list)

    def _require_state(self, allowed, action_label):
        invalid = self.filtered(lambda s: s.state not in allowed)
        if invalid:
            raise UserError(_(
                'Cannot %(action)s subscription %(name)s because it is in the %(state)s state.',
                action=action_label, name=invalid[0].name, state=invalid[0].state,
            ))

    def action_send_quotation(self):
        self._require_state(('draft',), _('send'))
        for subscription in self:
            if not subscription.line_ids:
                raise UserError(_('Add at least one line before sending %s as a quotation.') % subscription.name)
        self.write({'state': 'quotation'})

    def action_confirm(self):
        self._require_state(('quotation',), _('confirm'))
        self.write({'state': 'confirmed'})

    def action_start(self):
        self._require_state(('confirmed',), _('start'))
        self.write({'state': 'active'})

    def action_pause(self):
        self._require_state(('active',), _('pause'))
        blocked = self.filtered(lambda s: not s.plan_id.allow_pause)
        if blocked:
            raise UserError(_('The plan %s does not allow pausing.') % blocked[0].plan_id.display_name)
        self.write({'state': 'paused'})

    def action_resume(self):
        self._require_state(('paused',), _('resume'))
        self.write({'state': 'active'})

    def action_close(self):
        self._require_state(('confirmed', 'active', 'paused'), _('close'))
        today = fields.Date.context_today(self)
        for subscription in self:
            expired = subscription.expiry_date and subscription.expiry_date <= today
            if not expired and not subscription.plan_id.allow_close_early:
                raise UserError(_(
                    'The plan %s does not allow closing a subscription before its expiry date.'
                ) % subscription.plan_id.display_name)
        self.write({'state': 'closed'})

    def action_reset_to_draft(self):
        self._require_state(('quotation', 'closed'), _('reset'))
        self.write({'state': 'draft'})


class SubscriptionLine(models.Model):
    _name = 'subscription.line'
    _description = 'Subscription Line'
    _order = 'subscription_id, sequence, id'

    subscription_id = fields.Many2one(
        'subscription.subscription', required=True, ondelete='cascade', index=True
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(string='Description')
    quantity = fields.Float(default=1.0, required=True)
    price_unit = fields.Float(string='Unit Price', default=0.0)
    tax_ids = fields.Many2many('account.tax', string='Taxes')

    currency_id = fields.Many2one(related='subscription_id.currency_id', store=True)
    company_id = fields.Many2one(related='subscription_id.company_id', store=True)

    price_subtotal = fields.Monetary(compute='_compute_prices', store=True)
    price_tax = fields.Monetary(compute='_compute_prices', store=True)
    price_total = fields.Monetary(compute='_compute_prices', store=True)

    @api.depends('quantity', 'price_unit', 'tax_ids', 'product_id', 'currency_id')
    def _compute_prices(self):
        for line in self:
            taxes = line.tax_ids.compute_all(
                line.price_unit,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=line.subscription_id.partner_id,
            )
            line.price_subtotal = taxes['total_excluded']
            line.price_total = taxes['total_included']
            line.price_tax = taxes['total_included'] - taxes['total_excluded']

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.get_product_multiline_description_sale()
                line.price_unit = line.product_id.lst_price
                line.tax_ids = line.product_id.taxes_id

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
