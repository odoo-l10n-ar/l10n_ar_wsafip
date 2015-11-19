# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
import logging

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')


class validate_invoices(osv.osv_memory):
    _name = 'l10n_ar_wsafip_fe.validate_invoices'
    _description = 'Generate CAE from validated invoices'
    _columns = {
        'journal_id': fields.many2one(
            'account.journal', 'Journal', required=True),
        'first_invoice_number': fields.integer(
            'First invoice number', required=True),
        'last_invoice_number': fields.integer(
            'Last invoice number', required=True),
    }
    _defaults = {
        'first_invoice_number': 1,
        'last_invoice_number': 1,
    }

    def onchange_journal_id(self, cr, uid, ids, first_invoice_number,
                            journal_id):
        journal_obj = self.pool.get('account.journal')
        res = {}

        if journal_id:
            num_items = journal_obj.browse(cr, uid, journal_id
                                           ).sequence_id.number_next - 1
            res['value'] = {
                'first_invoice_number': min(first_invoice_number, num_items),
                'last_invoice_number': num_items,
            }

        return res

    def execute(self, cr, uid, ids, context=None):
        context = context or {}
        invoice_obj = self.pool.get('account.invoice')

        for qi in self.browse(cr, uid, ids):
            journal_id = qi.journal_id.id
            number_format = "%s%%0%sd%s" % (
                qi.journal_id.sequence_id.prefix,
                qi.journal_id.sequence_id.padding,
                qi.journal_id.sequence_id.suffix)

            # Obtengo la lista de facturas necesitan un CAE y están validadas.
            inv_ids = invoice_obj.search(cr, uid,
                                         [('journal_id', '=', journal_id),
                                          ('state', '!=', 'draft'),
                                          ('afip_cae', '=', False),
                                          ('number', '>=', number_format %
                                           qi.first_invoice_number),
                                          ('number', '<=', number_format %
                                           qi.last_invoice_number)],
                                         order='date_invoice')

            invoice_obj.action_retrieve_cae(cr, uid, inv_ids)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
