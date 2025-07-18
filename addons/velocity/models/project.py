# -*- coding: utf-8 -*-
from email.policy import default

from odoo import api, fields, models
from odoo.api import ondelete
from odoo.exceptions import UserError
from datetime import timedelta
import re

from odoo.tools import raise_error

SEQUENCE_CODES = ['HT', 'FS', 'VL']


class SuperTrip(models.Model):
    _name = "velocity.super_trip"
    _inherit = ['mail.thread']
    _description = "Containers for trips purpose is to aggregate accounting costs and revenue"

    name = fields.Char("Super Trip Number", readonly=True)
    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', string="Analytic Account",
                                          required=False, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.company)
    trips = fields.One2many(comodel_name='project.project', inverse_name='super_trip', string='Trips', required=False,
                            ondelete='cascade')

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals in vals_list:
            company_value = vals.get('company_id', False)
            if not company_value: company_value = self.env.company.id
            plan = self.determine_analytic_plan()
            trip_number = self.generate_sequence(company_value)
            account = self.env["account.analytic.account"].create({
                "name": trip_number,
                "plan_id": plan.value,
                "root_plan_id": plan.value
            })
            vals['analytic_account_id'] = account.id
            vals['name'] = trip_number
            new_vals_list.append(vals)
        return super().create([vals for vals in new_vals_list])

    def generate_sequence(self, company):
        sequence = self.env['ir.sequence'].search(
            [('company_id', '=', company), ('code', 'in', SEQUENCE_CODES)], limit=1)
        try:
            return sequence.next_by_id()
        except Exception:
            raise UserError(f"{self.env.company.name} has no sequence!")

    def determine_analytic_plan(self):
        return self.env.ref("velocity.velocity_super_trips_plan")


