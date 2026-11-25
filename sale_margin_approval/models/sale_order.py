from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    margin_approval_state = fields.Selection(
        [
            ("not_needed", "Not Needed"),
            ("to_approve", "To Approve"),
            ("approved", "Approved"),
        ],
        string="Margin Approval",
        compute="_compute_margin_approval_state",
        store=True,
        help="'To Approve': the margin is below the company minimum and no Sales "
        "Manager has approved it. An approval stays valid as long as the margin does "
        "not drop below the approved value.",
    )
    margin_approved_percent = fields.Float(copy=False, readonly=True)
    margin_approved_by_id = fields.Many2one("res.users", copy=False, readonly=True)
    margin_approved_date = fields.Datetime(copy=False, readonly=True)
    margin_approval_requested = fields.Boolean(copy=False, readonly=True)
    company_min_margin = fields.Float(related="company_id.sale_min_margin")

    @api.depends(
        "state",
        "margin_percent",
        "amount_untaxed",
        "company_id.sale_min_margin",
        "margin_approved_by_id",
        "margin_approved_percent",
    )
    def _compute_margin_approval_state(self):
        for order in self:
            order.margin_approval_state = order._get_margin_approval_state()

    def _get_margin_approval_state(self):
        self.ensure_one()
        minimum = self.company_id.sale_min_margin / 100
        if (
            self.state not in ("draft", "sent")
            or not minimum
            or self.amount_untaxed <= 0
            or float_compare(self.margin_percent, minimum, precision_digits=4) >= 0
        ):
            return "not_needed"
        approved = self.margin_approved_by_id and float_compare(
            self.margin_percent, self.margin_approved_percent, precision_digits=4
        ) >= 0
        return "approved" if approved else "to_approve"

    def _is_margin_approver(self):
        return self.env.user.has_group("sales_team.group_sale_manager")

    def action_request_margin_approval(self):
        for order in self.filtered(lambda o: o.margin_approval_state == "to_approve"):
            approver = order.company_id.sale_margin_approver_id
            if approver:
                order.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=approver.id,
                    summary=_("Approve low margin quotation"),
                    note=_(
                        "Margin %(margin).1f%% is below the minimum of %(minimum).1f%%.",
                        margin=order.margin_percent * 100,
                        minimum=order.company_id.sale_min_margin,
                    ),
                )
            order.margin_approval_requested = True
            order.message_post(body=_(
                "Margin approval requested by %(user)s (margin %(margin).1f%%).",
                user=self.env.user.name,
                margin=order.margin_percent * 100,
            ))
        return True

    def action_approve_margin(self):
        if not self._is_margin_approver():
            raise AccessError(_("Only Sales Managers can approve low margin quotations."))
        for order in self.filtered(lambda o: o.margin_approval_state == "to_approve"):
            order.write({
                "margin_approved_percent": order.margin_percent,
                "margin_approved_by_id": self.env.user.id,
                "margin_approved_date": fields.Datetime.now(),
            })
            order.activity_feedback(["mail.mail_activity_data_todo"], feedback=_("Margin approved"))
            order.message_post(body=_(
                "Margin of %(margin).1f%% approved by %(user)s.",
                margin=order.margin_percent * 100,
                user=self.env.user.name,
            ))
        return True

    def action_confirm(self):
        pending = self.filtered(lambda o: o.margin_approval_state == "to_approve")
        if pending:
            if not self._is_margin_approver():
                raise UserError(_(
                    "These quotations have a margin below the company minimum and need a "
                    "Sales Manager's approval first: %s",
                    ", ".join(pending.mapped("name")),
                ))
            # A manager confirming is an approval: record who and at which margin.
            pending.action_approve_margin()
        return super().action_confirm()
