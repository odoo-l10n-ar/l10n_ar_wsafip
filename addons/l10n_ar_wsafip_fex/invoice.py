# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
import logging
import re

from openerp.addons.l10n_ar_wsafip_fe.invoice import \
    re_label, _conv_date, _get_parents

_logger = logging.getLogger(__name__)


class account_invoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    def action_retrieve_cae(self):
        """
        Mensaje de solicitud de CAE
        """
        inv = self
        journal = inv.journal_id
        conn = journal.wsafip_connection_id

        # Only process if set to connect to afip
        if not conn:
            return True

        # Ignore invoice if connection server is not type WSFE.
        if conn.server_id.code != 'wsfex':
            return super(account_invoice, self).action_retrieve_cae()

        # Ignore journals with cae
        if inv.wsafip_cae and inv.wsafip_cae_due:
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

        if not inv.partner_id.afip_destination_id:
            raise ValidationError(
                _('Must defined a document destionarion for this partner.'))

        if inv.afip_concept in ('1',) and \
                journal.journal_class_id.afip_code in (19, 20, 21) and \
                not inv.afip_incoterm_id:
            raise ValidationError(
                _('Must define incoterm if you export products.'))

        if inv.tax_line:
            raise ValidationError(
                _('Must not have taxes.'))

        if inv.afip_concept in ('1',) and \
                journal.journal_class_id.afip_code in (19, 20, 21) and \
                not inv.afip_incoterm_id:
            raise ValidationError(
                _('Must define incoterm if you export products.'))

        if inv.journal_id.get_wsafip_state() == 'unsync':
            import pdb; pdb.set_trace()
            raise ValidationError(
                _('This invoice attemp to create an invoice'
                  ' with an invalid number.'))

        req = self._fex_new_request(journal, invoice_number)
        res = conn.server_id.wsfex_autorize(conn.id, [req])

        if res.FEXResultAuth.Cbte_nro != invoice_number:
            raise ValidationError('Desfazaje de número de facturas.')

        self.wsafip_cae = res.FEXResultAuth.Cae
        self.wsafip_cae_due = _conv_date(res.FEXResultAuth.Fch_venc_Cae)
        self.internal_number = invoice_number

        return True

    @api.multi
    def _fex_new_request(self, journal, invoice_number):
        self.ensure_one()

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
        seq = journal.wsafip_connection_id.batch_sequence_id

        return _remove_nones({
            'Id': seq.next_by_id(seq.id) or 1,
            'Fecha_cbte': _f_date(inv.date_invoice),
            'Cbte_Tipo': journal.journal_class_id.afip_code,
            'Punto_vta': journal.point_of_sale,
            'Cbte_nro': invoice_number,
            'Tipo_expo': inv.afip_concept,
            'Permiso_existente': 'N',
            'Permisos': None,
            'Dst_cmp': inv.partner_id.afip_destination_id.afip_code,
            'Cliente': inv.partner_id.name,
            'Cuit_pais_cliente':
            inv.partner_id.afip_destination_id.afip_cuit_company
            if inv.partner_id.is_company
            else inv.partner_id.afip_destination_id.afip_cuit_person,
            'Domicilio_cliente': inv.partner_id.contact_address,
            'Id_impositivo': inv.partner_id.vat,
            'Moneda_Id': inv.currency_id.afip_code,
            'Moneda_ctz': inv.currency_id.compute(1., inv.company_id.currency_id),
            'Obs_comerciales': inv.afip_commercial_obs,
            'Imp_total': inv.amount_total,
            'Obs': inv.afip_obs,
            'Forma_pago': inv.payment_term.name,
            'Incoterms': inv.afip_incoterm_id.afip_code
            if inv.afip_incoterm_id
            else None,
            'Incoterms_Ds': inv.afip_incoterm_description
            if inv.afip_incoterm_id
            else None,
            'Idioma_cbte': inv.partner_id.lang.afip_code or 2
            if inv.partner_id.lang
            else 2,
            'CbtesAsoc': {'CbteAsoc': inv.get_related_invoices() or None},
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
            }} for line in inv.invoice_line ]
        })


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
