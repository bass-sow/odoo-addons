from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_min_margin = fields.Float(
        string="Minimum Margin (%)",
        help="Quotations with a margin below this percentage need a Sales Manager's "
        "approval before they can be confirmed. 0 disables the check.",
    )
    sale_margin_approver_id = fields.Many2one(
        "res.users",
        string="Margin Approver",
        domain=lambda self: [("groups_id", "in", self.env.ref("sales_team.group_sale_manager").id)],
        help="Sales Manager who gets an activity when a salesperson asks for approval. "
        "If empty, any Sales Manager can approve but nobody is notified.",
    )
