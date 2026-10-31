from odoo.tests.common import TransactionCase


class SubscriptionCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env['res.partner']
        cls.Plan = cls.env['subscription.plan']
        cls.Sub = cls.env['subscription.subscription']
        cls.Discount = cls.env['discount.rule']
        cls.Move = cls.env['account.move']

        cls.customer = cls.Partner.create({'name': 'Test Customer'})
        cls.product = (
            cls.env['product.product'].search([('type', '=', 'service')], limit=1)
            or cls.env['product.product'].search([], limit=1)
        )
        cls.tax = cls.env['account.tax'].search([('type_tax_use', '=', 'sale')], limit=1)
        cls.plan = cls.Plan.create({
            'name': 'Test Monthly Plan',
            'billing_period': 'monthly',
            'billing_interval': 1,
            'price': 500.0,
            'min_quantity': 1.0,
            'auto_close': True,
            'allow_pause': True,
            'allow_close_early': True,
            'allow_renew': True,
            'date_start': '2026-01-01',
        })

    def _make_subscription(self, qty=2, price=500.0, taxes=True):
        return self.Sub.create({
            'partner_id': self.customer.id,
            'plan_id': self.plan.id,
            'start_date': '2026-10-01',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': 'Test line',
                'quantity': qty,
                'price_unit': price,
                'tax_ids': [(6, 0, self.tax.ids if taxes else [])],
            })],
        })
