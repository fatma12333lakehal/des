# -*- coding: utf-8 -*-
from odoo import models, fields, api


# ========================================
# CRM Lead Extended
# ========================================
class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _description = 'Lead / Opportunity Extended for YallaWrap'

    report_name = fields.Char(string="Report Reference", required=True, tracking=True)
    prepared_by = fields.Char(string="Prepared By")
    location = fields.Char(string="Location")
    conducted_on = fields.Datetime(string="Conducted On")
    client_id = fields.Many2one('res.partner', string="Client", required=True)
    notes = fields.Text(string="Additional Notes")

    # Inspection relations
    kitchen_ids = fields.One2many('yallawrap.kitchen', 'lead_id', string="Kitchen Inspections")
    bathroom_ids = fields.One2many('yallawrap.bathroom', 'lead_id', string="Bathroom Inspections")
    wardrobe_ids = fields.One2many('yallawrap.wardrobe', 'lead_id', string="Wardrobe Inspections")
    door_ids = fields.One2many('yallawrap.door', 'lead_id', string="Door Inspections")
    flooring_ids = fields.One2many('yallawrap.flooring', 'lead_id', string="Flooring")
    window_frame_ids = fields.One2many('yallawrap.window.frame', 'lead_id', string="Window Frames")
    furniture_ids = fields.One2many('yallawrap.furniture', 'lead_id', string="Furniture")
    skirting_ids = fields.One2many('skirting.material', 'lead_id', string="Furniture")

    def action_print_report(self):
        return self.env.ref('yalla_wrapit.action_yallawrap_master_inspection_report').report_action(self)

    # ========================================
    # Labour Cost Fields
    # ========================================

    labor_cost_per_day = fields.Float(
        string="Labour Cost / Day",
        default=550.0,
        help="Cost per worker per day (configurable)"
    )

    labor_workers = fields.Integer(
        string="Number of Workers",
        default=1
    )

    labor_days = fields.Float(
        string="Duration (Days)",
        default=1
    )

    labor_total = fields.Float(
        string="Total Labour Cost",
        compute="_compute_financials",
        store=True
    )

    # ========================================
    # Material + Total + Margin
    # ========================================

    material_total = fields.Float(
        string="Material Cost",
        compute="_compute_financials",
        store=True
    )

    total_cost = fields.Float(
        string="Total Cost",
        compute="_compute_financials",
        store=True
    )

    margin_percent = fields.Float(
        string="Margin (%)",
        default=40.0
    )

    final_price = fields.Float(
        string="Final Selling Price",
        compute="_compute_financials",
        store=True)

    @api.depends(
        'kitchen_ids', 'bathroom_ids', 'wardrobe_ids',
        'door_ids', 'window_frame_ids', 'furniture_ids',
        'skirting_ids', 'flooring_ids'
    )
    def _compute_financials(self):
        for rec in self:

            def compute_line(meters, labour, material):
                meters = meters or 0.0
                labour = labour or 0.0
                material = material or 0.0
                return meters * (labour + material)

            total_cost = 0.0

            # =========================
            # KITCHEN
            # =========================
            for k in rec.kitchen_ids:
                total_cost += compute_line(k.kitchen_cabinet_meters, k.kitchen_cabinet_labour, k.kitchen_cabinet_price)
                total_cost += compute_line(k.kitchen_countertop_meters, k.kitchen_countertop_labour,
                                           k.kitchen_countertop_price)
                total_cost += compute_line(k.backsplash_countertop_meters, k.backsplash_countertop_labour,
                                           k.backsplash_countertop_price)

                for f in k.flooring_ids:
                    total_cost += compute_line(f.floor_meters, f.floor_labour, f.floor_price)

            # =========================
            # BATHROOM
            # =========================
            for b in rec.bathroom_ids:
                total_cost += compute_line(b.wall_meters, b.wall_labour, b.wall_price)
                total_cost += compute_line(b.countertop_meters, b.countertop_labour, b.countertop_price)
                total_cost += compute_line(b.cabinet_meters, b.cabinet_labour, b.cabinet_price)

                for f in b.flooring_ids:
                    total_cost += compute_line(f.floor_meters, f.floor_labour, f.floor_price)

            # =========================
            # OTHER SCOPES
            # =========================
            for w in rec.wardrobe_ids:
                total_cost += compute_line(w.wardrobe_meters, w.wardrobe_labour, w.wardrobe_price)

            for d in rec.door_ids:
                total_cost += compute_line(d.door_meters, d.door_labour, d.door_price)

            for wf in rec.window_frame_ids:
                total_cost += compute_line(wf.window_frame_meters, wf.window_frame_labour, wf.window_frame_price)

            for fu in rec.furniture_ids:
                total_cost += compute_line(fu.furniture_meters, fu.furniture_meters_labour, fu.furniture_price)

            for s in rec.skirting_ids:
                total_cost += compute_line(s.skirting_qty, 0.0, s.skirting_price)

            for f in rec.flooring_ids:
                total_cost += compute_line(f.floor_meters, f.floor_labour, f.floor_price)

            # =========================
            # FINAL
            # =========================
            rec.material_total = total_cost
            rec.total_cost = total_cost
            rec.final_price = total_cost / 0.6 if total_cost else 0.0

    def action_create_quotation(self):
        self.ensure_one()

        order = self.env['sale.order'].create({
            'partner_id': self.client_id.id,
            'origin': self.name,
            'opportunity_id': self.id,
        })

        lines = []

        # =========================
        # CORE FORMULA
        # =========================
        def compute_price_unit(labour, material):
            base = (labour or 0.0) + (material or 0.0)
            return base / 0.6 if base else 0.0

        def get_qty(qty, meters):
            return meters or qty or 0.0

        def add_section(title):
            lines.append((0, 0, {
                'display_type': 'line_section',
                'name': title,
            }))

        def add_line(scope, subtitle, code, qty, labour, material):
            if not code or not qty:
                return

            lines.append((0, 0, {
                'name': f"{scope} / {subtitle} ({code.code})",
                'product_uom_qty': qty,
                'price_unit': compute_price_unit(labour, material),
            }))

        # =========================
        # KITCHEN
        # =========================
        if self.kitchen_ids:
            add_section("KITCHEN")

            for k in self.kitchen_ids:
                add_line("Kitchen", "Cabinet",
                         k.kitchen_cabinet_code,
                         get_qty(k.kitchen_cabinet_qty, k.kitchen_cabinet_meters),
                         k.kitchen_cabinet_labour,
                         k.kitchen_cabinet_price)

                add_line("Kitchen", "Countertop",
                         k.kitchen_countertop_code,
                         get_qty(k.kitchen_countertop_qty, k.kitchen_countertop_meters),
                         k.kitchen_countertop_labour,
                         k.kitchen_countertop_price)

                add_line("Kitchen", "Backsplash",
                         k.backsplash_countertop_code,
                         get_qty(k.backsplash_countertop_qty, k.backsplash_countertop_meters),
                         k.backsplash_countertop_labour,
                         k.backsplash_countertop_price)

                for f in k.flooring_ids:
                    add_line("Kitchen", "Flooring",
                             f.floor_code,
                             get_qty(f.floor_qty, f.floor_meters),
                             f.floor_labour,
                             f.floor_price)

        # =========================
        # BATHROOM
        # =========================
        if self.bathroom_ids:
            add_section("BATHROOM")

            for b in self.bathroom_ids:
                add_line("Bathroom", "Wall",
                         b.wall_code,
                         get_qty(b.wall_qty, b.wall_meters),
                         b.wall_labour,
                         b.wall_price)

                add_line("Bathroom", "Countertop",
                         b.countertop_code,
                         get_qty(b.countertop_qty, b.countertop_meters),
                         b.countertop_labour,
                         b.countertop_price)

                add_line("Bathroom", "Cabinet",
                         b.cabinet_code,
                         get_qty(b.cabinet_qty, b.cabinet_meters),
                         b.cabinet_labour,
                         b.cabinet_price)

                for f in b.flooring_ids:
                    add_line("Bathroom", "Flooring",
                             f.floor_code,
                             get_qty(f.floor_qty, f.floor_meters),
                             f.floor_labour,
                             f.floor_price)

        # =========================
        # WARDROBES
        # =========================
        if self.wardrobe_ids:
            add_section("WARDROBES")

            for r in self.wardrobe_ids:
                add_line("Wardrobe", "Installation",
                         r.wardrobe_code,
                         get_qty(r.wardrobe_qty, r.wardrobe_meters),
                         r.wardrobe_labour,
                         r.wardrobe_price)

        # =========================
        # DOORS
        # =========================
        if self.door_ids:
            add_section("DOORS")

            for r in self.door_ids:
                add_line("Door", "Installation",
                         r.door_code,
                         get_qty(r.door_qty, r.door_meters),
                         r.door_labour,
                         r.door_price)

        # =========================
        # WINDOWS
        # =========================
        if self.window_frame_ids:
            add_section("WINDOWS")

            for r in self.window_frame_ids:
                add_line("Window", "Frame",
                         r.window_frame_code,
                         get_qty(r.window_frame_qty, r.window_frame_meters),
                         r.window_frame_labour,
                         r.window_frame_price)

        # =========================
        # FURNITURE
        # =========================
        if self.furniture_ids:
            add_section("FURNITURE")

            for r in self.furniture_ids:
                add_line("Furniture", "Item",
                         r.furniture_code,
                         get_qty(r.furniture_qty, r.furniture_meters),
                         r.furniture_meters_labour,
                         r.furniture_price)

        # =========================
        # FLOORING
        # =========================
        if self.flooring_ids:
            add_section("FLOORING")

            for r in self.flooring_ids:
                add_line("Flooring", "Work",
                         r.floor_code,
                         get_qty(r.floor_qty, r.floor_meters),
                         r.floor_labour,
                         r.floor_price)

        # =========================
        # SKIRTING
        # =========================
        if self.skirting_ids:
            add_section("SKIRTING")

            for s in self.skirting_ids:
                add_line("Skirting", "Installation",
                         s.skirting_code,
                         s.skirting_qty or 0.0,
                         0.0,
                         s.skirting_price)

        order.order_line = lines

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': order.id,
        }
    @api.onchange('client_id')
    def _onchange_client_id(self):
        """Automatically set the location based on the selected client."""
        if self.client_id:
            self.location = self.client_id.city or self.client_id.state_id.name or ''
        else:
            self.location = ''
    def action_print_master_inspection_report(self):
        return self.env.ref(
            "yallawrap_inspection.action_yallawrap_master_inspection_report"
        ).report_action(self)

