# -*- coding: utf-8 -*-
##############################################################################
#
#    OCSWAFIP, Otro Cliente para el Servicio Web de la AFIP
#    Copyright (C) 2011-2015 Coop Trab Moldeo Interactive 
#    (<http://www.moldeointeractive.com.ar>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from M2Crypto import BIO, Rand, SMIME

class Signer:
    """
    Simplifica firmar digitalmente una cadena a enviar. 
    """
    def __init__(self, priv, cert, randpool=None):
        """
        Inicializa el objeto que permite firmar secuencias de caracteres.

        Argumentos:
        priv -- Nombre del archivo donde se encuentra la clave privada.
        cert -- Nombre del archivo donde se encuentra el certificado.
        randpool -- Nombre del archivo donde se encuentra datos generados aleatoreamente.

        """
        self.priv = priv
        self.cert = cert
        self.randpool = randpool
        if randpool is not None:
            Rand.load_file(self.randpool, -1)
        self.s = SMIME.SMIME()
        self.s.load_key(self.priv, self.cert)

    def __call__(self, data):
        """
        Devuelve el dato firmado.

        Argumentos:
        data -- Datos a ser firmados.
        """
        buf = BIO.MemoryBuffer(str(data))
        out = BIO.MemoryBuffer()
        p7 = self.s.sign(buf)
        self.s.write(out, p7)
        head, body, end = out.read().split('\n\n')
        return body

def _test_suite():
    import doctest
    return doctest.DocTestSuite()

if __name__ == "__main__":
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(test_suite())


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
