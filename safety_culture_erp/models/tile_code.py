from odoo import models, fields, api

class YallaWrapTileCode(models.Model):
    _name = 'yallawrap.tile.code'
    _description = 'YallaWrap Tile Codes'
    _rec_name = 'code'

    code = fields.Char(string="Code Number", required=True)
    description = fields.Char(string="Description")
    current_stock = fields.Integer(string="Current Stock (Packs)")
    qty_per_pack = fields.Integer(string="Quantity Per Pack", default=10)

    total_pieces_available = fields.Integer(
        string="Total Pieces Available",
        compute="_compute_total_pieces",
        store=True
    )
    price_type = fields.Selection([
        ('meter', 'Per Meter'),
        ('roll', 'Per Roll')
    ], string="Price Type", default='roll')
    price_per_meter = fields.Float(string="Price per Meter", default=0)
    price_per_roll = fields.Float(string="Price per Roll", default=0)
    price = fields.Float(string="price per Piece",compute="_compute_price",
    store=True)
    @api.depends('price_per_meter')
    def _compute_price(self):
        for rec in self:
            rec.price = rec.price_per_meter

    @api.depends('current_stock', 'qty_per_pack')
    def _compute_total_pieces(self):
        for rec in self:
            rec.total_pieces_available = rec.current_stock * rec.qty_per_pack
