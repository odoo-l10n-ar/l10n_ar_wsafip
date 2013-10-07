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
"""
This structure keep a cache structure to bind to not have continues connection
to the server.
"""
from sslhttps import HTTPSConnectionSSLVersion
from stub.LoginCMSService_client import *
import sys

PROXY_SIZE=5
TRACE_FILE=sys.stdout # To DEBUG: sys.stdout

ServiceSoap=LoginCMSServiceLocator().getLoginCms

_bind_cache = {}
_bind_list  = []

def get_bind(server, ssl=False):
    import pdb; pdb.set_trace()
    transport = HTTPSConnectionSSLVersion if ssl else None
    if not server.id in _bind_cache:
        if len(_bind_list) > PROXY_SIZE:
            del _bind_cache[_bind_list.pop(0)]
        _bind_cache[server.id] = ServiceSoap(url=server.url,
                                             transport=transport,
                                             tracefile=TRACE_FILE)
        _bind_list.append(server.id)
    return _bind_cache[server.id]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