class YallaWrapKitchen(models.Model):
    _name = 'yallawrap.kitchen'
    _description = 'Kitchen Inspection'

    # =========================
    # Relations
    # =========================

    lead_id = fields.Many2one(
        'crm.lead',
        string="Lead"
    )

    flooring_ids = fields.One2many(
        'yallawrap.flooring',
        'kitchen_id',
        string="Flooring for Kitchen"
    )

    # =========================
    # Kitchen Cabinet
    # =========================

    kitchen_cabinet_code = fields.Many2one(
        'yallawrap.tile.code',
        string="Cabinet  Code"
    )

    kitchen_cabinet_qty = fields.Float(
        string="Quantity",
        default=0.0
    )

    kitchen_cabinet_type = fields.Selection([
        ('one_side', 'One Side'),
        ('both_sides', 'Both Sides'),
        ('with_leveling', 'With Leveling'),
        ('no_leveling', 'No Leveling (Flat)'),
        ('keep_design', 'Keep Design'),
        ('break_design', 'Break the Design'),
        ('carcasses', 'Carcasses')
    ], string="Cabinet Type")

    kitchen_cabinet_width = fields.Float(
        string="Width "
    )

    kitchen_cabinet_height = fields.Float(
        string="Height "
    )

    kitchen_cabinet_meters = fields.Float(
        string="Meters for BOQ Calculator"
    )
    kitchen_cabinet_labour = fields.Monetary(
        string="Labour Rate ", currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )
    kitchen_cabinet_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")

    kitchen_cabinet_price = fields.Float(
        string="Cabinet Price",
        compute="_compute_kitchen_cabinet_price",
        store=True
    )

    @api.depends('kitchen_cabinet_code')
    def _compute_kitchen_cabinet_price(self):
        for rec in self:
            rec.kitchen_cabinet_price = rec.kitchen_cabinet_code.price_per_meter if rec.kitchen_cabinet_code else 0.0
    kitchen_cabinet_cleaning = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A')
    ], string="Cleaning Needed")

    kitchen_cabinet_peeled_off = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string="Peeled Off")

    kitchen_cabinet_hard_frame = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A')
    ], string="Hard Frame")

    kitchen_cabinet_free_handles = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A')
    ], string="Free Handles")

    kitchen_cabinet_change_handles_size = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A')
    ], string="Change Handles Size")
    kitchen_attachment_ids = fields.Many2many(
        'ir.attachment',
        'kitchen_attachment_rel',
        'kitchen_id',
        'attachment_id',
        string="Attachments"
    )
    formula_kitchen= fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula ."
    )
    # =========================
    # Kitchen Countertop
    # =========================

    kitchen_countertop_code = fields.Many2one(
        'yallawrap.tile.code',
        string="Countertop Material (Optional)"
    )

    kitchen_countertop_qty = fields.Float(
        string="Quantity",
        default=0.0
    )

    kitchen_countertop_width = fields.Float(
        string="Width (Optional)"
    )

    kitchen_countertop_height = fields.Float(
        string="Height (Optional)"
    )

    kitchen_countertop_meters = fields.Float(
        string="Meters for BOQ Calculator"
    )
    kitchen_countertop_labour = fields.Monetary(
        string="Labour Rate"
        , currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )
    kitchen_countertop_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")
    kitchen_countertop_price = fields.Float(
        string="Cabinet Price",
        compute="_compute_kitchen_countertop_price",
        store=True
    )
    @api.depends('kitchen_countertop_code')
    def _compute_kitchen_countertop_price(self):
        for rec in self:
            rec.kitchen_countertop_price = (
                rec.kitchen_countertop_code.price_per_meter
                if rec.kitchen_countertop_code else 0.0
            )


    kitchen_countertop_condition = fields.Selection([
        ('good', 'Good Condition'),
        ('bad', 'Bad Condition')
    ], string="Condition")

    kitchen_countertop_condition_notes = fields.Text(
        string="Condition Notes (Optional)"
    )
    kitchen_countertop_attachment_ids = fields.Many2many(
        'ir.attachment',
        'kitchen_countertop_attachment_rel',
        'kitchen_countertop_id',
        'attachment_id',
        string="Attachments"
    )

    formula_countertop= fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )

    backsplash_countertop_code = fields.Many2one(
        'yallawrap.tile.code',
        string="Countertop Material (Optional)"
    )

    backsplash_countertop_qty = fields.Float(
        string="Quantity",
        default=0.0
    )

    backsplash_countertop_width = fields.Float(
        string="Width (Optional)"
    )

    backsplash_countertop_height = fields.Float(
        string="Height (Optional)"
    )

    backsplash_countertop_meters = fields.Float(
        string="Meters for BOQ Calculator")

    backsplash_countertop_labour = fields.Monetary(
        string="Labour Rate"
        , currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )
    backsplash_countertop_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")
    backsplash_countertop_price = fields.Float(
        string="Cabinet Price",
        compute="_compute_backsplash_price",
        store=True
    )
    @api.depends('backsplash_countertop_code')
    def _compute_backsplash_price(self):
        for rec in self:
            rec.backsplash_countertop_price = (
                rec.backsplash_countertop_code.price_per_meter
                if rec.backsplash_countertop_code else 0.0
            )
    backsplash_countertop_attachment_ids = fields.Many2many(
        'ir.attachment',
        'backsplash_countertop_attachment_rel',
        'backsplash_countertop_id',
        'attachment_id',
        string="Attachments"
    )


    backsplash_wall = fields.Selection([
        ('with_leveling', 'Requires Leveling'),
        ('no_leveling', 'No Leveling Required'),
        ('break_design', 'Break Existing Design'),
    ], string="Condition")

    formula_backsplash= fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )


