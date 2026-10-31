from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import SubscriptionCase


@tagged('post_install', '-at_install')
class TestQuotationValidity(SubscriptionCase):

    def test_validity_date_set_from_plan_when_quotation_sent(self):
        self.plan.quotation_validity_days = 15
        sub = self._make_subscription()
        self.assertFalse(sub.validity_date)
        sub.action_send_quotation()
        expected = fields.Date.context_today(sub) + relativedelta(days=15)
        self.assertEqual(sub.validity_date, expected)

    def test_zero_validity_days_means_no_expiry(self):
        self.plan.quotation_validity_days = 0
        sub = self._make_subscription()
        sub.action_send_quotation()
        self.assertFalse(sub.validity_date)
        self.assertFalse(sub.is_quotation_expired)
        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')

    def test_expired_quotation_cannot_be_confirmed(self):
        sub = self._make_subscription()
        sub.action_send_quotation()
        sub.validity_date = fields.Date.context_today(sub) - relativedelta(days=1)
        self.assertTrue(sub.is_quotation_expired)
        with self.assertRaises(UserError):
            sub.action_confirm()
        self.assertEqual(sub.state, 'quotation')

    def test_quotation_valid_today_can_still_be_confirmed(self):
        sub = self._make_subscription()
        sub.action_send_quotation()
        sub.validity_date = fields.Date.context_today(sub)
        self.assertFalse(sub.is_quotation_expired)
        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')

    def test_reset_to_draft_clears_validity_and_billing_schedule(self):
        sub = self._make_subscription()
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_start()
        self.assertTrue(sub.next_invoice_date)
        sub.action_close()
        sub.action_reset_to_draft()
        self.assertFalse(sub.validity_date)
        self.assertFalse(sub.next_invoice_date)

    def test_restarted_subscription_bills_from_its_start_date(self):
        sub = self._make_subscription()
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_start()
        sub.generate_invoice()
        sub.action_close()
        sub.action_reset_to_draft()
        sub.action_send_quotation()
        sub.action_confirm()
        sub.action_start()
        self.assertEqual(sub.next_invoice_date, sub.start_date)
