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
from signer import Signer
from stub.LoginCMSService_types import *
from stub.LoginCMSService_client import *
from rand import randint
import xml.etree.ElementTree as ET
from dateutil.parser import parse as dateparse
from dateutil.tz import tzlocal
from firmante import Firmante

_login_message="""\
<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
<header>
    <uniqueId>{uniqueId}</uniqueId>
    <generationTime>{generationTime}</generationTime>
    <expirationTime>{expirationTime}</expirationTime>
</header>
<service>{service}</service>
</loginTicketRequest>
"""

class wsafip_service(osv.osv):
    _name = "wsafip.service"
    _columns = {
        'name': fields.char('Name', size=64),
        'code': fields.char('Code', size=16)
    }

class wsafip_service(osv.osv):
    def _get_status(self, cr, uid, ids, fields_name, arg, context=None):
        if None in (self.uniqueId, self.generationTime, self.expirationTime, self.token, self.sign):
            return 'Disconnected'
        elif datetime.now(tzlocal()) < self.generationTime - timedelta(0,1):
            return 'Shifted Clock'
        elif datetime.now(tzlocal()) < self.expirationTime:
            return 'Connected'
        else:
            return 'Invalid'
        # 'Invalid Partner' si el cuit del partner no es el mismo al de la clave publica/privada.

    _name = "wsafip.authorization"
    _columns = {
        'name': fields.char('Name', size=64),
        'partner': fields.many2one('res.partner', 'Partner'),
        'certfile': field.many2one('ir.attachment', 'Certification File'),
        'keyfile': field.many2one('ir.attachment', 'Key File'),
        'uniqueId': fields.integer('Unique ID'),
        'service': fields.many2one('wsafip.service', 'Service'),
        'token': fields.char('Token', size=512),
        'sign': field.char('Sign', size=512),
        'generationTime': field.datetime('Generation Time'),
        'expirationTime': field.datetime('Expiration Time'),
        'status': field.function('Status', _get_status),
    }

    def login(self, cr, uid, ids, context=None):
        if self.state == 'Connected': return

        obj_partner = self.pool.get('res.partner')
        obj_attachment = self.pool.get('ir.attachment')

###
        bind = LoginCMSServiceLocator().getLoginCms()

        keyfile = 
        certfile = 
        S = Signer(keyfile, certfile)

        uniqueId=randint(0, 10**9)
        generationTime=(datetime.now(tzlocal()) - timedelta(0,60)).isoformat(),
        expirationTime=(datetime.now(tzlocal()) + timedelta(0,60)).isoformat(),
        service=self.service
        msg = S(_login_message.format(
            uniqueId=1313901283,
            generationTime=(datetime.now(tzlocal()) - timedelta(0,60)).isoformat(),
            expirationTime=(datetime.now(tzlocal()) + timedelta(0,60)).isoformat(),
            service='wsfe'
        ))

        request  = loginCmsRequest()
        request._in0 = msg
        response = bind.loginCms(request)

        T = ET.fromstring(response._loginCmsReturn)

        auth_data = {
        'source' : T.find('header/source').text,
        'destination' : T.find('header/destination').text,
        'uniqueId' : int(T.find('header/uniqueId').text),
        'generationTime' : dateparse(T.find('header/generationTime').text),
        'expirationTime' : dateparse(T.find('header/expirationTime').text),
        'token' : T.find('credentials/token').text,
        'sign' : T.find('credentials/sign').text,
        }

        # Faltan los asserts!
        assert(int(auth_data('uniqueId'))==uniqueId)
        assert(auth_data('generationTime') < datetime.now(tzlocal()))
        assert(datetime.now(tzlocal()) < auth_data('expirationTime'))

        self.uniqueId = auth_data('uniqueId')
        self.token = auth_data('token')
        self.sign = auth_data('sign')
        self.generationTime = auth_data('generationTime')
        self.experationTime = auth_data('experationTime')

wsafip_service()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
