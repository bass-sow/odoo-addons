# Account Payment Reminder (Odoo 17)

Automatic reminder emails for overdue customer invoices. Odoo Community has no payment
follow-ups (they are an Enterprise feature), so in many companies someone checks the aged
receivables by hand and writes the emails. This module does it every day with
configurable levels.

## Features

- **Reminder levels** (Invoicing > Configuration > Payment Reminders): days overdue, a
  message for that level and, optionally, an email template. Comes with 7, 15 and 30
  days ("First reminder", "Second reminder", "Final notice").
- **Daily scheduled action**: for each customer, one email per level reached that
  lists **all** its overdue invoices with due date, days overdue and amount due (not
  one email per invoice).
- **Each level is sent once per invoice.** An invoice that is already 40 days overdue
  when the module is installed gets the final notice only, not the three of them.
- On the invoice: *Last Reminder* and its date (Other Info tab), days overdue and last
  reminder in the invoice list, and a chatter message for each reminder sent.
- **Opt-out per customer** ("No Payment Reminders" on the Accounting tab), e.g. when a
  payment plan was agreed.
- **Reset Payment Reminders** action (Accounting managers) to start the sequence again.

## Rules worth knowing

- Only posted customer invoices that are not paid or are partially paid. Invoices
  "In Payment" are skipped.
- The email goes to the commercial partner (the company, not the contact on the
  invoice). Customers without an email are skipped and logged, and the invoice is not
  marked as reminded.
- The due date used is the invoice's `invoice_date_due` (the last installment when the
  payment terms have several).

## Technical notes

- Grouping is done in Python on a single search per company, keyed by
  `(commercial_partner_id, level)`.
- The template is rendered on `res.partner` with the invoice ids in the context, so the
  same template works for any number of invoices.
- Multi-company: levels belong to a company and the cron loops over the companies that
  have levels.

## Tests

10 tests on top of `AccountTestInvoicingCommon`: days overdue, level selection, one email
per customer and level, no duplicates, next level after more days, paid invoices,
opt-out, customers without email, chatter and reset, cron.

```bash
./scripts/run_tests.sh account_payment_reminder   # from the repository root
```

## License

LGPL-3
