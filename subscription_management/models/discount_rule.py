from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DiscountRule(models.Model):
    _name = 'discount.rule'
    _description = 'Automated Subscription Discount Rule'
    _order = 'sequence, id desc'

    name = fields.Char(string='Discount Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    discount_type = fields.Selection(
        [
            ('fixed', 'Fixed Amount'),
            ('percentage', 'Percentage (%)'),
        ],
        string='Discount Type',
        required=True,
        default='percentage',
    )
    discount_value = fields.Float(string='Discount Value', required=True)

    apply_on = fields.Selection(
        [
            ('subscription', 'Whole Subscription'),
            ('product', 'Specific Products'),
        ],
        string='Applies To',
        required=True,
        default='subscription',
    )
    product_ids = fields.Many2many('product.product', string='Eligible Products')

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
    min_purchase_amount = fields.Monetary(
        string='Minimum Purchase Amount',
        currency_field='currency_id',
        default=0.0,
    )
    min_quantity = fields.Float(string='Minimum Quantity', default=0.0)

    date_start = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today,
    )
    date_end = fields.Date(string='End Date', required=True)

    usage_limit = fields.Integer(string='Usage Cap (0 = Unlimited)', default=0)
    current_usage = fields.Integer(string='Times Used', default=0, readonly=True)

    @api.constrains('discount_type', 'discount_value')
    def _check_discount_value(self):
        for rule in self:
            if rule.discount_value <= 0:
                raise ValidationError(_('Discount value must be greater than zero.'))
            if rule.discount_type == 'percentage' and rule.discount_value > 100:
                raise ValidationError(_('Percentage discount cannot exceed 100%.'))

    @api.model
    def _get_applicable_discounts(self, subscription):
        today = fields.Date.context_today(self)
        rules = self.search([
            ('active', '=', True),
            ('date_start', '<=', today),
            ('date_end', '>=', today),
        ])
        
        valid_rules = self.env['discount.rule']
        total_qty = sum(subscription.line_ids.mapped('quantity')) if subscription.line_ids else 0.0

        for rule in rules:
            if rule.usage_limit > 0 and rule.current_usage >= rule.usage_limit:
                continue
            if subscription.amount_untaxed < rule.min_purchase_amount:
                continue
            if total_qty < rule.min_quantity:
                continue
            if rule.apply_on == 'product' and subscription.line_ids:
                sub_products = subscription.line_ids.mapped('product_id')
                if not (sub_products & rule.product_ids):
                    continue
            valid_rules |= rule
            
        return valid_rules

    def _calculate_discount_amount(self, subscription):
        self.ensure_one()
        if self.apply_on == 'product' and subscription.line_ids:
            matching_lines = subscription.line_ids.filtered(lambda l: l.product_id in self.product_ids)
            base_amount = sum(matching_lines.mapped('price_subtotal'))
        else:
            base_amount = subscription.amount_untaxed

        if self.discount_type == 'fixed':
            return min(self.discount_value, base_amount)
        return base_amount * (self.discount_value / 100.0)