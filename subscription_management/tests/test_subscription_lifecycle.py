from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import SubscriptionCase


@tagged('post_install', '-at_install')
class TestSubscriptionLifecycle(SubscriptionCase):

    def test_sequence_is_assigned_on_create(self):
        sub = self._make_subscription()
        self.assertTrue(sub.name)
        self.assertNotEqual(sub.name, 'New')
        self.assertTrue(sub.name.startswith('SUB/'))

    def test_amounts_computed_from_lines_and_taxes(self):
        sub = self._make_subscription(qty=2, price=500.0, taxes=False)
        self.assertEqual(sub.amount_untaxed, 1000.0)
        self.assertEqual(sub.amount_tax, 0.0)
        self.assertEqual(sub.amount_total, 1000.0)

        sub.line_ids.tax_ids = [(6, 0, self.tax.ids)]
        self.assertEqual(sub.amount_untaxed, 1000.0)
        self.assertGreaterEqual(sub.amount_total, sub.amount_untaxed)

    def test_full_happy_path_transitions(self):
        sub = self._make_subscription()
        self.assertEqual(sub.state, 'draft')
        sub.action_send_quotation(); self.assertEqual(sub.state, 'quotation')
        sub.action_confirm();        self.assertEqual(sub.state, 'confirmed')
        sub.action_start();          self.assertEqual(sub.state, 'active')
        sub.action_pause();          self.assertEqual(sub.state, 'paused')
        sub.action_resume();         self.assertEqual(sub.state, 'active')
        sub.action_close();          self.assertEqual(sub.state, 'closed')

    def test_cannot_confirm_from_draft(self):
        sub = self._make_subscription()
        with self.assertRaises(UserError):
            sub.action_confirm()

    def test_cannot_send_quotation_without_lines(self):
        sub = self.Sub.create({
            'partner_id': self.customer.id,
            'plan_id': self.plan.id,
            'start_date': '2026-10-01',
        })
        with self.assertRaises(UserError):
            sub.action_send_quotation()

    def test_pause_blocked_when_plan_forbids(self):
        self.plan.allow_pause = False
        sub = self._make_subscription()
        sub.action_send_quotation(); sub.action_confirm(); sub.action_start()
        with self.assertRaises(UserError):
            sub.action_pause()

    def test_early_close_blocked_when_plan_forbids(self):
        self.plan.allow_close_early = False
        sub = self._make_subscription()
        sub.action_send_quotation(); sub.action_confirm(); sub.action_start()
        sub.expiry_date = '2099-12-31'
        with self.assertRaises(UserError):
            sub.action_close()

    def test_expiry_before_start_rejected(self):
        with self.assertRaises(ValidationError):
            self.Sub.create({
                'partner_id': self.customer.id,
                'plan_id': self.plan.id,
                'start_date': '2026-10-01',
                'expiry_date': '2026-09-01',
            })
