from odoo import models, fields, api
import re

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # --- Contenido CMS / Headless ---
    headless_short_description = fields.Text(
        string="Descripción Corta",
        help="Breve resumen para tarjetas de producto."
    )
    
    headless_long_description = fields.Html(
        string="Descripción Larga (Rich Text)",
        help="Contenido completo del producto."
    )

    headless_material = fields.Char(string="Material / Composición")
    
    # --- Dimensiones Específicas (Largo x Ancho x Alto) ---
    # Odoo tiene 'volume' y 'weight', pero a veces se necesita L/W/H explícito
    dim_length = fields.Float(string="Largo (cm)")
    dim_width = fields.Float(string="Ancho (cm)")
    dim_height = fields.Float(string="Alto (cm)")

    # --- SEO & URLs ---
    headless_slug = fields.Char(
        string="Slug URL",
        copy=False,
        help="Identificador único para la URL del frontend."
    )
    headless_seo_keyword = fields.Char(string="Palabra Clave SEO")
    headless_meta_title = fields.Char(string="Meta Título")
    headless_meta_description = fields.Text(string="Meta Descripción")

    # --- Generación automática de Slug ---
    @api.onchange('name')
    def _onchange_name_slug(self):
        if not self.headless_slug and self.name:
            # Limpieza básica para crear un slug
            s = self.name.lower().strip()
            s = re.sub(r'[^a-z0-9\s-]', '', s) # Quitar caracteres especiales
            self.headless_slug = re.sub(r'\s+', '-', s) # Espacios a guiones

    _sql_constraints = [
        ('headless_slug_unique', 'unique(headless_slug)', 'El Slug del producto debe ser único.')
    ]