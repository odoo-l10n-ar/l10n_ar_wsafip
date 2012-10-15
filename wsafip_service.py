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
from osv import fields, osv
from stub.LoginCMSService_types import *
from stub.LoginCMSService_client import *
from random import randint
import xml.etree.ElementTree as ET
from dateutil.parser import parse as dateparse
from dateutil.tz import tzlocal
from datetime import datetime, timedelta

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

class wsafip_service(osv.osv):
    _name = "wsafip.service"
    _columns = {
        'name': fields.char('Name', size=64),
        'code': fields.char('Code', size=16)
    }
wsafip_service()

class wsafip_authorization(osv.osv):
    def _get_status(self, cr, uid, ids, fields_name, arg, context=None):
        r = {}
        for auth in self.browse(cr, uid, ids):
            if False in (auth.uniqueid, auth.generationtime, auth.expirationtime, auth.token, auth.sign):
                r[auth.id]='Disconnected'
            elif dateparse(auth.generationtime) - timedelta(0,1) < datetime.now() :
                r[auth.id]='Shifted Clock'
            elif datetime.now() < dateparse(auth.expirationtime):
                r[auth.id]='Connected'
            else:
                r[auth.id]='Invalid'
            # 'Invalid Partner' si el cuit del partner no es el mismo al de la clave publica/privada.
        return r

    _name = "wsafip.authorization"
    _columns = {
        'name': fields.char('Name', size=64),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'service': fields.many2one('wsafip.service', 'Service'),
        'certificate': fields.many2one('crypto.certificate', 'Certificate Signer'),
        'url': fields.char('URL', size=512),
        'uniqueid': fields.integer_big('Unique ID'),
        'token': fields.char('Token', size=512),
        'sign': fields.char('Sign', size=512),
        'generationtime': fields.datetime('Generation Time'),
        'expirationtime': fields.datetime('Expiration Time'),
        'status': fields.function(_get_status, method=True, string='Status', type='char'),
    }

    def login(self, cr, uid, ids, context=None):

        status = self._get_status(cr, uid, ids, None, None)

        for ws in self.browse(cr, uid, [ _id for _id, _stat in status.items() if _stat != 'Connected' ]):
            obj_partner = self.pool.get('res.partner')
            obj_attachment = self.pool.get('ir.attachment')

            bind = LoginCMSServiceLocator().getLoginCms(url=ws.url)

            uniqueid=randint(0, 10**9)
            generationtime=(datetime.now(tzlocal()) - timedelta(0,60)).isoformat(),
            expirationtime=(datetime.now(tzlocal()) + timedelta(0,60)).isoformat(),
            msg = _login_message.format(
                uniqueid=uniqueid,
                generationtime=(datetime.now(tzlocal()) - timedelta(0,60)).isoformat(),
                expirationtime=(datetime.now(tzlocal()) + timedelta(0,60)).isoformat(),
                service=ws.service.code
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
            'uniqueid' : int(T.find('header/uniqueId').text),
            'generationtime' : dateparse(T.find('header/generationTime').text),
            'expirationtime' : dateparse(T.find('header/expirationTime').text),
            'token' : T.find('credentials/token').text,
            'sign' : T.find('credentials/sign').text,
            }

            del auth_data['source']
            del auth_data['destination']

            self.write(cr, uid, ws.id, auth_data)

    def set_auth_request(self, cr, uid, ids, request):
        assert(type(ids) == int)
        auth = self.browse(cr, uid, ids)
        argAuth = request.new_argAuth()
        argAuth.set_element_Token(auth.token)
        argAuth.set_element_Sign(auth.sign)
        argAuth.set_element_cuit(auth.partner_id.vat)
        request.ArgAuth = argAuth
        return request

wsafip_authorization()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
