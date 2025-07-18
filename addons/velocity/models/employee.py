# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class Account(models.Model):
    _inherit = "hr.employee"

    employee_code = fields.Char("Employee Code", required=True)
