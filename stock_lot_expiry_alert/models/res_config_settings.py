from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    expiry_warning_days = fields.Integer(
        related="company_id.expiry_warning_days", readonly=False
    )
    expiry_responsible_id = fields.Many2one(
        related="company_id.expiry_responsible_id", readonly=False
    )