class Project(models.Model):
    _inherit = 'project.project'

    name = fields.Char("Name", index='trigram', readonly=False, required=False, tracking=True, translate=True,
                       default_export_compatible=True)
    super_trip = fields.Many2one("velocity.super_trip", "Super Trip", required=False)
    cd3_number = fields.Char("CD3 Number")
    currency = fields.Many2one("res.currency", "Billing Currency", readonly=False,
                               default=lambda self: self.company_id.currency_id.id)
    cd3_amount = fields.Float("CD3 Amount", compute="_compute_cd3_amount")
    clearing_customer = fields.Many2one("res.partner", "Receiving Customer")
    supplier = fields.Many2one("res.partner", "Supplier", required=False)
    # partner_id = fields.Many2one("res.partner", "Customer", required=False)
    d_note = fields.Char("D Note")
    generated_from_super_trip = fields.Boolean("Generated From Super Trip", default=False, )
    date_start = fields.Date("Start Date", required=False,
                             default=fields.Date.today())
    date = fields.Date("End Date", required=False, default=fields.Date.today())
    end_date = fields.Date("End Date", required=False, default=fields.Date.today())
    shortage_deduction = fields.Float(
        "Shortage Deduction", compute="_compute_shortage_deduction")
    vehicle = fields.Many2one("fleet.vehicle", "Vehicle")
    driver = fields.Many2one("hr.employee", "Driver")
    product = fields.Many2one("product.product",
                              "Product")  # , default=lambda self: self.env.ref('velocity.velocity_transportation_service')
    good = fields.Many2one("velocity.product", "Good")
    _good = fields.Char("Good")
    good_quantity = fields.Float("Capacity")
    good_price = fields.Float("Price Per Ton")
    supplier_invoice = fields.Char("Supplier Invoice")
    supplier_invoice_value = fields.Float("Supplier Invoice Value", compute="_compute_supplier_invoice_value")
    route = fields.Many2one("velocity.route", "Route")
    route_distance = fields.Float("Route Distance (km)", related='route.route_distance', readonly=True)
    loading_point = fields.Char("Loading Point")
    offloading_point = fields.Char("Offloading Point")
    loading_quantity = fields.Float("Loading Quantity")
    date_arrived_at_loading = fields.Date("Date Arrived At Loading")
    load_date = fields.Date("Load Date")
    date_arrived_at_offloading = fields.Date("Date Arrived At Offloading")
    offload_date = fields.Date("Offload Date")
    quantity_loaded = fields.Float("Quantity Loaded")
    quantity_offloaded = fields.Float("Quantity Offloaded")
    quantity_difference = fields.Float(
        "Shortage", compute="_compute_quantity_difference")
    transport_invoice = fields.Many2one("account.move", "Transport Invoice")
    clearing_invoice = fields.Many2one("account.move", "Clearing Invoice")
    loading_first_weight = fields.Float("Loading First Weight")
    loading_second_weight = fields.Float("Loading Second Weight")
    loading_net_weight = fields.Float(
        "Loading Net Weight", compute="_compute_loading_net_weight")
    offloading_first_weight = fields.Float("Offloading First Weight")
    offloading_second_weight = fields.Float("Offloading Second Weight")
    offloading_net_weight = fields.Float(
        "Offloading Net Weight", compute="_compute_offloading_net_weight")

    road_manifest = fields.Char("Road Manifest")
    cd3_rate = fields.Float("CD3 Rate")
    route_rate = fields.Float("Route Rate", readonly=False)
    transport_invoice_value = fields.Float("Transport Invoice Value", compute="_compute_transport_invoice_value")

    _sql_constraints = [
        ('name_uniq',
         'unique (name)',
         'Each trip should have a unique trip number!')
    ]

    def unlink(self):
        for record in self:
            if record.transport_invoice:
                raise UserError("You cannot delete an invoiced trip!")
            if record.end_date:
                raise UserError("You cannot delete a trip that has been completed!")
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals_index, vals in enumerate(vals_list):
            super_trip_value = vals.get('super_trip', False)
            company_value = vals.get('company_id', False)
            if not company_value: company_value = self.env.company.id
            trip_number = self.generate_sequence(
                company_value) if not super_trip_value else self.generate_subsequence(super_trip_value,
                                                                                      vals_index)
            if not super_trip_value:
                plan = self.determine_analytic_plan(vals['company_id'])
                account = self.env["account.analytic.account"].create({
                    "name": trip_number,
                    "plan_id": plan.value,
                    "root_plan_id": plan.value
                })
                vals['analytic_account_id'] = account.id
            else:
                vals['analytic_account_id'] = self._get_analytic_from_super_trip(super_trip_value)
            vals['name'] = trip_number
            vals['end_date'] = False
            new_vals_list.append(vals)
        return super().create([vals for vals in new_vals_list])

    def generate_sequence(self, company):
        sequence = self.env['ir.sequence'].search(
            [('company_id', '=', company), ('code', 'in', SEQUENCE_CODES)], limit=1)
        try:
            return sequence.next_by_id()
        except Exception:
            raise UserError(f"{self.env.company.name} has no sequence!")

    def generate_subsequence(self, super_trip, increase_by):
        super_trip = self.env['velocity.super_trip'].browse(int(super_trip))
        trip_suffix = len(super_trip.trips) + increase_by + 1
        return f"{super_trip.name}-{trip_suffix}"

    def _get_analytic_from_super_trip(self, super_trip):
        super_trip = self.env['velocity.super_trip'].browse(int(super_trip))
        return super_trip.analytic_account_id.id

    def determine_analytic_plan(self, company):
        return self.env.ref("velocity.velocity_trips_plan")

    # @api.constrains('name')
    # def _check_name(self):
    #     pattern = r'VL-\d{2}-\d{4}$'
    #     for record in self:
    #         if not re.match(pattern, record.name):
    #             raise UserError(
    #                 "Trip number should be in the sequence VL-{current year}-{4 digit number} i.e. VL-24-0000")

    @api.constrains('date_start', 'end_date', 'load_date', 'offload_date', 'date_arrived_at_loading',
                    'date_arrived_at_offloading')
    def _check_dates(self):
        for rec in self:
            # Rule 1: Start date must be less than or equal to end date
            if rec.date_start and rec.end_date:
                if rec.date_start > rec.end_date:
                    raise UserError("Start date cannot be after end date.")

            # Rule 2: Offloading date must be greater than loading date
            if rec.offload_date and rec.load_date:
                if rec.offload_date < rec.load_date:
                    raise UserError("Offloading date cannot be before loading date.")

            # Rule 3: Loading date must be between start date and end date
            if rec.date_start and rec.load_date and rec.offload_date:
                if not (rec.date_start <= rec.load_date and rec.date_start <= rec.offload_date):
                    raise UserError("Load date must be between start date and end date.")

            # Rule 4: offloading date must be between start date and end date
            if rec.end_date and rec.load_date and rec.offload_date:
                if not (rec.load_date <= rec.end_date and rec.offload_date <= rec.end_date):
                    raise UserError("offload date must be between start date and end date.")

            # Rule 5: Offloading date must be after date arrived at offloading
            if rec.offload_date and rec.date_arrived_at_offloading:
                if rec.offload_date < rec.date_arrived_at_offloading:
                    raise UserError("Offloading date cannot be before date arrived at offloading.")

            # Rule 6: Loading date must be after date arrived at loading
            if rec.load_date and rec.date_arrived_at_loading:
                if rec.load_date < rec.date_arrived_at_loading:
                    raise UserError("Loading date cannot be before date arrived at loading.")

            # Rule 7: Date arrived at offloading must be between start date and end date
            if rec.date_start and rec.end_date and rec.date_arrived_at_offloading:
                if not (rec.date_start <= rec.date_arrived_at_offloading <= rec.end_date):
                    raise UserError("Date arrived at offloading must be between start date and end date.")

            # Rule 8: Date arrived at loading must be between start date and end date
            if rec.date_start and rec.end_date and rec.date_arrived_at_loading:
                if not (rec.date_start <= rec.date_arrived_at_loading <= rec.end_date):
                    raise UserError("Date arrived at loading must be between start date and end date.")

    @api.depends('loading_net_weight', 'offloading_net_weight')
    def _compute_quantity_difference(self):
        for record in self:
            record.quantity_difference = record.offloading_net_weight - \
                                         record.loading_net_weight

    @api.depends('loading_first_weight', 'loading_second_weight')
    def _compute_loading_net_weight(self):
        for record in self:
            record.loading_net_weight = record.loading_second_weight - record.loading_first_weight

    @api.depends('offloading_first_weight', 'offloading_second_weight')
    def _compute_offloading_net_weight(self):
        for record in self:
            record.offloading_net_weight = record.offloading_first_weight - record.offloading_second_weight

    @api.depends('good_price', 'loading_net_weight')
    def _compute_supplier_invoice_value(self):
        for rec in self:
            rec.supplier_invoice_value = (rec.good_price * rec.loading_net_weight) / 1000

    @api.onchange('route', 'date_start')
    def _onchange_route(self):
        if self.route and self.date_start and self.route.average_days_to_complete_trip > 0:
            self.date = self.date_start + \
                        timedelta(days=self.route.average_days_to_complete_trip)
            self.route_distance = self.route.route_distance
            self.route_rate = self.route.route_rate

    @api.onchange('vehicle')
    def _onchange_vehicle(self):
        if self.vehicle:
            self.driver = self.vehicle.driver

    @api.depends('quantity_difference', '_good')
    def _compute_shortage_deduction(self):
        for rec in self:
            if rec.quantity_difference < -100:
                rec.shortage_deduction = abs(rec.quantity_difference + 100) * (rec.good_price / 1000)
            else:
                rec.shortage_deduction = 0

    @api.depends('loading_net_weight', 'cd3_rate')
    def _compute_cd3_amount(self):
        for rec in self:
            rec.cd3_amount = (rec.loading_net_weight * rec.cd3_rate) / 1000

    @api.depends('loading_net_weight', 'route_rate')
    def _compute_transport_invoice_value(self):
        for rec in self:
            rec.transport_invoice_value = (rec.route_rate * rec.loading_net_weight) / 1000

    def generate_invoice(self):
        if not self.quantity_loaded:
            raise UserError("Quantity loaded not set!")
        if not self.partner_id:
            raise UserError("Please specify the customer!")
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': self.date_start or fields.Date.today(),
            'currency_id': self.currency_id.id or self.env.company.currency_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': self.loading_net_weight,
                'price_unit': self.route_rate,
                'name': self.product.name
            })]
        })
        invoice.action_post()
        # self.supplier_invoice = invoice


