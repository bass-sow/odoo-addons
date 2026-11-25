# Sale Margin Approval (Odoo 17)

Salespeople can't confirm a quotation whose margin is below a company minimum. They ask
for approval, the Sales Manager gets an activity, approves it, and then the order can be
confirmed. Built on the margin that Odoo's `sale_margin` already computes (sale price
minus product cost).

## Features

- **Minimum margin per company** in Sales > Configuration > Settings > Pricing, next to
  the "Margins" option, plus the manager who receives the requests.
- **Margin approval state** on quotations: *Not Needed*, *To Approve*, *Approved*.
  Banner on the form, badge in the quotation list and a "Margin To Approve" filter.
- **Request Margin Approval** button: schedules a to-do activity for the approver and
  logs the request in the chatter.
- **Approve Margin** button (Sales Managers only): stores who approved, when and at which
  margin, and closes the activity.
- **Confirm is blocked** for salespeople while the margin is to approve. A manager who
  confirms directly is recorded as the approver.
- **Sales > Orders > Margins To Approve** menu for managers.

## Rules worth knowing

- An approval is tied to the approved margin. If the salesperson then adds a discount and
  the margin drops further, the quotation goes back to *To Approve*. If the margin goes
  up, the approval stays.
- Duplicating a quotation does not copy the approval.
- Changing the company minimum recomputes the state of the open quotations.
- Minimum margin 0 turns the check off.

## Technical notes

- `margin_approval_state` is a stored computed field depending on `margin_percent`
  (stored by `sale_margin`), the company minimum and the approval fields, so it can be
  searched, filtered and grouped without custom search methods.
- The check is in `action_confirm`, so it also applies to confirmations from code or
  other modules (e.g. online signature), not only to the button.
- Floating point comparisons use `float_compare` with 4 digits on the margin ratio.

## Tests

11 tests: approval flow, access rights (salesperson cannot approve), margin drop after
approval, recompute on settings change, copy.

```bash
./scripts/run_tests.sh sale_margin_approval   # from the repository root
```

## License

LGPL-3
