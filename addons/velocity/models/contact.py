# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Contact(models.Model):
    _inherit = 'res.partner'

    tin = fields.Char("TIN")
