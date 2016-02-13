# -*- coding: utf-8 -*-

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(cr, version):
    openupgrade.rename_columns(cr, {
        'account_journal': [('afip_connection_id', 'wsafip_connection_id')],
        'account_invoice': [('afip_cae', 'wsafip_cae'),
                            ('afip_cae_due', 'wsafip_cae_due')]
    })

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
