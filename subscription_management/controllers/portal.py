from odoo import _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class SubscriptionPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'subscription_count' in counters:
            values['subscription_count'] = request.env['subscription.subscription'].search_count(
                [('partner_id', 'child_of', partner.commercial_partner_id.id)]
            )
        return values

    @route(['/my/subscriptions', '/my/subscriptions/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_subscriptions(self, page=1, sortby=None, **kw):
        partner = request.env.user.partner_id
        Subscription = request.env['subscription.subscription']
        domain = [('partner_id', 'child_of', partner.commercial_partner_id.id)]

        sortings = {
            'date': {'label': _('Newest'), 'order': 'start_date desc, id desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        sortby = sortby if sortby in sortings else 'date'
        order = sortings[sortby]['order']

        total = Subscription.search_count(domain)
        pager = portal_pager(
            url='/my/subscriptions',
            url_args={'sortby': sortby},
            total=total,
            page=page,
            step=self._items_per_page,
        )
        subscriptions = Subscription.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values = {
            'subscriptions': subscriptions,
            'page_name': 'subscription',
            'pager': pager,
            'default_url': '/my/subscriptions',
            'sortby': sortby,
            'sortings': sortings,
        }
        return request.render('subscription_management.portal_my_subscriptions', values)

    @route(['/my/subscription/<int:subscription_id>'], type='http', auth='user', website=True)
    def portal_subscription_detail(self, subscription_id, **kw):
        try:
            subscription = request.env['subscription.subscription'].browse(subscription_id)
            subscription.check_access_rights('read')
            subscription.check_access_rule('read')
        except (AccessError, MissingError):
            return request.redirect('/my')

        return request.render('subscription_management.portal_subscription_detail', {
            'subscription': subscription,
            'page_name': 'subscription',
        })