# ========================================
# Bathroom Inspection
# ========================================
class YallaWrapBathroom(models.Model):
    _name = 'yallawrap.bathroom'
    _description = 'Bathroom Inspection'

    lead_id = fields.Many2one('crm.lead', string="Lead")
    name = fields.Selection([
        ('bathroom_1', 'Bathroom 1'),
        ('bathroom_2', 'Bathroom 2'),
        ('bathroom_3', 'Bathroom 3'),
        ('bathroom_4', 'Bathroom 4'),
        ('bathroom_5', 'Bathroom 5'),
        ('guest', 'Guest Bathroom'),
        ('kids', 'Kids Bathroom'),
        ('master', 'Master Bathroom'),
        ('other', 'Other Bathroom'),
    ], string="Name of Bathroom", tracking=True)

    wall_code = fields.Many2one('yallawrap.tile.code', string="Wall Material (Optional)")
    wall_qty = fields.Float(default=0.0)
    wall_width = fields.Float(string="Width (Optional)")
    wall_height = fields.Float(string="Height (Optional)")
    wall_meters = fields.Float(string="Meters for BOQ Calculator")
    wall_labour = fields.Monetary(
        string="Labour Rate"
        , currency_field='currency_id')

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )
    wall_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")
    wall_price = fields.Float(
        string="Wall Price",
        compute="_compute_wall_price",
        store=True
    )
    wall_attachment_ids = fields.Many2many(
        'ir.attachment',
        'wall_attachment_rel',
        'wall_id',
        'attachment_id',
        string="Attachments"
    )

    @api.depends('wall_code')
    def _compute_wall_price(self):
        for rec in self:
            rec.wall_price = (
                rec.wall_code.price_per_meter
                if rec.wall_code else 0.0
            )
    wall_type = fields.Selection([
        ('one_side', 'One Side'),
        ('both_sides', 'Both Sides'),
        ('with_leveling', 'With Leveling'),
        ('no_leveling', 'No Leveling'),
        ('keep_design', 'Keep Design'),
        ('break_design', 'Break Design'),
        ('carcasses', 'Carcasses')
    ], string="Cabinet Type")
    formula_wall = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )
    floor_code = fields.Many2one('yallawrap.tile.code', string="Floor Material (Optional)")
    floor_qty = fields.Float(default=0.0)
    floor_width = fields.Float(string="Width (Optional)")
    floor_height = fields.Float(string="Height (Optional)")
    floor_meters = fields.Float(string="Meters for BOQ Calculator")
    floor_labour = fields.Monetary(
        string="Labour Rate"
        , currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )
    flooring_ids = fields.One2many(
        'yallawrap.flooring',
        'bathroom_id',
        string="Flooring for Kitchen"
    )
    formula_floor = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )

    countertop_code = fields.Many2one('yallawrap.tile.code', string="Countertop Material (Optional)")
    countertop_qty = fields.Float(default=0.0)
    countertop_width = fields.Float(string="Width (Optional)")
    countertop_height = fields.Float(string="Height (Optional)")
    countertop_meters = fields.Float(string="Meters for BOQ Calculator")
    countertop_labour = fields.Monetary(
        string="Labour Rate", currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )

    countertop_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")
    countertop_price = fields.Float(
        string="Countertop Price",
        compute="_compute_countertop_price",
        store=True
    )
    countertop_attachment_ids = fields.Many2many(
        'ir.attachment',
        'countertop_attachment_rel',
        'countertop_id',
        'attachment_id',
        string="Attachments"
    )
    formula_countertop = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )
    @api.depends('countertop_code')
    def _compute_countertop_price(self):
        for rec in self:
            rec.countertop_price = (
                rec.countertop_code.price_per_meter
                if rec.countertop_code else 0.0
            )
    countertop_condition = fields.Selection([('good', 'Good Condition'), ('bad', 'Bad Condition')])
    countertop_condition_notes = fields.Text(string="Condition Notes (Optional)")

    cabinet_code = fields.Many2one('yallawrap.tile.code', string="Cabinet Material (Optional)")
    cabinet_qty = fields.Float(default=0.0)
    cabinet_width = fields.Float(string="Width (Optional)")
    cabinet_height = fields.Float(string="Height (Optional)")
    cabinet_meters = fields.Float(string="Meters for BOQ Calculator")
    cabinet_labour = fields.Monetary(
        string="Labour Rate"
        , currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )

    cabinet_attachment_ids = fields.Many2many(
        'ir.attachment',
        'cabinet_attachment_rel',
        'cabinet_id',
        'attachment_id',
        string="Attachments"
    )
    cabinet_type = fields.Selection([
        ('one_side', 'One Side'),
        ('both_sides', 'Both Sides'),
        ('with_leveling', 'With Leveling'),
        ('no_leveling', 'No Leveling'),
        ('keep_design', 'Keep Design'),
        ('break_design', 'Break Design'),
        ('carcasses', 'Carcasses')
    ], string="Cabinet Type")
    type = fields.Selection([
        ('removal_bathtub', 'Removal of Bathtub'),
        ('glass_partition', 'Glass Partition'),
        ('door_with', 'With Door'),
        ('door_without', 'Without Door'),
        ('replace_ceiling_tiles', 'Replacing of Ceiling Tiles'),
        ('replace_ceiling_gypsum', 'Replacement Ceiling to Gypsum'),
        ('replace_walls_tiles', 'Replacing of Walls Tiles'),
    ], string="Type")
    formula_cabinet = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula ."
    )

    bathroom_attachment_ids = fields.Many2many(
        'ir.attachment',
        'bathroom_attachment_rel',
        'bathroom_id',
        'attachment_id',
        string="Attachments"
    )
    cabinet_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")
    cabinet_price = fields.Float(
        string="Cabinet Price",
        compute="_compute_cabinet_price",
        store=True
    )

    @api.depends('cabinet_code')
    def _compute_cabinet_price(self):
        for rec in self:
            rec.cabinet_price = (
                rec.cabinet_code.price_per_meter
                if rec.cabinet_code else 0.0
            )
