# -*- coding: utf-8 -*-
from openerp import models, api, _
from openerp.exceptions import Warning
from openerp.addons.l10n_ar_wsafip_fe.wizard.query_invoices import _fch_
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
        self.ensure_one()
        invoice_obj = self.env['account.invoice']
        partner_obj = self.env['res.partner']

        v_r = []

        qi = self
        conn = qi.journal_id.wsafip_connection_id
        serv = qi.journal_id.wsafip_connection_id.server_id

        if serv.code != 'wsfex':
            return super(query_invoices, self).execute()

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

            invoice = invoice_obj.search(
                [('journal_id', '=', qi.journal_id.id)] +
                invoice_domain)

            if invoice and qi.update_invoices and len(invoice) == 1:
                # Update Invoice
                _logger.debug("Update invoice number: %s" % (
                    number_format % inv_number))
                invoice.write({
                    'date_invoice': _fch_(r.FEXResultGet.Fecha_cbte),
                    'internal_number': number_format % inv_number,
                    'wsafip_cae': r.FEXResultGet.Cae,
                    'wsafip_cae_due': r.FEXResultGet.Fch_venc_Cae,
                    'amount_total': r.FEXResultGet.Imp_total,
                })
                msg = 'Updated from AFIP (%s)' % (
                    number_format % inv_number)
                invoice.message_post(
                    body=msg,
                    subtype="l10n_ar_wsafip_fe.mt_invoice_ws_action")
                v_r.append(invoice.id)
            elif invoice and qi.update_invoices and len(invoice) > 1:
                # Duplicated Invoices
                _logger.info("Duplicated invoice number: %s %s" %
                             (number_format % inv_number, tuple(invoice.ids)))
                msg = 'Posible duplication from AFIP (%s)' % (
                    number_format % inv_number)
                for inv in invoice:
                    invoice.message_post(
                        body=msg,
                        subtype=_mt_invoice_ws_action)
            elif not invoice and qi.create_invoices:
                partner = partner_obj.search([
                    ('name', '=', r.FEXResultGet.Cliente),
                    '|', '|', '|',
                    ('afip_destination_id.afip_cuit_company',
                     '=', r.FEXResultGet.Cuit_pais_cliente),
                    ('afip_destination_id.afip_cuit_person',
                     '=', r.FEXResultGet.Cuit_pais_cliente),
                    ('afip_destination_id.afip_cuit_other',
                     '=', r.FEXResultGet.Cuit_pais_cliente),
                    ('vat', '=', r.FEXResultGet.Id_impositivo),
                ])

                if not partner:
                    # Create partner
                    destination = partner_obj.destination_id.search([
                        ('afip_cuit_company',
                         '=', r.FEXResultGet.Cuit_pais_cliente),
                        ('afip_cuit_person',
                         '=', r.FEXResultGet.Cuit_pais_cliente),
                        ('afip_cuit_other',
                         '=', r.FEXResultGet.Cuit_pais_cliente),
                    ])
                    partner = partner_obj.create({
                        'name': '%s' % r.FEXResultGet.Cliente,
                        'afip_destination_id': destination or False,
                        'vat': r.FEXResultGet.Cuit_pais_cliente
                        if not destination else False,
                    })

                _logger.debug("Creating invoice number: %s" %
                              (number_format % inv_number))

                if not partner.property_account_receivable.id:
                    raise Warning(
                        _(u'Partner has not set a receivable account'
                          u'Please, first set the receivable account '
                          u'for %s') % partner.name)

                invoice = invoice_obj.create({
                    'company_id': qi.journal_id.company_id.id,
                    'account_id':
                    partner.property_account_receivable.id,
                    'internal_number': number_format % inv_number,
                    'name':
                    'Created from AFIP (%s)' % (
                        number_format % inv_number),
                    'journal_id': qi.journal_id.id,
                    'partner_id': partner.id,
                    'date_invoice': _fch_(r.FEXResultGet.Fecha_cbte),
                    'afip_cae': r.FEXResultGet.Cae,
                    'afip_cae_due': r.FEXResultGet.Fch_venc_Cae,
                    'amount_total': r.FEXResultGet.Imp_total,
                    'state': 'draft',
                })
                msg = 'Created from AFIP (%s)' % (
                    number_format % inv_number)
                invoice.message_post(
                    body=msg,
                    subtype=_mt_invoice_ws_action)
                v_r.append(invoice.id)
            else:
                _logger.debug("Ignoring invoice: %s" %
                              (number_format % inv_number))

        if qi.update_sequence:
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
