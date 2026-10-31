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

    def _open_dashboard(self):
        """Open the dashboard the way the web client does, through default_get."""
        Dashboard = self.env['subscription.dashboard']
        return Dashboard.create(Dashboard.default_get(list(Dashboard._fields)))

    def test_dashboard_counts_active_subscriptions(self):
        before = self._open_dashboard().active_subscription_count
        self._activate(self._make_subscription())
        self.assertEqual(self._open_dashboard().active_subscription_count, before + 1)

    def test_dashboard_figures_are_filled_when_opened(self):
        self._activate(self._make_subscription())
        dashboard = self._open_dashboard()
        self.assertTrue(dashboard.active_subscription_count)
        self.assertTrue(dashboard.currency_id)

    def test_dashboard_outstanding_includes_posted_unpaid_invoice(self):
        before = self._open_dashboard().outstanding_amount
        invoice = self._activate(self._make_subscription()).generate_invoice()
        invoice.action_post()
        self.assertAlmostEqual(
            self._open_dashboard().outstanding_amount - before, invoice.amount_total, places=2,
        )

    def test_dashboard_revenue_counts_paid_invoice_only(self):
        before = self._open_dashboard().total_revenue
        invoice = self._activate(self._make_subscription()).generate_invoice()
        invoice.action_post()
        self.assertAlmostEqual(self._open_dashboard().total_revenue, before, places=2)

        invoice.payment_method = 'bank'
        invoice.action_register_subscription_payment()
        self.assertAlmostEqual(
            self._open_dashboard().total_revenue - before, invoice.amount_total, places=2,
        )

    def test_dashboard_refresh_picks_up_new_activity(self):
        dashboard = self._open_dashboard()
        before = dashboard.active_subscription_count
        self._activate(self._make_subscription())
        dashboard.action_refresh()
        self.assertEqual(dashboard.active_subscription_count, before + 1)

    def test_dashboard_overdue_count_tracks_past_due_invoices(self):
        before = self._open_dashboard().overdue_count
        invoice = self._activate(self._make_subscription()).generate_invoice()
        invoice.action_post()
        invoice.invoice_date_due = '2026-01-01'
        self.assertEqual(self._open_dashboard().overdue_count, before + 1)
