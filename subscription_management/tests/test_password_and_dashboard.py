from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import SubscriptionCase


@tagged('post_install', '-at_install')
class TestPasswordPolicy(SubscriptionCase):

    def _make_user(self, password):
        return self.env['res.users'].create({
            'name': 'Policy User',
            'login': 'policy.user.%s@example.com' % abs(hash(password)),
            'password': password,
        })

    def test_short_password_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._make_user('Ab1!xyz')

    def test_password_without_uppercase_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._make_user('lowercase1!')

    def test_password_without_lowercase_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._make_user('UPPERCASE1!')

    def test_password_without_special_character_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._make_user('NoSpecial123')

    def test_compliant_password_is_accepted(self):
        user = self._make_user('Brightloop#2026')
        self.assertTrue(user.id)


@tagged('post_install', '-at_install')
class TestSubscriptionDashboard(SubscriptionCase):

    def _activate(self, sub):
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_start()
        return sub

    def test_dashboard_counts_active_subscriptions(self):
        dashboard = self.env['subscription.dashboard'].create({})
        before = dashboard.active_subscription_count
        self._activate(self._make_subscription())
        dashboard.invalidate_recordset()
        self.assertEqual(dashboard.active_subscription_count, before + 1)

    def test_dashboard_outstanding_includes_posted_unpaid_invoice(self):
        dashboard = self.env['subscription.dashboard'].create({})
        before = dashboard.outstanding_amount
        invoice = self._activate(self._make_subscription()).generate_invoice()
        invoice.action_post()
        dashboard.invalidate_recordset()
        self.assertAlmostEqual(
            dashboard.outstanding_amount - before, invoice.amount_total, places=2,
        )

    def test_dashboard_revenue_counts_paid_invoice_only(self):
        dashboard = self.env['subscription.dashboard'].create({})
        before = dashboard.total_revenue
        invoice = self._activate(self._make_subscription()).generate_invoice()
        invoice.action_post()
        dashboard.invalidate_recordset()
        self.assertAlmostEqual(dashboard.total_revenue, before, places=2)

        invoice.payment_method = 'bank'
        invoice.action_register_subscription_payment()
        dashboard.invalidate_recordset()
        self.assertAlmostEqual(
            dashboard.total_revenue - before, invoice.amount_total, places=2,
        )

    def test_dashboard_overdue_count_tracks_past_due_invoices(self):
        dashboard = self.env['subscription.dashboard'].create({})
        before = dashboard.overdue_count
        invoice = self._activate(self._make_subscription()).generate_invoice()
        invoice.action_post()
        invoice.invoice_date_due = '2026-01-01'
        dashboard.invalidate_recordset()
        self.assertEqual(dashboard.overdue_count, before + 1)
