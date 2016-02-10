# -*- coding: utf-8 -*-
{'active': False,
 'name': 'Argentina - Factura Electrónica de Exportación del AFIP',
 'author': 'OpenERP - Team de Localización Argentina',
 'category': 'Localization/Argentina',
 'depends': ['l10n_ar_wsafip_fe'],
 'data': [
     'data/wsafip_server.xml',
     'data/invoice_view.xml',
     'data/invoice_workflow.xml',
     'data/journal_view.xml',
     # 'data/reports.xml',
     # 'data/wsafip_fe_config.xml',
     # 'data/res_config_view.xml',
     'data/wsafip_server_actions.xml',
     # 'data/report_invoice.xml',
     'data/wsafip.error.csv',
     # 'wizard/query_invoices_view.xml',
     # 'wizard/validate_invoices_view.xml',
     'security/wsafip_fex_security.xml',
     'security/ir.model.access.csv'
 ],
 'demo': [
     'test/journal.yml',
     'test/partners.yml'
 ],
 'license': 'AGPL-3',
 'test': [
     'test/check_journal.yml',
     'test/query_invoices.yml',
     'test/invoice.yml',
     ],
 'version': '8.0.1.2',
 'website': 'https://launchpad.net/~openerp-l10n-ar-localization',
 'installable': True,
 }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
