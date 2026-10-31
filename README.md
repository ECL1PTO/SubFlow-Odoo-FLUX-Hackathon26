# SubFlow - Subscription Management for Odoo 18

An Odoo 18 module that runs the full life of a subscription business: products and
plans, subscriptions, recurring invoicing, discounts, payments and revenue reporting,
with a customer portal. Built for the Odoo x FLUX Lucknow Hackathon '26.

## Quick start

Requirements: Docker Desktop.

```bash
git clone https://github.com/ECL1PTO/SubFlow-Odoo-FLUX-Hackathon26.git
cd SubFlow-Odoo-FLUX-Hackathon26
docker compose up -d
```

1. Open http://localhost:8069
2. Create a database (tick "Demo data" to load sample records).
3. Go to Apps, remove the "Apps" filter, search "Subscription Management" and install.

Stop with `docker compose down`. Add `-v` to also delete the database.

## Roles

| Role | Access |
|---|---|
| Administrator | Full control: plans, discounts, taxes, and adding staff |
| Staff | Day-to-day subscriptions and customers, no configuration rights |
| Customer (portal) | Read-only view of their own subscriptions and invoices |

Access is enforced in `security/` with group-based model access and record rules,
so a customer can never read another customer's records.

## Subscription lifecycle

```
Draft -> Quotation -> Confirmed -> Active -> Closed
                                     |  ^
                                     v  |
                                    Paused
```

Each transition is a button on the form, valid only from the right state.
Pausing and early closing are allowed or blocked per plan.

A quotation carries a validity date, taken from the plan's quotation validity in
days. Once it passes, the quotation can no longer be confirmed until it is reset
to draft and sent again. Set the validity to 0 for a quotation that never expires.

## Billing

Every active subscription tracks `next_invoice_date`. A daily scheduled action
invoices the ones that are due, then moves the date forward by the plan's period
multiplied by its interval, so "every 3 months" is one plan rather than three.
Because the date advances in the same transaction as the invoice, running the
cron twice never bills twice.

Discount rules apply automatically at invoicing: percentage rules set the
discount on the invoice line so tax is computed on the discounted base, and
fixed-amount rules are added as a negative line. Rules are filtered by date
window, minimum amount, minimum quantity, product scope and a usage cap.

Recording a payment goes through Odoo's payment register, so the payment is
reconciled against the invoice and the status becomes Paid.

## Dashboard

A dashboard reports active subscriptions, revenue, outstanding amount and
overdue invoice count. The figures come from SQL aggregates over posted customer
invoices, not from loading records in Python.

## Tests

```bash
docker compose stop odoo
docker compose run --rm --no-deps odoo odoo -d subflow -u subscription_management \
  --stop-after-init --test-enable --test-tags=/subscription_management \
  --http-port=8070 --db_host=db --db_user=odoo --db_password=odoo
docker compose up -d odoo
```

42 tests cover the lifecycle transitions, invoice generation and tax carry-over,
cron double-billing, discount rules, quotation validity, payment recording,
dashboard figures, password rules, access rights, and the portal pages over HTTP.

## Repository layout

```
subscription_management/
  models/       business logic (subscriptions, plans, billing, discounts)
  views/        list, form and search views, menus
  security/     groups, access rights, record rules
  data/         sequences and demo data
docker-compose.yml   Odoo 18 + PostgreSQL 16
```

## Team

Four contributors, each owning a separate slice so work merges cleanly:
subscriptions and security, billing and payments, plans and discounts,
portal and dashboard.
