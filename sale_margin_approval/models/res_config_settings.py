from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_min_margin = fields.Float(related="company_id.sale_min_margin", readonly=False)
    sale_margin_approver_id = fields.Many2one(
        related="company_id.sale_margin_approver_id", readonly=False
    )