# ========================================
# Wardrobe Inspection
# ========================================
class YallaWrapWardrobe(models.Model):
    _name = 'yallawrap.wardrobe'
    _description = 'Wardrobe Inspection'

    lead_id = fields.Many2one('crm.lead', string="Lead")
    wardrobe_code = fields.Many2one('yallawrap.tile.code', string="Wardrobe Material (Optional)")
    wardrobe_qty = fields.Float(default=0.0)
    wardrobe_width = fields.Float(string="Width (Optional)")
    wardrobe_height = fields.Float(string="Height (Optional)")
    wardrobe_meters = fields.Float(string="Meters for BOQ Calculator")
    wardrobe_labour = fields.Monetary(
        string="Labour Rate"
        , currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )

    wardrobe_height_selection = fields.Selection([('full', 'Full 1 Section'), ('two', '2 Section')])
    wardrobe_needs_cutting = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('na', 'N/A')])
    wardrobe_price_type= fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")
    wardrobe_price = fields.Float(
        string="Wardrobe Price",
        compute="_compute_wardrobe_price",
        store=True
    )
    wardrobe_attachment_ids = fields.Many2many(
        'ir.attachment',
        'wardrobe_attachment_rel',
        'wardrobe_id',
        'attachment_id',
        string="Attachments"
    )
    formula_wardrobe = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )

    @api.depends('wardrobe_code')
    def _compute_wardrobe_price(self):
        for rec in self:
            rec.wardrobe_price = (
                rec.wardrobe_code.price_per_meter
                if rec.wardrobe_code else 0.0
            )

    Type_of_Shutter_Multiple_choice= fields.Selection([
        ('one_side', 'One Side'),
        ('both_sides', 'Both Sides'),
        ('with_leveling', 'With Leveling'),
        ('no_leveling', 'No Leveling'),
        ('keep_design', 'Keep Design'),
        ('break_design', 'Break Design'),
        ('carcasses', 'Carcasses')
    ], string="Type of shorter")
    shutter_height = fields.Selection([
        ('full_1_section', 'Full 1 Section'),
        ('two_section', '2 Section'),
    ], string="Height of Shutters", required=True)
    needs_cutting = fields.Selection([
    ('yes', 'Yes'),
    ('no', 'No'),
    ('na', 'N/A'),
], string="Needs Cutting / Trimming / Shortening")
    formula_wordable = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )
    wardrobe_attachment_ids = fields.Many2many(
        'ir.attachment',
        'wardrobe_attachment_rel',
        'wardrobe_id',
        'attachment_id',
        string="Attachments"
    )
