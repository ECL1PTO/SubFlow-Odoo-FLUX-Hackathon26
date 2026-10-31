{
    'name': 'Subscription Management',
    'version': '18.0.1.0.0',
    'category': 'Sales/Subscriptions',
    'summary': 'Plans, subscriptions, recurring billing, discounts and revenue reporting',
    'description': """
Subscription Management
=======================
Run the full life of a subscription business in one place:

- Products with variants and subscription plans
- Subscriptions with a Draft -> Quotation -> Confirmed -> Active -> Closed lifecycle
- Automatic recurring invoicing with tax computation
- Discount rules applied automatically to upcoming invoices
- Payment recording and outstanding/overdue tracking
- Revenue dashboard for active subscriptions, payments and overdue invoices
- Customer portal restricted to a customer's own subscriptions and invoices
""",
    'author': 'Team SubFlow',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'account',
        'sale_management',
        'portal',
    ],
    'data': [
        'security/subscription_security.xml',
        'security/ir.model.access.csv',
        'data/subscription_sequence.xml',
        'views/subscription_views.xml',
        'views/subscription_plan_views.xml',
        'views/discount_rule_views.xml',
        'views/subscription_menus.xml',
        'data/cron_data.xml',
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
}