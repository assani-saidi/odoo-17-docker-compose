# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Comnpany(models.Model):
    _inherit = 'res.company'

    logo_size = fields.Integer(string="Log Size", help="logo size in pixels/mm")
