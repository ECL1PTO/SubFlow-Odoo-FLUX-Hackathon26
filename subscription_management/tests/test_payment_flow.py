from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import SubscriptionCase


@tagged('post_install', '-at_install')
class TestPaymentFlow(SubscriptionCase):

    def _invoice(self):
        sub = self._make_subscription(qty=2, price=500.0)
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_start()
        return sub.generate_invoice()

    def test_payment_requires_a_payment_method(self):
        invoice = self._invoice()
        with self.assertRaises(UserError):
            invoice.action_register_subscription_payment()

    def test_recording_payment_marks_invoice_paid(self):
        invoice = self._invoice()
        invoice.payment_method = 'bank'
        invoice.action_register_subscription_payment()
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.payment_state, 'paid')
        self.assertEqual(invoice.amount_residual, 0.0)

    def test_paying_twice_is_rejected(self):
        invoice = self._invoice()
        invoice.payment_method = 'cash'
        invoice.action_register_subscription_payment()
        with self.assertRaises(UserError):
            invoice.action_register_subscription_payment()

    def test_dashboard_stats_reflect_payment(self):
        stats_before = self.Sub.get_billing_dashboard_stats()
        invoice = self._invoice()
        invoice.payment_method = 'bank'
        invoice.action_register_subscription_payment()
        stats_after = self.Sub.get_billing_dashboard_stats()
        self.assertAlmostEqual(
            stats_after['total_revenue'] - stats_before['total_revenue'],
            invoice.amount_total, places=2,
        )

    def test_unpaid_past_due_invoice_counts_as_overdue(self):
        before = self.Sub.get_billing_dashboard_stats()['overdue_count']
        invoice = self._invoice()
        invoice.action_post()
        invoice.invoice_date_due = '2026-01-01'
        after = self.Sub.get_billing_dashboard_stats()['overdue_count']
        self.assertEqual(after, before + 1)
