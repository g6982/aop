# © 2011-2015 Sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Stock Scanner',
    'summary': 'Allows managing barcode readers with simple scenarios',
    'version': '12.0.1.0.1',
    'category': 'Generic Modules/Inventory Control',
    'website': 'https://github.com/OCA/stock-logistics-barcode',
    'author': 'Subteno IT,'
              'ACSONE SA/NV,'
              'Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'depends': [
        'base_sparse_field',
        'product',
        'stock',
    ],
    'data': [
        'security/stock_scanner_security.xml',
        'security/ir.model.access.csv',
        'data/stock_scanner.xml',
        'data/ir_cron.xml',
        'data/scenarios/Login/Login.scenario',
        'data/scenarios/Logout/Logout.scenario',
        'data/scenarios/Stock/Stock.scenario',
        'wizard/res_config_settings.xml',
        'views/menu.xml',
        'views/scanner_scenario.xml',
        'views/scanner_scenario_step.xml',
        'views/scanner_scenario_transition.xml',
        'views/scanner_hardware.xml',
        'demo/stock_scanner_demo.xml',
        'demo/Tutorial/Tutorial.scenario',
        'demo/Tutorial/Step_types/Step_types.scenario',
        'demo/Tutorial/Sentinel/Sentinel.scenario',
    ],
    'demo': [
        'demo/stock_scanner_demo.xml',
        'demo/Tutorial/Tutorial.scenario',
        'demo/Tutorial/Step_types/Step_types.scenario',
        'demo/Tutorial/Sentinel/Sentinel.scenario',
        'tests/data/Test.scenario',
    ],
    'images': [
        'images/scanner_hardware.png',
        'images/scanner_scenario.png',
        'images/scanner_screen.png',
    ],
}
