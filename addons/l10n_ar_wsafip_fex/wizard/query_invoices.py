# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from openerp.exceptions import Warning
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

_queries = {
    'by number': "[['number','=',invoice_number]]",
    'by nearest draft': "[['state','=','draft'],"
    "['partner_id.document_type_id.afip_code','=',result.Cbte_tipo],"
    "['partner_id.document_number','=',result.Cbte_nro],"
    "['amount_total','=',result.Imp_total]]",
}
_update_domain = [
    ('by number', 'By invoice number'),
    ('by nearest draft', 'Nearest draft invoice'),
]
_mt_invoice_ws_action = "l10n_ar_wsafip_fe.mt_invoice_ws_action"


class query_invoices(models.Model):
    _inherit = 'l10n_ar_wsafip_fe.query_invoices'

    @api.multi
    def execute(self):
        invoice_obj = self.env['account.invoice']

        for qi in self:
            conn = qi.journal_id.wsafip_connection_id
            serv = qi.journal_id.wsafip_connection_id.server_id

            if serv.code != 'wsfex':
                return super(query_invoice, self).execute()

            sequence = qi.journal_id.sequence_id
            interpolation_dict = sequence._interpolation_dict()
            interpolated_prefix = sequence._interpolate(
                sequence.prefix or "", interpolation_dict)
            interpolated_suffix = sequence._interpolate(
                sequence.suffix or "", interpolation_dict)
            number_format = "%s%%0%sd%s" % (
                interpolated_prefix, qi.journal_id.sequence_id.padding,
                interpolated_suffix)

            if qi.first_invoice_number > qi.last_invoice_number:
                raise Warning(
                    _(u'Qrong invoice range numbers'
                      u'Please, first invoice number must be less '
                      u'than last invoice'))

            v_r = []
            for inv_number in range(qi.first_invoice_number,
                                    qi.last_invoice_number+1):
                r = serv.wsfex_query_invoice(
                    conn.id,
                    qi.journal_id.journal_class_id.afip_code,
                    inv_number,
                    qi.journal_id.point_of_sale)

                invoice_domain = eval(
                    _queries[qi.update_domain],
                    {},
                    {'invoice_number': number_format % inv_number,
                     'response': r.FEXResultGet}
                )

                inv_ids = invoice_obj.search(
                    [('journal_id', '=', qi.journal_id.id)] +
                    invoice_domain)

                if inv_ids and qi.update_invoices and len(inv_ids) == 1:
                    # Update Invoice
                    import pdb; pdb.set_trace()
                    _logger.debug("Update invoice number: %s" % (
                        number_format % inv_number))
                    invoice_obj.write(cr, uid, inv_ids, {
                        'date_invoice': _fch_(r['CbteFch']),
                        'internal_number': number_format % inv_number,
                        'wsafip_cae': r['CodAutorizacion'],
                        'wsafip_cae_due': _fch_(r['FchProceso']),
                        'afip_service_start': _fch_(r['FchServDesde']),
                        'afip_service_end': _fch_(r['FchServHasta']),
                        'amount_total': r['ImpTotal'],
                    })
                    msg = 'Updated from AFIP (%s)' % (
                        number_format % inv_number)
                    invoice_obj.message_post(
                        cr, uid, inv_ids,
                        body=msg,
                        subtype="l10n_ar_wsafip_fe.mt_invoice_ws_action",
                        context=context)
                    v_r.extend(inv_ids)
                elif inv_ids and qi.update_invoices and len(inv_ids) > 1:
                    # Duplicated Invoices
                    import pdb; pdb.set_trace()
                    _logger.info("Duplicated invoice number: %s %s" %
                                    (number_format % inv_number, tuple(inv_ids)
                                    ))
                    msg = 'Posible duplication from AFIP (%s)' % (
                        number_format % inv_number)
                    for inv_id in inv_ids:
                        invoice_obj.message_post(
                            cr, uid, inv_id,
                            body=msg,
                            subtype=_mt_invoice_ws_action,
                            context=context)
                elif not inv_ids and qi.create_invoices:
                    import pdb; pdb.set_trace()
                    partner_id = partner_obj.search(cr, uid, [
                        ('document_type_id.afip_code', '=', r['DocTipo']),
                        ('document_number', '=', r['DocNro']),
                    ])
                    if partner_id:
                        # Take partner
                        partner_id = partner_id[0]
                    else:
                        # Create partner
                        _logger.debug("Creating partner doc number: %s"
                                        % r['DocNro'])
                        document_type_id = document_type_obj.search(
                            cr, uid, [('afip_code', '=', r['DocTipo'])])
                        assert len(document_type_id) == 1
                        document_type_id = document_type_id[0]
                        partner_id = partner_obj.create(cr, uid, {
                            'name': '%s' % r['DocNro'],
                            'document_type_id': document_type_id,
                            'document_number': r['DocNro'],
                        })
                    _logger.debug("Creating invoice number: %s" %
                                    (number_format % inv_number))
                    partner = partner_obj.browse(cr, uid, partner_id)
                    if not partner.property_account_receivable.id:
                        raise osv.except_osv(
                            _(u'Partner has not set a receivable account'),
                            _(u'Please, first set the receivable account '
                                u'for %s') % partner.name)

                    inv_id = invoice_obj.create(cr, uid, {
                        'company_id': qi.journal_id.company_id.id,
                        'account_id':
                        partner.property_account_receivable.id,
                        'internal_number': number_format % inv_number,
                        'name':
                        'Created from AFIP (%s)' % (
                            number_format % inv_number),
                        'journal_id': qi.journal_id.id,
                        'partner_id': partner_id,
                        'date_invoice': _fch_(r['CbteFch']),
                        'afip_cae': r['CodAutorizacion'],
                        'afip_cae_due': _fch_(r['FchProceso']),
                        'afip_service_start': _fch_(r['FchServDesde']),
                        'afip_service_end': _fch_(r['FchServHasta']),
                        'amount_total': r['ImpTotal'],
                        'state': 'draft',
                    })
                    for iva in r['Iva']:
                        tax_id = tax_obj.search(cr, uid, [
                            ('tax_code_id.afip_code','=',iva['Id']),
                            ('type_tax_use','=','sale')
                        ])
                        line_vals=invoice_line_obj.product_id_change(
                            cr, uid, False,
                            qi.default_product_id.id
                            if r['Concepto'] == 1
                            else qi.default_service_id.id,
                            False,
                            qty=1,
                            name=_('AFIP declaration'),
                            type='out_invoice',
                            price_unit=iva['BaseImp'],
                            partner_id=partner_id,
                        )
                        line_vals['value']['invoice_id']=inv_id
                        line_vals['value']['tax_id']=(6,0,tax_id)
                        line_vals['value']['price_unit']=iva['BaseImp']
                        invoice_line_obj.create(cr, uid, line_vals['value'])

                    msg = 'Created from AFIP (%s)' % (
                        number_format % inv_number)
                    invoice_obj.message_post(
                        cr, uid, inv_id,
                        body=msg,
                        subtype=_mt_invoice_ws_action,
                        context=context)
                    v_r.append(inv_id)
                else:
                    _logger.debug("Ignoring invoice: %s" %
                                    (number_format % inv_number))

            if qi.update_sequence:
                import pdb
                pdb.set_trace()
                qi.journal_id.sequence_id.number_next = \
                    max(qi.journal_id.wsafip_items_generated+1,
                        qi.journal_id.sequence_id.number_next)
                _logger.debug("Update invoice journal number to: %i" %
                              (qi.journal_id.sequence_id.number_next))


        return {
            'name': _('Invoices'),
            'domain': [('id', 'in', v_r)],
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'limit': 80,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
