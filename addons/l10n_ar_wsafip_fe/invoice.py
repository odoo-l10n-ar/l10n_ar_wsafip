# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
import datetime as dt
import re
import logging
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


_logger = logging.getLogger(__name__)

# Label filter to recover invoice number
re_label = re.compile(r'%\([^\)]+\)s')


def _conv_date(d, f="%Y%m%d"):
    return dt.datetime.strptime(d, f).date().strftime(DATE_FORMAT)


def _get_parents(child, parents=[]):
    "Functions to list parents names."
    if child:
        return parents + [child.name] + _get_parents(child.parent_id)
    else:
        return parents


class account_invoice(models.Model):
    _inherit = "account.invoice"

    afip_batch_number = fields.Integer('AFIP Batch number', readonly=True)
    afip_cae = fields.Char('CAE number', size=24)
    afip_cae_due = fields.Date('CAE due')
    afip_error_id = fields.Many2one('wsafip.error',
                                    string='Web Service Status',
                                    readonly=True)
    state = fields.Selection(selection_add=[('delayed',
                                             'Delay WS Validation')])

    @api.multi
    def action_delay(self):
        self.write({'state': 'delayed'})
        return True

    @api.multi
    def no_delays(self):
        """
        Return true if exists any other invoice in delay in the journal
        """
        self.ensure_one()

        if self.search([('journal_id', '=', self.journal_id),
                        ('state', '=', 'delayed')]):
            return False
        else:
            return True

    @api.one
    def valid_batch(self):
        """
        Increment batch number groupping by afip connection server.
        """
        inv = self
        jou = inv.journal_id
        conn = jou.afip_connection_id
        if conn:
            if (jou.afip_items_generated + 1 != jou.sequence_id.number_next):
                raise ValidationError(
                    _('La AFIP espera que el próximo número de secuencia'
                      ' sea %i, pero el sistema indica que será %i. '
                      'Hable inmediatamente con su administrador del '
                      'sistema para resolver este problema.'
                      ) % (jou.afip_items_generated + 1,
                           jou.sequence_id.number_next))

            prefix = conn.batch_sequence_id.prefix or ''
            suffix = conn.batch_sequence_id.suffix or ''
            sid_re = re.compile('%s(\d*)%s' % (prefix, suffix))
            sid = conn.batch_sequence_id.next_by_id(conn.batch_sequence_id.id)
            inv.afip_batch_number = int(sid_re.search(sid).group(1))

        return True

    @api.model
    def get_related_invoices(self):
        rel_invs = self.search([
            ('number', '=', self.origin),
            ('state', 'not in', ['draft', 'proforma', 'proforma2', 'cancel'])
        ])
        return [{'Tipo': rel_inv.journal_id.journal_class_id.afip_code,
                 'PtoVta': rel_inv.journal_id.point_of_sale,
                 'Nro': self.number} for rel_inv in rel_invs]

    @api.model
    def get_taxes(self):
        """
        Tributos: Detalle de tributos relacionados con el comprobante que se
        solicita autorizar (array).
        """
        # Ignore IVA for this list
        taxes = [
            tax for tax in self.tax_line
            if 'IVA' not in _get_parents(tax.tax_code_id)
        ]

        # Check if all taxes has tax_code_id
        taxes_wo_code_id = [
            tax.name for tax in taxes
            if not tax.tax_code_id
        ]

        if taxes_wo_code_id:
            raise ValidationError(
                _(u'Please, check if you set tax code for '
                  u'invoice or refund to taxes: %s.') %
                ','.join(taxes_wo_code_id)
            )

        return [{'Id': tax.tax_code_id.parent_afip_code,
                 'Desc': tax.tax_code_id.name,
                 'BaseImp': tax.base_amount,
                 'Alic': tax.tax_amount / tax.base_amount,
                 'Importe': tax.tax_amount}
                for tax in taxes]

    @api.model
    def get_vat(self):
        """
        IVA: Detalle de alícuotasrelacionadas con el comprobante que se solicita
        autorizar (array).
        """
        taxes = [
            tax for tax in self.tax_line
            if 'IVA' in _get_parents(tax.tax_code_id)
        ]

        return [{'Id': tax.tax_code_id.parent_afip_code,
                 'BaseImp': tax.base_amount,
                 'Importe': tax.tax_amount}
                for tax in taxes]

    @api.model
    def get_optionals(self):
        """
        Los datos opcionales sólo deberán ser incluidos si el emisor pertenece
        al conjunto de emisores habilitados a informar opcionales. En ese caso
        podrá incluirel o los datos opcionalesque correspondan, especificando
        el identificador de dato opcional de acuerdo a la situación del emisor.
        El listado de tipos de datos opcionales se puede consultar con el método
        FEParamGetTiposOpcional
        """
        opt_type_obj = self.env['afip.optional_type']

        return [{'Id': opt_type.afip_code,
                 'Valor': opt_type.value_computation(self)}
                for opt_type in opt_type_obj.search([])
                if opt_type.apply_rule(self)]

    @api.one
    def action_retrieve_cae(self):
        """
        Mensaje de solicitud de CAE
        """
        inv = self
        journal = inv.journal_id
        conn = journal.afip_connection_id

        # Ignore invoice if connection server is not type WSFE.
        if conn.server_id.code != 'wsfe':
            return True

        # Ignore journals with cae
        if inv.afip_cae and inv.afip_cae_due:
            return True

        # Only process if set to connect to afip
        if not conn:
            return True

        # Take the last number of the "number".
        prefix_re = ".*".join([
            re.escape(w)
            for w in re_label.split(inv.journal_id.sequence_id.prefix or "")
        ])
        suffix_re = ".*".join([
            re.escape(w)
            for w in re_label.split(inv.journal_id.sequence_id.suffix or "")
        ])
        re_number = re.compile(prefix_re + r"(\d+)" + suffix_re)
        invoice_number = int(re_number.search(inv.number).group(1) or -1)

        if invoice_number < 0:
            raise ValidationError(
                _("Can't find invoice number. "
                  "Please check the journal sequence prefix and suffix "
                  "are not breaking the number generator."))

        if not inv.currency_id.afip_code:
            raise ValidationError(
                _('Must defined afip_code for the currency.'))

        req = self._new_request(journal, invoice_number)
        res = conn.server_id.wsfe_get_cae(conn.id, [req])

        for k, v in res.iteritems():
            if 'CAE' in v:
                self.afip_cae = v['CAE']
                self.afip_cae_due = _conv_date(v['CAEFchVto'])
                self.internal_number = invoice_number
            else:
                raise ValidationError(
                    'Factura %s:\n' % k + '\n'.join(
                        [u'(%s) %s\n' % e for e in v['Errores']] +
                        [u'(%s) %s\n' % e for e in v['Observaciones']]
                    ) + '\n')

        return True

    @api.model
    def _new_request(self, journal, invoice_number):
        def _f_date(d):
            return d and d.replace('-', '')

        def _iva_filter(t):
            return 'IVA' in _get_parents(t.tax_code_id)

        def _not_iva_filter(t):
            return 'IVA' not in _get_parents(t.tax_code_id)

        def _remove_nones(d):
            if (hasattr(d, 'iteritems')):
                return {k: _remove_nones(v)
                        for k, v in d.iteritems()
                        if _remove_nones(v) not in [None, {}]}
            else:
                return d

        inv = self

        return _remove_nones({
            'CbteTipo': journal.journal_class_id.afip_code,
            'PtoVta': journal.point_of_sale,
            'Concepto': inv.afip_concept,
            'DocTipo': inv.partner_id.document_type_id.afip_code or '99',
            'DocNro': int(inv.partner_id.document_number)
            if inv.partner_id.document_type_id.afip_code is not None
            and inv.partner_id.document_number
            and inv.partner_id.document_number.isdigit()
            else None,
            'CbteDesde': invoice_number,
            'CbteHasta': invoice_number,
            'CbteFch': _f_date(inv.date_invoice),
            'ImpTotal': inv.amount_total,
            # TODO:
            # Averiguar como calcular el Importe Neto no Gravado
            'ImpTotConc': 0,
            'ImpNeto': inv.amount_untaxed,
            'ImpOpEx': inv.compute_all(
                line_filter=lambda line: len(line.invoice_line_tax_id) == 0
            )['amount_total'],
            'ImpIVA': inv.compute_all(
                tax_filter=_iva_filter)['amount_tax'],
            'ImpTrib': inv.compute_all(
                tax_filter=_not_iva_filter)['amount_tax'] or None,
            'FchServDesde': _f_date(inv.afip_service_start)
            if inv.afip_concept != '1' else None,
            'FchServHasta': _f_date(inv.afip_service_end)
            if inv.afip_concept != '1' else None,
            'FchVtoPago': _f_date(inv.date_due)
            if inv.afip_concept != '1' else None,
            'MonId': inv.currency_id.afip_code,
            'MonCotiz': inv.currency_id.compute(1., inv.company_id.currency_id),
            'CbtesAsoc': {'CbteAsoc': inv.get_related_invoices() or None},
            'Tributos': {'Tributo': inv.get_taxes() or None},
            'Iva': {'AlicIva': inv.get_vat() or None},
            'Opcionales': {'Opcional': inv.get_optionals() or None},
        })

    @api.multi
    def invoice_print(self):
        '''
        This function prints the invoice and mark it as sent,
        so that we can see more easily the next step of the workflow
        Check if electronic invoice or normal invoice.
        '''
        assert len(self) == 1, \
            'This option should only be used for a single id at a time.'
        self.sent = True
        is_electronic = bool(self.journal_id.afip_connection_id)

        return self.env['report'].get_action(
            self,
            'l10n_ar_wsafip_fe.report_invoice'
            if is_electronic else 'account.report_invoice'
        )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
