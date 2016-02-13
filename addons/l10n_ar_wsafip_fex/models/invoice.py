# -*- coding: utf-8 -*-
from openerp import models, api, _
from openerp.exceptions import ValidationError
import logging

from openerp.addons.l10n_ar_wsafip_fe.tools import conv_date

_logger = logging.getLogger(__name__)


def _f_date(d):
    return d and d.replace('-', '')


def _remove_nones(d):
    if (hasattr(d, 'iteritems')):
        return {k: _remove_nones(v)
                for k, v in d.iteritems()
                if _remove_nones(v) not in [None, {}]}
    else:
        return d


class account_invoice(models.Model):
    _inherit = "account.invoice"

    @api.depends('afip_doc_number',
                 'currency_id.afip_code',
                 'partner_id.afip_destination_id',
                 'afip_concept',
                 'tax_line')
    @api.multi
    def fex_validation(self):
        self.ensure_one()

        journal = self.journal_id

        invoice_number = self.afip_doc_number

        if invoice_number is False or invoice_number < 0:
            raise ValidationError(
                _("Can't find invoice number. "
                  "Please check the journal sequence prefix and suffix "
                  "are not breaking the number generator."))

        if not self.currency_id.afip_code:
            raise ValidationError(
                _('Must defined afip_code for the currency.'))

        if not self.partner_id.afip_destination_id:
            raise ValidationError(
                _('Must defined a document destionarion for this partner.'))

        if self.afip_concept in ('1',) and \
                journal.journal_class_id.afip_code in (19, 20, 21) and \
                not self.afip_incoterm_id:
            raise ValidationError(
                _('Must define incoterm if you export products.'))

        if self.tax_line:
            raise ValidationError(
                _('Must not have taxes.'))

    @api.depends('afip_doc_number')
    @api.one
    def action_retrieve_cae(self):
        """
        Mensaje de solicitud de CAE
        """
        self.ensure_one()
        journal = self.journal_id
        conn = journal.wsafip_connection_id

        # Only process if set to connect to afip
        if not conn:
            return True

        # Ignore invoice if connection server is not type WSFE.
        if conn.server_id.code != 'wsfex':
            return super(account_invoice, self).action_retrieve_cae()

        # Ignore journals with cae
        if self.wsafip_cae and self.wsafip_cae_due:
            return True

        self.fex_validation()

        req = self._fex_new_request()
        res = conn.server_id.wsfex_autorize(conn.id, [req])

        if res.FEXResultAuth.Cbte_nro != self.afip_doc_number:
            _logger.warning(res)
            raise ValidationError('Desfazaje de número de facturas.')

        self.wsafip_cae = res.FEXResultAuth.Cae
        self.wsafip_cae_due = conv_date(res.FEXResultAuth.Fch_venc_Cae)
        self.internal_number = self.number

        return True

    @api.multi
    def _fex_new_request(self):
        self.ensure_one()

        journal = self.journal_id
        seq = journal.wsafip_connection_id.batch_sequence_id

        return _remove_nones({
            'Id': seq.next_by_id(seq.id) or 1,
            'Fecha_cbte': _f_date(self.date_invoice),
            'Cbte_Tipo': journal.journal_class_id.afip_code,
            'Punto_vta': journal.point_of_sale,
            'Cbte_nro': self.afip_doc_number,
            'Tipo_expo': self.afip_concept,
            'Permiso_existente': 'N',
            'Permisos': None,
            'Dst_cmp': self.partner_id.afip_destination_id.afip_code,
            'Cliente': self.partner_id.name,
            'Cuit_pais_cliente':
            self.partner_id.afip_destination_id.afip_cuit_company
            if self.partner_id.is_company
            else self.partner_id.afip_destination_id.afip_cuit_person,
            'Domicilio_cliente': self.partner_id.contact_address,
            'Id_impositivo': self.partner_id.vat,
            'Moneda_Id': self.currency_id.afip_code,
            'Moneda_ctz': self.currency_id.compute(1,
                                                   self.company_id.currency_id),
            'Obs_comerciales': self.afip_commercial_obs,
            'Imp_total': self.amount_total,
            'Obs': self.afip_obs,
            'Forma_pago': self.payment_term.name,
            'Incoterms': self.afip_incoterm_id.afip_code
            if self.afip_incoterm_id
            else None,
            'Incoterms_Ds': self.afip_incoterm_description
            if self.afip_incoterm_id
            else None,
            'Idioma_cbte': self.partner_id.lang.afip_code or 2
            if self.partner_id.lang
            else 2,
            'CbtesAsoc': {'CbteAsoc': self.get_related_invoices() or None},
            'Items': [{'Item': {
                'Pro_codigo': line.product_id.code,
                'Pro_ds': line.name,
                'Pro_umed': line.uos_id.afip_code,
                'Pro_qty': line.quantity
                if line.uos_id.afip_code not in (0, 97, 99) else 0,
                'Pro_precio_uni': line.price_unit
                if line.uos_id.afip_code not in (0, 97, 99) else 0,
                'Pro_bonificacion': line.discount
                if line.uos_id.afip_code not in (0, 97, 99) else 0,
                'Pro_total_item': line.price_subtotal
            }} for line in self.invoice_line]
        })


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
