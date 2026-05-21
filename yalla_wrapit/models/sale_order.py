from odoo import models, fields,api
import json

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_material_cost = fields.Float(string="Material Cost")
    total_labour_cost = fields.Float(string="Labour Cost")
    total_cost = fields.Float(string="Total Cost")


