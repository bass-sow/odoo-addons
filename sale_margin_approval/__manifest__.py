{
    "name": "Sale Margin Approval",
    "summary": "Quotations below a minimum margin need a manager's approval before confirmation",
    "version": "17.0.1.0.0",
    "category": "Sales/Sales",
    "author": "Bassirou Sow",
    "website": "https://github.com/bass-sow/odoo-addons",
    "license": "LGPL-3",
    "depends": ["sale_margin", "sale_management"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