class ProjectVehicle(models.Model):
    _inherit = "fleet.vehicle"

    fleet_number = fields.Char("Fleet Number")
    horse_reg = fields.Char("Horse Reg")
    tanker_reg = fields.Char("Tanker Reg")
    analytic_account_id = fields.Many2one(
        "account.analytic.account", "Analytical Account")

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals in vals_list:
            plan = self.determine_analytic_plan(vals['company_id'])
            account = self.env["account.analytic.account"].create({
                "name": vals['fleet_number'],
                "plan_id": plan.value,
                "root_plan_id": plan.value
            })
            vals['analytic_account_id'] = account.id
            new_vals_list.append(vals)
        return super().create([vals for vals in new_vals_list])

    def determine_analytic_plan(self, company):
        if not company: raise UserError(f"This vehicle needs to be tagged to a company!")
        velocity_liquid = self.env.ref("velocity.velocity_liquid_company_id")
        if company == velocity_liquid.id:
            return self.env.ref("velocity.velocity_vehicle_plan")
        else:
            return self.env.ref("velocity.velocity_truck_plan")


class ProjectProduct(models.Model):
    _name = "velocity.product"

    name = fields.Char("Name")
    price = fields.Float("Unit Price", required=False)
    uom = fields.Many2one("uom.uom", string="Unit of Measure",
                          required=False)  # , default=lambda self: self.env.ref("uom.product_uom_ton")


