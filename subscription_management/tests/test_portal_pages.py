from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestPortalPages(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = cls.env['res.users'].create({
            'name': 'Portal Customer',
            'login': 'portal.customer@example.com',
            'password': 'Brightloop#2026',
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
        })
        cls.other_partner = cls.env['res.partner'].create({'name': 'Rival Corp'})
        cls.plan = cls.env['subscription.plan'].create({
            'name': 'Portal Test Plan',
            'billing_period': 'monthly',
            'billing_interval': 1,
            'price': 300.0,
        })
        cls.product = cls.env['product.product'].search([], limit=1)
        cls.own_subscription = cls._make_for(cls.portal_user.partner_id)
        cls.foreign_subscription = cls._make_for(cls.other_partner)

    @classmethod
    def _make_for(cls, partner):
        return cls.env['subscription.subscription'].create({
            'partner_id': partner.id,
            'plan_id': cls.plan.id,
            'start_date': '2026-10-01',
            'line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'name': 'Portal line',
                'quantity': 1,
                'price_unit': 300.0,
            })],
        })

    def test_portal_list_page_shows_only_own_subscriptions(self):
        self.authenticate('portal.customer@example.com', 'Brightloop#2026')
        response = self.url_open('/my/subscriptions')
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.own_subscription.name, response.text)
        self.assertNotIn(self.foreign_subscription.name, response.text)

    def test_portal_detail_page_renders_for_own_subscription(self):
        self.authenticate('portal.customer@example.com', 'Brightloop#2026')
        response = self.url_open('/my/subscription/%s' % self.own_subscription.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.own_subscription.name, response.text)

    def test_portal_detail_page_blocks_another_customers_subscription(self):
        self.authenticate('portal.customer@example.com', 'Brightloop#2026')
        response = self.url_open(
            '/my/subscription/%s' % self.foreign_subscription.id, allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertNotIn(self.foreign_subscription.name, response.text)
