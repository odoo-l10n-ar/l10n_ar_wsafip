# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2012 OpenERP - Team de Localización Argentina.
# https://launchpad.net/~openerp-l10n-ar-localization
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import fields, osv
import logging
import base64
from M2Crypto import X509

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

class l10n_ar_wsafip_keygen_config(osv.osv_memory):
    def _default_company(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id

    def update_data(self, cr, uid, ids, company_id, context=None):
        company = self.pool.get('res.company').browse(cr, uid, company_id)
        v = {
            'country_id': company.country_id.id if company.country_id else None,
            'state_id': company.state_id.id if company.state_id else None,
            'city': company.city or None,
            'cuit': company.partner_id.vat[2:] if company.partner_id.vat else None,
        }
        return {'value': v}

    def execute(self, cr, uid, ids, context=None):
        """
        """
        pairkey_obj = self.pool.get('crypto.pairkey')

        for wzr in self.read(cr, uid, ids):
            pk_id = pairkey_obj.create(cr, uid, { 'name': wzr['name'] }, context=context)
            x509_name = X509.X509_Name()
            x509_name.C = wzr['country_id'][1].encode('ascii', 'ignore')
            x509_name.ST = wzr['state_id'][1].encode('ascii', 'ignore')
            x509_name.L = wzr['city'].encode('ascii', 'ignore')
            x509_name.O = wzr['company_id'][1].encode('ascii', 'ignore')
            x509_name.OU = wzr['department'].encode('ascii', 'ignore')
            x509_name.serialNumber = 'CUIT %s' % wzr['cuit'].encode('ascii', 'ignore')
            x509_name.CN = wzr['name'].encode('ascii', 'ignore')
            pairkey_obj.generate_keys(cr, uid, [pk_id], context=context)
            crt_ids = pairkey_obj.generate_certificate_request(cr, uid, [pk_id], x509_name, context=context)
        return True

    _name = 'l10n_ar_wsafip.keygen_config'
    _inherit = 'res.config'
    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'country_id': fields.many2one('res.country', 'Country', required=True),
        'state_id': fields.many2one('res.country.state', 'State', required=True),
        'city': fields.char('City', size=64, required=True),
        'department': fields.char('Department', size=64, required=True),
        'cuit': fields.char('CUIT', size=16, required=True),
        'name': fields.char('Name', size=64, required=True),
    }
    _defaults= {
        'company_id': _default_company,
        'department': 'IT',
        'name': 'AFIP Web Services',
    }
l10n_ar_wsafip_keygen_config()


class l10n_ar_wsafip_loadcert_config(osv.osv_memory):

    def update_data(self, cr, uid, ids, certificate_id, context=None):
        certificate = self.pool.get('crypto.certificate').browse(cr, uid, certificate_id)
        v = {
            'request_string': certificate.csr,
            'request_file': base64.encodestring(certificate.csr),
        }
        return {'value': v}

    def execute(self, cr, uid, ids, context=None):
        """
        """
        certificate_obj = self.pool.get('crypto.certificate')
        for wz in self.browse(cr, uid, ids, context=context):
            wz.request_id.write({'crt': wz.response_string})
            wz.request_id.action_validate()

        return True

    _name = 'l10n_ar_wsafip.loadcert_config'
    _inherit = 'res.config'
    _columns = {
        'request_id': fields.many2one('crypto.certificate', 'Certificate Request', required=True),
        'request_file': fields.binary('', readonly=True),
        'request_string': fields.text('Certificate string', readonly=True),
        'response_string': fields.text('Response string', required=True),
    }
    _defaults= {
    }
l10n_ar_wsafip_loadcert_config()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