# ========================================
# Door Inspection
# ========================================
class YallaWrapDoor(models.Model):
    _name = 'yallawrap.door'
    _description = 'Door Inspection'

    lead_id = fields.Many2one('crm.lead', string="Lead")
    door_code = fields.Many2one('yallawrap.tile.code', string="Door Material (Optional)")
    door_qty = fields.Float(default=0.0)
    door_width = fields.Float(string="Width (Optional)")
    door_height = fields.Float(string="Height (Optional)")
    door_meters = fields.Float(string="Meters for BOQ Calculator")
    door_labour = fields.Monetary(
        string="Labour Rate"
        , currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )
    Type_of_doors_Multiple_choice = fields.Selection([
        ('one_side', 'One Side'),
        ('both_sides', 'Both Sides'),
        ('with_leveling', 'With Leveling'),
        ('no_leveling', 'No Leveling'),
        ('keep_design', 'Keep Design'),
        ('break_design', 'Break Design'),
        ('carcasses', 'Carcasses')
    ], string="Type of shorter")

    door_needs_scaffolding_door = fields.Selection([('yes', 'Yes'), ('no', 'No')])
    door_needs_cutting = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('na', 'N/A')])
    door_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")
    door_price = fields.Float(
        string="Door Price",
        compute="_compute_door_price",
        store=True
    )
    door_attachment_ids = fields.Many2many(
        'ir.attachment',
        'door_attachment_rel',
        'door_id',
        'attachment_id',
        string="Attachments"
    )
    formula_door = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )
    @api.depends('door_code')
    def _compute_door_price(self):
        for rec in self:
            rec.door_price = rec.door_code.price_per_meter if rec.door_code else 0.0
    # =========================
    door_size = fields.Selection([
        ('standard', 'Standard'),
        ('double', 'Double'),
        ('sliding', 'Sliding'),
        ('big', 'Big Door'),
    ], string="Size of Door")

    # =========================
    # Needs Scaffolding
    # =========================
    needs_scaffolding_door = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Needs Scaffolding")

    # =========================
    # Needs Cutting
    # =========================
    needs_cutting_door = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A'),
    ], string="Needs Cutting / Trimming / Shortening")

