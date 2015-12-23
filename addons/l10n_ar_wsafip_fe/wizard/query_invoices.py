# -*- coding: utf-8 -*-
from openerp import fields, models, _, api
from openerp.exceptions import Warning
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

AFIP_DATE_FORMAT = "%Y%m%d"
AFIP_DATETIME_FORMAT = "%Y%m%d%H%M%S"


def _fch_(s):
    if s and len(s) == 8:
        return datetime.strptime(
            s, AFIP_DATE_FORMAT).strftime(DATETIME_FORMAT)
    elif s and len(s) > 8:
        return datetime.strptime(
            s, AFIP_DATETIME_FORMAT).strftime(DATETIME_FORMAT)
    else:
        return False


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
    def _take_number_format(self):
        self.ensure_one()

        sequence = self.journal_id.sequence_id
        interpolation_dict = sequence._interpolation_dict()
        interpolated_prefix = sequence._interpolate(
            sequence.prefix or "", interpolation_dict)
        interpolated_suffix = sequence._interpolate(
            sequence.suffix or "", interpolation_dict)
        number_format = "%s%%0%sd%s" % (
            interpolated_prefix, self.journal_id.sequence_id.padding,
            interpolated_suffix)
        return number_format

    @api.multi
    @api.model
    def _take_partner(self, DocTipo, DocNro):
        partner_pool = self.env['res.partner']
        document_type_pool = self.env['afip.document_type']

        partner = partner_pool.search([
            ('document_type_id.afip_code', '=', DocTipo),
            ('document_number', '=', DocNro),
        ])
        if not partner:
            # Create partner
            _logger.debug("Creating partner doc number: %s" % DocNro)
            document_type = document_type_pool.search(
                [('afip_code', '=', DocTipo)])
            assert len(document_type) == 1
            document_type = document_type[0]
            partner = partner_pool.create({
                'name': '%s' % DocNro,
                'document_type_id': document_type.id,
                'document_number': DocNro,
            })
        if not partner.property_account_receivable.id:
            raise Warning(
                _(u'Partner has not set a receivable account\n'
                    u'Please, first set the receivable account '
                    u'for %s') % partner.name)
        return partner

    @api.multi
    def _generate_cae(self, inv_number, r):
        self.ensure_one()

        tax_pool = self.env['account.tax']
        invoice_pool = self.env['account.invoice']
        invoice_line_pool = self.env['account.invoice.line']
        number_format = self._take_number_format()
        qi = self
        v_r = []

        cr = self.env.cr
        uid = self.env.uid
        context = self.env.context

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
                         (number_format % inv_number, tuple(inv_ids)))
            msg = 'Posible duplication from AFIP (%s)' % (
                number_format % inv_number)
            for inv_id in inv_ids:
                invoice_pool.message_post(
                    cr, uid, inv_id,
                    body=msg,
                    subtype=_mt_invoice_ws_action,
                    context=context)
        elif not inv_ids and qi.create_invoices:
            partner = qi._take_partner(r['DocTipo'], r['DocNro'])

            _logger.debug("Creating invoice number: %s" %
                          (number_format % inv_number))

            inv_id = invoice_pool.create(cr, uid, {
                'company_id': qi.journal_id.company_id.id,
                'account_id':
                partner.property_account_receivable.id,
                'internal_number': number_format % inv_number,
                'name':
                'Created from AFIP (%s)' % (
                    number_format % inv_number),
                'journal_id': qi.journal_id.id,
                'partner_id': partner.id,
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
                    ('tax_code_id.afip_code', '=', iva['Id']),
                    ('type_tax_use', '=', 'sale')
                ])
                line_vals = invoice_line_pool.product_id_change(
                    cr, uid, False,
                    qi.default_product_id.id
                    if r['Concepto'] == 1
                    else qi.default_service_id.id,
                    False,
                    qty=1,
                    name=_('AFIP declaration'),
                    type='out_invoice',
                    price_unit=iva['BaseImp'],
                    partner_id=partner.id,
                )
                line_vals['value']['invoice_id'] = inv_id
                line_vals['value']['tax_id'] = (6, 0, tax_id)
                line_vals['value']['price_unit'] = iva['BaseImp']
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
            _logger.debug("Ignoring invoice: %s" % (number_format % inv_number))
        return v_r

    @api.multi
    def execute(self):
        v_r = []
        for qi in self:
            conn = qi.journal_id.afip_connection_id
            serv = qi.journal_id.afip_connection_id.server_id

            if qi.first_invoice_number > qi.last_invoice_number:
                raise Warning(u'Qrong invoice range numbers\n'
                              u'Please, first invoice number must be less'
                              u' than last invoice')

            for inv_number in range(qi.first_invoice_number,
                                    qi.last_invoice_number+1):
                r = serv.wsfe_query_invoice(
                    conn,
                    qi.journal_id.journal_class_id.afip_code,
                    inv_number,
                    qi.journal_id.point_of_sale
                )

                if r and r['EmisionTipo'] == 'CAE':
                    v_r.extend(qi._generate_cae(inv_number, r))
                elif r:
                    raise Warning("Emision type %s not implemented for %i" %
                                  (r['EmisionTipo'], inv_number))
                else:
                    _logger.warning("Problem reading invoice %i" % inv_number)

            if qi.update_sequence:
                qi.journal_id.sequence_id.number_next = \
                    max(qi.journal_id.afip_items_generated,
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
