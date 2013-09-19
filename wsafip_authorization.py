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
from stub.LoginCMSService_types import *
from stub.LoginCMSService_client import *
from random import randint
import xml.etree.ElementTree as ET
from dateutil.parser import parse as dateparse
from dateutil.tz import tzlocal
from datetime import datetime, timedelta
from openerp.tools.translate import _
import logging
from M2Crypto.X509 import X509Error
from ZSI import FaultException

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

_login_message="""\
<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
<header>
    <uniqueId>{uniqueid}</uniqueId>
    <generationTime>{generationtime}</generationTime>
    <expirationTime>{expirationtime}</expirationTime>
</header>
<service>{service}</service>
</loginTicketRequest>"""

_intmin = -2147483648
_intmax = 2147483647

class wsafip_authorization(osv.osv):
    def _get_state(self, cr, uid, ids, fields_name, arg, context=None):
        r = {}
        for auth in self.browse(cr, uid, ids):
            if False in (auth.uniqueid, auth.generationtime, auth.expirationtime, auth.token, auth.sign):
                _logger.info("AFIP reject connection.")
                r[auth.id]='disconnected'
            elif not dateparse(auth.generationtime) - timedelta(0,5) < datetime.now() :
                _logger.warning("clockshifted. Server: %s, Now: %s" %
                            (str(dateparse(auth.generationtime)), str(datetime.now())))
                _logger.warning("clockshifted. Please syncronize your host to a NTP server.")
                r[auth.id]='clockshifted'
            elif datetime.now() < dateparse(auth.expirationtime):
                r[auth.id]='connected'
            else:
                _logger.info("invalid Connection to AFIP.")
                r[auth.id]='invalid'
            # 'Invalid Partner' si el cuit del partner no es el mismo al de la clave publica/privada.
        return r

    _name = "wsafip.authorization"
    _columns = {
        'name': fields.char('Name', size=64),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'server_id': fields.many2one('wsafip.server', 'Service Server'),
        'logging_id': fields.many2one('wsafip.server', 'Authorization Server'),
        'certificate': fields.many2one('crypto.certificate', 'Certificate Signer'),
        'uniqueid': fields.integer('Unique ID', readonly=True),
        'token': fields.text('Token', readonly=True),
        'sign': fields.text('Sign', readonly=True),
        'generationtime': fields.datetime('Generation Time', readonly=True),
        'expirationtime': fields.datetime('Expiration Time', readonly=True),
        'state': fields.function(_get_state, method=True, string='Status', type='char', readonly=True),
        'batch_sequence_id': fields.many2one('ir.sequence', 'Batch Sequence', readonly=False),
    }

    _defaults = {
        'partner_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, [uid], c)[0].company_id.partner_id.id,
#        'logging_id': lambda self, cr, uid, c: self.pool.get('wsafip.server').search(cr, uid, [('code','=','wsaa'), ('class','=','homologación')], c)[0],
    }

    def login(self, cr, uid, ids, context=None):

        state = self._get_state(cr, uid, ids, None, None)

        for ws in self.browse(cr, uid, [ _id for _id, _stat in state.items()
                                        if _stat not in [ 'connected', 'clockshifted' ]]):
            obj_partner = self.pool.get('res.partner')
            obj_attachment = self.pool.get('ir.attachment')

            bind = LoginCMSServiceLocator().getLoginCms(url=ws.logging_id.url)

            uniqueid=randint(_intmin, _intmax)
            generationtime=(datetime.now(tzlocal()) - timedelta(0,60)).isoformat(),
            expirationtime=(datetime.now(tzlocal()) + timedelta(0,60)).isoformat(),
            msg = _login_message.format(
                uniqueid=uniqueid-_intmin,
                generationtime=(datetime.now(tzlocal()) - timedelta(0,60)).isoformat(),
                expirationtime=(datetime.now(tzlocal()) + timedelta(0,60)).isoformat(),
                service=ws.server_id.code
            )
            msg = ws.certificate.smime(msg)[ws.certificate.id]
            head, body, end = msg.split('\n\n')

            request  = loginCmsRequest()
            request._in0 = body
            response = bind.loginCms(request)

            T = ET.fromstring(response._loginCmsReturn)

            auth_data = {
            'source' : T.find('header/source').text,
            'destination' : T.find('header/destination').text,
            'uniqueid' : int(T.find('header/uniqueId').text)+_intmin,
            'generationtime' : dateparse(T.find('header/generationTime').text),
            'expirationtime' : dateparse(T.find('header/expirationTime').text),
            'token' : T.find('credentials/token').text,
            'sign' : T.find('credentials/sign').text,
            }

            del auth_data['source']
            del auth_data['destination']

            _logger.info("Successful Connection to AFIP.")
            self.write(cr, uid, ws.id, auth_data)

    def set_auth_request(self, cr, uid, ids, request):
        r = {}
        for auth in self.browse(cr, uid, ids):
            argAuth = request.new_argAuth()
            argAuth.set_element_Token(auth.token.encode('ascii'))
            argAuth.set_element_Sign(auth.sign.encode('ascii'))
            if 'ar' in auth.partner_id.vat:
                cuit = int(auth.partner_id.vat[2:])
                argAuth.set_element_cuit(cuit)
            else:
                raise osv.except_osv(_('Error in VATs'), _('Please check if your VAT is an Argentina one before continue.'))
            request.ArgAuth = argAuth
            r[auth.id] = request
        if len(ids) == 1:
            return r[ids[0]]
        else:
            return r

    def do_login(self, cr, uid, ids, context=None):
        try:
            self.login(cr, uid, ids)
        except X509Error, m:
            raise osv.except_osv(_('Certificate Error'), _(m))
        except FaultException, m:
            if type(m) is not str:
                m = m.fault.string
            raise osv.except_osv(_('AFIP Message'), _(m))
        return {}

wsafip_authorization()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