# ========================================
# Flooring
# ========================================
class YallaWrapFlooring(models.Model):
    _name = 'yallawrap.flooring'
    _description = 'Flooring'

    lead_id = fields.Many2one('crm.lead', string="Lead")
    kitchen_id = fields.Many2one('yallawrap.kitchen', string="Kitchen (Optional)")
    bathroom_id = fields.Many2one('yallawrap.bathroom', string="Bathroom")
    floor_code = fields.Many2one('yallawrap.tile.code', string="Material (Optional)")
    floor_qty = fields.Float(default=0.0)
    floor_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")
    floor_meters = fields.Float(string="Meters for BOQ Calculator")
    floor_labour = fields.Monetary(
        string="Labour Rate"
        , currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )

    floor_price = fields.Float(
        string="Floor Price",
        compute="_compute_floor_price",
        store=True
    )
    floor_attachment_ids = fields.Many2many(
        'ir.attachment',
        'floor_attachment_rel',
        'floor_id',
        'attachment_id',
        string="Attachments"
    )
    formula_floor = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )

    @api.depends('floor_code')
    def _compute_floor_price(self):
        for rec in self:
            rec.floor_price = rec.floor_code.price_per_meter if rec.floor_code else 0.0


    type = fields.Selection([
        ('spc', 'SPC'),
        ('lvt', 'LVT'),
        ('wpc', 'WPC'),
        ('herringbone', 'Herringbone'),
    ], string="Type")

