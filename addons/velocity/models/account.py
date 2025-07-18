# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class InvoiceTrip(models.TransientModel):
    _name = "velocity.invoice_trip"

    service = fields.Many2one("product.product", "Service",
                              help="Make sure that you select the correct service for clearing and transportation. The system is unable to identify if a specific service is for clearing or not!")
    customer = fields.Many2one("res.partner", "Customer")
    journal = fields.Many2one("account.journal", "Journal")
    is_clearing = fields.Boolean("Is for Clearing", default=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    trips = fields.Many2many(
        "project.project", "invoice_trip_project_rel", "id", string="Trips", domain="[('company_id', '=', company_id)]")

    def generate_invoice(self):
        lines = []
        trips = []
        for trip in self.trips:
            if trip.partner_id.id != self.customer.id and not self.is_clearing:
                raise UserError(
                    f"Trip: {trip.name} does not belong to customer: {self.customer.name}. It belongs to {trip.partner_id.name}.")
            clearing_customer = trip.clearing_customer or trip.partner_id
            if clearing_customer.id != self.customer.id and self.is_clearing:
                raise UserError(
                    f"Trip: {trip.name} does not belong to clearing customer: {self.customer.name} It belongs to {clearing_customer.name}.")
            if self.is_clearing and trip.clearing_invoice:
                raise UserError(
                    f"Trip {trip.name} already has a clearing invoice.")
            if not self.is_clearing and trip.transport_invoice:
                raise UserError(
                    f"Trip {trip.name} already has a transportation invoice.")

            lines.append((0, 0, {
                "product_id": self.service.id,
                "quantity": trip.loading_net_weight / 1000,
                "name": f"{self.service.name}\n{trip.name} {trip.route.name}",
                "description": f"{self.service.name}<br/>{trip.name} {trip.route.name}",
                "price_unit": trip.route_rate,
                "trip": trip.id,
                "analytic_distribution": {trip.analytic_account_id.id: 100, trip.vehicle.analytic_account_id.id: 100},
            }))
            trips.append(trip)

        invoice = self.env["account.move"].create({
            "partner_id": self.customer.id,
            "currency_id": trip.currency_id.id,
            "invoice_date": fields.Date.today(),
            "journal_id": self.journal.id,
            "invoice_line_ids": lines,
            "move_type": "out_invoice"
        })

        invoice.action_post()

        for trip in trips:
            if self.is_clearing:
                trip.clearing_invoice = invoice
            else:
                trip.transport_invoice = invoice


class JournalItem(models.Model):
    _inherit = "account.move.line"

    trip = fields.Many2one('project.project', "Trip")
    company_id = fields.Many2one(
        related='move_id.company_id', store=True, readonly=False, precompute=True,
        index=True,
    )

    @api.onchange("trip")
    def _compute_vehicle_analytic(self):
        for rec in self:
            try:
                trip_analytic = rec.trip.analytic_account_id
                vehicle_analytic = self.env['account.analytic.account'].browse([rec.trip.vehicle.analytic_account_id.id])
                if not vehicle_analytic: raise UserError(f"{rec.trip.vehicle.fleet_number} has no analytical account!")
                analytic = {f"{trip_analytic.id},{vehicle_analytic.id}": 100}
                rec.analytic_distribution = analytic
            except:
                continue

class Account(models.Model):
    _inherit = "account.move"
    
    amount_in_words = fields.Char("Amount In Words")
    is_transportation = fields.Boolean("Is Transportation Invoice", default=True)

    @api.onchange("state")
    def _compute_state(self):
        for rec in self:
            for line in rec.invoice_line_ids:
                line._compute_vehicle_analytic()
    
    
class InvoiceLine(models.Model):
    _inherit = "account.move.line"
    
    trip = fields.Many2one('project.project', "Trip")
    description = fields.Html("Description")
    
    # _sql_constraints = [
    #     ('trip_uniq',
    #      'unique (trip,product_id,account_id)',
    #      'Each trip can be invoiced wants per service per income account!')
    # ]
    
    @api.onchange("trip")
    def _compute_quantity(self):
        for rec in self:
            rec.quantity = rec.trip.loading_net_weight / 1000
            
    @api.onchange("trip")
    def _compute_price_unit(self):
        for rec in self:
            rec.price_unit = rec.trip.route_rate
    
    @api.onchange("trip")
    def _compute_label(self):
        for rec in self:
            rec.name = f"{rec.product_id.name}\n{rec.trip.name} {rec.trip.route.name}"
    
    @api.onchange("trip")
    def _compute_description(self):
        for rec in self:
            rec.description = f"{rec.product_id.name}<br/>{rec.trip.name} {rec.trip.route.name}"



# because we had no guard on re select it removed analytics for those trips without trip colunm
# records = env['project.project'].search([])
# for record in records:
#     transport_invoice = record.transport_invoice
#     if transport_invoice:
#         for line in transport_invoice.invoice_line_ids:
#             try:
#                 is_false = 'False,False' in list(line.analytic_distribution.keys())
#                 if not line.trip and is_false:
#                     if record.name in line.name:
#                         line.write({
#                             "trip": record.id
#                         })
#             except:
#                 continue
    
    @api.onchange("trip")
    def _compute_vehicle_analytic(self):
        for rec in self:
            if not rec.trip: continue
            try:
                if 'False,False' not in list(rec.analytic_distribution.keys()): continue
            except:
                pass
            try:
                trip_analytic = rec.trip.analytic_account_id
                vehicle_analytic = self.env['account.analytic.account'].browse([rec.trip.vehicle.analytic_account_id.id])
                if not vehicle_analytic: raise UserError(f"{rec.trip.vehicle.fleet_number} has no analytical account!")
                analytic = {f"{trip_analytic.id},{vehicle_analytic.id}": 100}
                rec.analytic_distribution = analytic
            except:
                continue
