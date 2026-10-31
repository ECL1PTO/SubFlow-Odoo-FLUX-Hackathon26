from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import SubscriptionCase


@tagged('post_install', '-at_install')
class TestAccessRights(SubscriptionCase):

    def _portal_user_for(self, partner):
        return self.env['res.users'].create({
            'name': 'Portal of %s' % partner.name,
            'login': 'portal_%s' % partner.id,
            'partner_id': partner.id,
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

    def test_portal_user_sees_only_own_subscription(self):
        own_sub = self._make_subscription()
        other = self.Partner.create({'name': 'Other Customer'})
        other_sub = self.Sub.create({
            'partner_id': other.id,
            'plan_id': self.plan.id,
            'start_date': '2026-10-01',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })

        portal_user = self._portal_user_for(self.customer)
        visible = self.Sub.with_user(portal_user).search([])
        self.assertIn(own_sub, visible)
        self.assertNotIn(other_sub, visible)

    def test_portal_user_cannot_create_subscription(self):
        portal_user = self._portal_user_for(self.customer)
        with self.assertRaises(AccessError):
            self.Sub.with_user(portal_user).create({
                'partner_id': self.customer.id,
                'plan_id': self.plan.id,
                'start_date': '2026-10-01',
            })

    def test_staff_cannot_delete_subscription(self):
        staff = self.env['res.users'].create({
            'name': 'Staff User', 'login': 'staff_user',
            'groups_id': [(6, 0, [self.env.ref(
                'subscription_management.group_subscription_staff').id])],
        })
        sub = self._make_subscription()
        with self.assertRaises(AccessError):
            sub.with_user(staff).unlink()