class SkirtingMaterial(models.Model):
    _name = 'skirting.material'
    _description = 'Skirting Material'
    lead_id = fields.Many2one('crm.lead', string="Lead")
    skirting_code = fields.Many2one('yallawrap.tile.code', string="Material (Optional)")
    skirting_qty = fields.Float(default=0.0)

    type = fields.Selection([
        ('break', 'Break Skirting'),
        ('replace', 'Replace Skirting'),
        ('white', 'White Skirting'),
        ('spc_lvt', 'SPC/LVT Skirting'),
    ], string="Type")
    formula_skirting = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )
    skirting_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")

    skirting_price = fields.Float(
        string="Floor Price",
        compute="_compute_floor_price",
        store=True
    )
    skirting_attachment_ids = fields.Many2many(
        'ir.attachment',
        'skirting_attachment_rel',
        'skirting_id',
        'attachment_id',
        string="Attachments"
    )


    @api.depends('skirting_code')
    def _compute_floor_price(self):
        for rec in self:
            rec.skirting_price = rec.skirting_code.price_per_meter if rec.skirting_code else 0.0
# ========================================
# Window Frame
# ========================================
class YallaWrapWindowFrame(models.Model):
    _name = 'yallawrap.window.frame'
    _description = 'Window Frame'

    lead_id = fields.Many2one('crm.lead', string="Lead")
    window_frame_code = fields.Many2one('yallawrap.tile.code', string="Material (Optional)")
    window_frame_qty = fields.Float(default=0.0)
    window_frame_width = fields.Float(string="Width (Optional)")
    window_frame_height = fields.Float(string="Height (Optional)")
    window_frame_meters = fields.Float(string="Meters for BOQ Calculator")
    window_frame_condition = fields.Selection([('good', 'Good Condition'), ('bad', 'Bad Condition')])
    window_frame_needs_scaffolding = fields.Selection([('yes', 'Yes'), ('no', 'No')])
    window_frame_labour = fields.Monetary(
        string="Labour Rate"
        , currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )
    countertop_condition_notes = fields.Text(string="Condition Notes (Optional)")
    window_frame_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")

    window_frame_price = fields.Float(
        string="window fram Price",
        compute="_compute_floor_price",
        store=True
    )

    @api.depends('window_frame_code')
    def _compute_window_frame_price(self):
        for rec in self:
            rec.window_frame_price = rec.window_frame_code.price_per_meter if rec.window_frame_code else 0.0
    needs_scaffolding_door = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Needs Scaffolding")
    formula_window_frame = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )
    window_attachment_ids = fields.Many2many(
        'ir.attachment',
        'window_attachment_rel',
        'window_id',
        'attachment_id',
        string="Attachments"
    )
