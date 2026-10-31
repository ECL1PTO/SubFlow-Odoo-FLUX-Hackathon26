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
