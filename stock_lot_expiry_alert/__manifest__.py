{
    "name": "Stock Lot Expiry Alert",
    "summary": "Daily digest of lots in stock that are about to expire",
    "version": "17.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "Bassirou Sow",
    "website": "https://github.com/bass-sow/odoo-addons",
    "license": "LGPL-3",
    "depends": ["product_expiry", "mail"],
    "data": [
        "data/mail_template_data.xml",
        "data/ir_cron_data.xml",
        "views/res_config_settings_views.xml",
        "views/stock_lot_views.xml",
    ],
    "installable": True,
    "application": False,
}
