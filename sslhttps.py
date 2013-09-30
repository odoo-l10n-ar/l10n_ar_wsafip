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

import socket
import httplib
import ssl

class HTTPSConnectionSSLVersion(httplib.HTTPConnection):
        "This class allows communication via SSL."

        default_port = httplib.HTTPS_PORT

        def __init__(self, host, port=None, key_file=None, cert_file=None,
                     strict=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                     source_address=None, ssl_version=ssl.PROTOCOL_TLSv1):
            # Fix error for python 2.6
            try:
                super(HTTPSConnectionSSLVersion, self).__init__(host, port, strict, timeout, source_address)
            except:
                httplib.HTTPConnection.__init__(self, host, port, strict, timeout)
            self.key_file = key_file
            self.cert_file = cert_file
            self.ssl_version = ssl_version

        def connect(self):
            "Connect to a host on a given (SSL) port."
            # Fix error for python 2.6
            try:
                sock = socket.create_connection((self.host, self.port),
                                            self.timeout, self.source_address)
            except:
                sock = socket.create_connection((self.host, self.port), self.timeout)
            if self._tunnel_host:
                self.sock = sock
                self._tunnel()
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=self.ssl_version)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
