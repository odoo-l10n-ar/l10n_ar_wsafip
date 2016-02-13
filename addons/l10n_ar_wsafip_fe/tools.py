# -*- coding: utf-8 -*-
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
import datetime as dt


def conv_date(d, f="%Y%m%d"):
    """
    Convert a date format to Odoo date format
    """
    return dt.datetime.strptime(d, f).date().strftime(DATE_FORMAT)


def get_parents(child, parents=[]):
    """
    Functions to list parents names.
    """
    if child:
        return parents + [child.name] + get_parents(child.parent_id)
    else:
        return parents


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
