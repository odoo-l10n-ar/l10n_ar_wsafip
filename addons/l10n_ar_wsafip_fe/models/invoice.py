# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
import sys
import logging
from openerp.addons.l10n_ar_wsafip_fe.tools import get_parents, conv_date

_logger = logging.getLogger(__name__)


class account_invoice(models.Model):
    _inherit = "account.invoice"

    wsafip_cae = fields.Char(
        'CAE number',
        size=24,
        readonly=True,
        copy=False)
    wsafip_cae_due = fields.Date(
        'CAE due',
        readonly=True,
        copy=False)
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

        if self.search([('journal_id', '=', self.journal_id.id),
                        ('state', '=', 'delayed')]):
            return False
        else:
            return True

    @api.multi
    def wsafip_validation(self):
        """
        Check if invoice could be created with this number.
        """
        self.ensure_one()

        _logger.info("Invoice state: %s" % self.state)

        inv = self
        jou = inv.journal_id
        conn = jou.wsafip_connection_id
        if conn:
            if (jou.wsafip_items_generated + 1 != jou.sequence_id.number_next):
                raise ValidationError(
                    _('La AFIP espera que el próximo número de secuencia'
                      ' sea %i, pero el sistema indica que será %i. '
                      'Hable inmediatamente con su administrador del '
                      'sistema para resolver este problema.'
                      ) % (jou.wsafip_items_generated + 1,
                           jou.sequence_id.number_next))

        return True

    @api.model
    def get_related_invoices(self, ktype="Tipo", ksp="PtoVta", kno="Nro"):
        rel_invs = self.search([
            ('number', '=', self.origin),
            ('state', 'not in', ['draft', 'proforma', 'proforma2', 'cancel'])
        ])
        return [{ktype: rel_inv.journal_id.journal_class_id.afip_code,
                 ksp: rel_inv.journal_id.point_of_sale,
                 kno: rel_inv.afip_doc_number} for rel_inv in rel_invs]

    @api.model
    def get_taxes(self):
        """
        Tributos: Detalle de tributos relacionados con el comprobante que se
        solicita autorizar (array).
        """
        # Ignore IVA for this list
        taxes = [
            tax for tax in self.tax_line
            if 'IVA' not in get_parents(tax.tax_code_id)
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
            if 'IVA' in get_parents(tax.tax_code_id)
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
        from openerp.tools import safe_eval

        opt_type_obj = self.env['afip.optional_type']

        return [{'Id': opt_type.afip_code,
                 'Valor': opt_type.value_computation(self)}
                for opt_type in opt_type_obj.search([])
                if opt_type.apply_rule and
                safe_eval(opt_type.apply_rule, self.env.context)]

    @api.multi
    def action_retrieve_cae(self):
        """
        Mensaje de solicitud de CAE
        """
        self.ensure_one()

        invs = [inv for inv in self
                # Only process if set to connect to AFIP.
                if inv.journal_id.wsafip_connection_id
                # Only if connection server is not type WSFE.
                and inv.journal_id.wsafip_connection_id.server_id.code == 'wsfe'
                # Ignore journals with cae.
                and not inv.wsafip_cae and not inv.wsafip_cae_due
                # Check if invoice number is ok.
                and inv.afip_doc_number
                # Currency must have AFIP code.
                and inv.currency_id.afip_code
                ]

        # Group invoices by journal.
        invs_group = {journal:
                      [inv for inv in invs if inv.journal_id == journal]
                      for journal in set(invs.mapped('journal_id'))}

        # Send validation, one by journal.
        for jou, invs in invs_group.items():
            reqs = [self._fe_new_request(jou, inv.afip_doc_number)
                    for inv in invs]
            conn = jou.connection_id
            res = conn.server_id.wsfe_get_cae(conn.id, reqs)

            for k, v in res.iteritems():
                inv = invs.filtered(lambda i: int(k) == int(i.afip_doc_number))
                if 'CAE' in v:
                    inv.wsafip_cae = v['CAE']
                    inv.wsafip_cae_due = conv_date(v['CAEFchVto'])
                    inv.internal_number = inv.number
                else:
                    inv.message_post(
                        'Error en la factura %s:\n' % k + '\n'.join(
                            [u'(%s) %s\n' % e for e in v['Errores']] +
                            [u'(%s) %s\n' % e for e in v['Observaciones']]
                        ),
                    )

        return True

    @api.model
    def _fe_new_request(self, journal, invoice_number):
        def _f_date(d):
            return d and d.replace('-', '')

        def _iva_filter(t):
            return 'IVA' in get_parents(t.tax_code_id)

        def _not_iva_filter(t):
            return 'IVA' not in get_parents(t.tax_code_id)

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
        is_electronic = bool(self.journal_id.wsafip_connection_id)

        return self.env['report'].get_action(
            self,
            'l10n_ar_wsafip_fe.report_invoice'
            if is_electronic else 'account.report_invoice'
        )

    @api.model
    def cron_wsafip_fe(self):
        _logger.info("Starting invoice validation")
        cr = self.env.cr

        # Solve unsynchronized journals
        for jou in self.mapped('journal_id').filtered(lambda x:
                                                      x.wsafip_state
                                                      == 'unsync'):
            query = self.env['l10n_ar_wsafip_fe.query_invoices'].create({
                'journal_id': jou.id,
                'first_invoice_number': jou.sequence_id.number_next,
                'last_invoice_number': jou.wsafip_items_generated,
                'update_invoices': True,
                'update_sequence': True,
                'update_domain': 'by number',
                'create_invoices': False
            })
            query.execute()

        # Validating invoices
        for inv in self.search(
            [
                ('journal_id.wsafip_connection_id.server_id.code', '=', 'wsfe'),
                ('state', '=', 'delayed'),
            ]
        ):
            try:
                inv.signal_workflow("invoice_open")
            except Exception as e:
                cr.rollback()
                _logger.info("ERROR(%s): %s" % (inv.name, str(e)))
                inv.message_post("Error validating invoice.\n"
                                 "ERROR: %s" % str(e))
                cr.commit()
            except:
                cr.rollback()
                e = sys.exc_info()[0]
                _logger.info("ERROR.sys(%s): %s" % (inv.name, str(e)))
                inv.message_post("Error validating invoice.\n"
                                 "ERROR: %s" % str(e))
                cr.commit()
            else:
                cr.commit()

        _logger.info("Finish invoice validation")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
