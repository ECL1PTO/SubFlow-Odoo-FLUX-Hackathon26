from odoo.tests import tagged

from .common import SubscriptionCase


@tagged('post_install', '-at_install')
class TestBillingAndDiscounts(SubscriptionCase):

    def _activate(self, sub):
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_start()

    def test_invoice_carries_lines_quantities_and_taxes(self):
        sub = self._make_subscription(qty=3, price=200.0)
        self._activate(sub)
        invoice = sub.generate_invoice()
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.partner_id, self.customer)
        self.assertEqual(invoice.subscription_id, sub)
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        line = invoice.invoice_line_ids
        self.assertEqual(line.quantity, 3)
        self.assertEqual(line.price_unit, 200.0)
        self.assertEqual(line.tax_ids, self.tax)
        self.assertAlmostEqual(invoice.amount_untaxed, 600.0, places=2)

    def test_next_invoice_date_advances_by_billing_period(self):
        sub = self._make_subscription()
        self._activate(sub)
        before = sub.next_invoice_date
        sub.generate_invoice()
        self.assertEqual(sub.next_invoice_date.month - before.month, 1)

    def test_cron_never_double_bills(self):
        sub = self._make_subscription()
        self._activate(sub)
        sub.generate_invoice()
        count_after_first = sub.invoice_count
        self.Sub._cron_generate_subscription_invoices()
        self.Sub._cron_generate_subscription_invoices()
        self.assertEqual(sub.invoice_count, count_after_first)

    def test_expired_subscription_is_auto_closed_by_cron(self):
        self.plan.auto_close = True
        sub = self.Sub.create({
            'partner_id': self.customer.id,
            'plan_id': self.plan.id,
            'start_date': '2026-10-01',
            'expiry_date': '2026-10-05',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        self._activate(sub)
        sub.next_invoice_date = '2026-10-06'
        self.Sub.with_context(mail_notrack=True)._cron_generate_subscription_invoices()
        self.assertEqual(sub.state, 'closed')

    def test_percentage_discount_applied_to_invoice_line(self):
        discount = self.Discount.create({
            'name': 'Launch 10%',
            'discount_type': 'percentage',
            'discount_value': 10.0,
            'apply_on': 'subscription',
            'date_start': '2026-01-01',
            'date_end': '2099-12-31',
        })
        sub = self._make_subscription(qty=2, price=500.0)
        self._activate(sub)
        invoice = sub.generate_invoice()
        self.assertEqual(invoice.invoice_line_ids.discount, 10.0)
        self.assertAlmostEqual(invoice.amount_untaxed, 900.0, places=2)
        self.assertEqual(discount.current_usage, 1)

    def test_fixed_discount_added_as_negative_line(self):
        self.Discount.create({
            'name': 'Loyalty 100 off',
            'discount_type': 'fixed',
            'discount_value': 100.0,
            'apply_on': 'subscription',
            'date_start': '2026-01-01',
            'date_end': '2099-12-31',
        })
        sub = self._make_subscription(qty=2, price=500.0)
        self._activate(sub)
        invoice = sub.generate_invoice()
        self.assertEqual(len(invoice.invoice_line_ids), 2)
        self.assertAlmostEqual(invoice.amount_untaxed, 900.0, places=2)

    def test_expired_discount_is_not_applied(self):
        self.Discount.create({
            'name': 'Expired promo',
            'discount_type': 'percentage',
            'discount_value': 50.0,
            'apply_on': 'subscription',
            'date_start': '2020-01-01',
            'date_end': '2020-12-31',
        })
        sub = self._make_subscription(qty=2, price=500.0)
        self._activate(sub)
        invoice = sub.generate_invoice()
        self.assertEqual(invoice.invoice_line_ids.discount, 0.0)
        self.assertAlmostEqual(invoice.amount_untaxed, 1000.0, places=2)

    def test_discount_usage_cap_enforced(self):
        rule = self.Discount.create({
            'name': 'One-shot 20%',
            'discount_type': 'percentage',
            'discount_value': 20.0,
            'apply_on': 'subscription',
            'date_start': '2026-01-01',
            'date_end': '2099-12-31',
            'usage_limit': 1,
        })
        sub1 = self._make_subscription()
        self._activate(sub1); sub1.generate_invoice()
        sub2 = self._make_subscription()
        self._activate(sub2); invoice2 = sub2.generate_invoice()
        self.assertEqual(invoice2.invoice_line_ids.discount, 0.0)
        self.assertEqual(rule.current_usage, 1)
