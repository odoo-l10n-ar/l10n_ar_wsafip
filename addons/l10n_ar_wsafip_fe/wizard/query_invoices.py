# -*- coding: utf-8 -*-
from openerp import fields, models, _, api
from openerp.exceptions import Warning
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

_queries = {
    'by number': "[['number','=',invoice_number]]",
    'by nearest draft': "[['state','=','draft'],"
    "['partner_id.document_type_id.afip_code','=',DocTipo],"
    "['partner_id.document_number','=',DocNro],"
    "['amount_total','=',ImpTotal]]",
}
_update_domain = [
    ('by number', 'By invoice number'),
    ('by nearest draft', 'Nearest draft invoice'),
]
_mt_invoice_ws_action = "l10n_ar_wsafip_fe.mt_invoice_ws_action"


class query_invoices(models.TransientModel):
    _name = 'l10n_ar_wsafip_fe.query_invoices'
    _description = 'Query for invoices in AFIP web services'

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True)
    first_invoice_number = fields.Integer(
        string='First invoice number',
        required=True,
        default=1)
    last_invoice_number = fields.Integer(
        string='Last invoice number',
        required=True,
        default=1)
    update_invoices = fields.Boolean(
        string='Update CAE if invoice exists')
    update_sequence = fields.Boolean(
        string='Update journal sequence if possible')
    update_domain = fields.Selection(
        selection=_update_domain,
        string="Update relation",
        default='by number')
    create_invoices = fields.Boolean(
        string='Create invoice in draft if not exists')
    default_product_id = fields.Many2one(
        'product.product',
        string='Default product')
    default_service_id = fields.Many2one(
        'product.product',
        string='Default service')

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        self.ensure_one()
        num_items = self.journal_id.afip_items_generated
        self.first_invoice_number = min(self.first_invoice_number, num_items)
        self.last_invoice_number = num_items

    @api.multi
    def execute(self):
        invoice_pool = self.env['account.invoice']
        invoice_line_pool = self.env['account.invoice.line']
        partner_pool = self.env['res.partner']
        document_type_pool = self.env['afip.document_type']
        tax_pool = self.env['account.tax']
        v_r = []

        for qi in self:
            conn = qi.journal_id.afip_connection_id
            serv = qi.journal_id.afip_connection_id.server_id

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
                raise Warning(u'Qrong invoice range numbers\n'
                              u'Please, first invoice number must be less'
                              u' than last invoice')

            def _fch_(s):
                if s and len(s) == 8:
                    return datetime.strptime(
                        s, "%Y%m%d").strftime('%Y-%m-%d %H:%M:%S')
                elif s and len(s) > 8:
                    return datetime.strptime(
                        s, "%Y%m%d%H%M%S").strftime('%Y-%m-%d %H:%M:%S')
                else:
                    return False

            for inv_number in range(qi.first_invoice_number,
                                    qi.last_invoice_number+1):
                import pdb; pdb.set_trace()

                r = serv.wsfe_query_invoice(
                    qi.journal_id.journal_class_id.afip_code,
                    inv_number,
                    qi.journal_id.point_of_sale)

                import pdb; pdb.set_trace()

                r = r[serv.id]

                if r['EmisionTipo'] == 'CAE':
                    invoice_domain = eval(
                        _queries[qi.update_domain],
                        {},
                        dict(r.items() + [
                            ['invoice_number', number_format % inv_number]]))
                    inv_ids = invoice_pool.search(
                        [('journal_id', '=', qi.journal_id.id)]
                        + invoice_domain)

                    if inv_ids and qi.update_invoices and len(inv_ids) == 1:
                        # Update Invoice
                        _logger.debug("Update invoice number: %s" % (
                            number_format % inv_number))
                        invoice_pool.write(cr, uid, inv_ids, {
                            'date_invoice': _fch_(r['CbteFch']),
                            'internal_number': number_format % inv_number,
                            'afip_cae': r['CodAutorizacion'],
                            'afip_cae_due': _fch_(r['FchProceso']),
                            'afip_service_start': _fch_(r['FchServDesde']),
                            'afip_service_end': _fch_(r['FchServHasta']),
                            'amount_total': r['ImpTotal'],
                        })
                        msg = 'Updated from AFIP (%s)' % (
                            number_format % inv_number)
                        invoice_pool.message_post(
                            cr, uid, inv_ids,
                            body=msg,
                            subtype="l10n_ar_wsafip_fe.mt_invoice_ws_action",
                            context=context)
                        v_r.extend(inv_ids)
                    elif inv_ids and qi.update_invoices and len(inv_ids) > 1:
                        # Duplicated Invoices
                        _logger.info("Duplicated invoice number: %s %s" %
                                     (number_format % inv_number, tuple(inv_ids)
                                      ))
                        msg = 'Posible duplication from AFIP (%s)' % (
                            number_format % inv_number)
                        for inv_id in inv_ids:
                            invoice_pool.message_post(
                                cr, uid, inv_id,
                                body=msg,
                                subtype=_mt_invoice_ws_action,
                                context=context)
                    elif not inv_ids and qi.create_invoices:
                        partner_id = partner_pool.search(cr, uid, [
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
                            document_type_id = document_type_pool.search(
                                cr, uid, [('afip_code', '=', r['DocTipo'])])
                            assert len(document_type_id) == 1
                            document_type_id = document_type_id[0]
                            partner_id = partner_pool.create(cr, uid, {
                                'name': '%s' % r['DocNro'],
                                'document_type_id': document_type_id,
                                'document_number': r['DocNro'],
                            })
                        _logger.debug("Creating invoice number: %s" %
                                      (number_format % inv_number))
                        partner = partner_pool.browse(cr, uid, partner_id)
                        if not partner.property_account_receivable.id:
                            raise osv.except_osv(
                                _(u'Partner has not set a receivable account'),
                                _(u'Please, first set the receivable account '
                                  u'for %s') % partner.name)

                        inv_id = invoice_pool.create(cr, uid, {
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
                            tax_id = tax_pool.search(cr, uid, [
                                ('tax_code_id.afip_code','=',iva['Id']),
                                ('type_tax_use','=','sale')
                            ])
                            line_vals=invoice_line_pool.product_id_change(
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
                            invoice_line_pool.create(cr, uid, line_vals['value'])

                        msg = 'Created from AFIP (%s)' % (
                            number_format % inv_number)
                        invoice_pool.message_post(
                            cr, uid, inv_id,
                            body=msg,
                            subtype=_mt_invoice_ws_action,
                            context=context)
                        v_r.append(inv_id)
                    else:
                        _logger.debug("Ignoring invoice: %s" %
                                      (number_format % inv_number))

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