# ========================================
# Furniture
# ========================================
class YallaWrapFurniture(models.Model):
    _name = 'yallawrap.furniture'
    _description = 'Furniture'

    lead_id = fields.Many2one('crm.lead', string="Lead")
    furniture_code = fields.Many2one('yallawrap.tile.code', string="Material (Optional)")
    furniture_qty = fields.Float(default=0.0)
    furniture_width = fields.Float(string="Width (Optional)")
    furniture_height = fields.Float(string="Height (Optional)")
    furniture_meters = fields.Float(string="Meters for BOQ Calculator")
    furniture_meters_labour = fields.Monetary(
        string="Labour Rate"
        , currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency"
    )
    furniture_type = fields.Char(string="Furniture Type")
    furniture_price_type = fields.Selection([
        ('meter', 'Price per Meter'),
        ('roll', 'Price per Roll')
    ], string="Price Type")

    furniture_price = fields.Float(
        string="window fram Price",
        compute="_compute_floor_price",
        store=True
    )

    @api.depends('furniture_code')
    def _compute_furniture_price(self):
        for rec in self:
            rec.furniture_price = rec.furniture_code.price_per_meter if rec.furniture_code else 0.0
    formula_furniture = fields.Text(
        string="Custom Formula (Optional)",
        help="Enter a custom formula for the BOQ calculation if needed."
    )
    furniture_attachment_ids = fields.Many2many(
        'ir.attachment',
        'furniture_attachment_rel',
        'furniture_id',
        'attachment_id',
        string="Attachments"
    )
class YallaWrapAttachment(models.Model):
    _name = "yallawrap.attachment"
    _description = "Inspection Attachments"

    name = fields.Char(string="Description")

    file = fields.Binary(string="File", attachment=True)
    filename = fields.Char(string="Filename")

    # Relations to inspection models
    kitchen_id = fields.Many2one('yallawrap.kitchen', string="Kitchen")
    bathroom_id = fields.Many2one('yallawrap.bathroom', string="Bathroom")
    wardrobe_id = fields.Many2one('yallawrap.wardrobe', string="Wardrobe")
    door_id = fields.Many2one('yallawrap.door', string="Door")
    flooring_id = fields.Many2one('yallawrap.flooring', string="Flooring")
    window_frame_id = fields.Many2one('yallawrap.window.frame', string="Window Frame")
    furniture_id = fields.Many2one('yallawrap.furniture', string="Furniture")

    lead_id = fields.Many2one('crm.lead', string="Lead")