class ProjectFleet(models.Model):
    _inherit = "fleet.vehicle"

    driver = fields.Many2one("hr.employee", string="Driver", required=False)
    asset = fields.Many2one("velocity.fleet_asset", string="Asset", required=False)

    @api.onchange("asset")
    def _onchange_asset(self):
        if self.asset.vehicle:
            raise UserError(
                f"{self.asset.type.capitalize()} {self.asset.name} is already assigned to vehicle: {self.asset.vehicle.fleet_number}")


class ProjectFleetAsset(models.Model):
    _name = "velocity.fleet_asset"
    _description = "Fleet asset such as trailer or tankers that are movable between vehicles"

    name = fields.Char("Asset Number", required=True)
    type = fields.Selection([('trailer', 'Trailer'), ('tanker', 'Tanker')], default="trailer", required=True)
    vehicle = fields.One2many('fleet.vehicle', 'asset')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)



class ProjectRoutes(models.Model):
    _name = "velocity.route"

    name = fields.Char("Route Name", compute="_compute_route")
    route_start = fields.Char("Route Start")
    route_end = fields.Char("Route End")
    route_distance = fields.Float("Route Distance")
    route_rate = fields.Float("Route Rate")
    average_days_to_complete_trip = fields.Float("Days To Complete")

    @api.depends("route_start", "route_end")
    def _compute_route(self):
        for rec in self:
            if rec.route_end and rec.route_start:
                rec.name = f"{rec.route_start} - {rec.route_end}"
            else:
                rec.name = ""


class AnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    vehicle = fields.One2many(
        comodel_name='fleet.vehicle',
        inverse_name='analytic_account_id',
        string='Vehicle',
        required=False,
    )
