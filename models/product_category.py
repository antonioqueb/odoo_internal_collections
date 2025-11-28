from odoo import models, fields, api
import re

class ProductCategory(models.Model):
    _inherit = 'product.category'

    # --- Campos de Configuración ---
    is_collection = fields.Boolean(
        string="Es una Colección Pública",
        default=False,
        help="Marca esta casilla si esta categoría representa una colección en el sitio web (Next.js)."
    )

    collection_key = fields.Char(
        string="Key / Slug (JSON)",
        help="La clave única que usa el JSON (ej: 'mineral specimens'). Si se deja vacío, se genera del nombre.",
        copy=False
    )

    # --- Contenido ---
    collection_title_display = fields.Char(
        string="Título Público",
        help="Si quieres que el título en la web sea diferente al nombre interno de la categoría."
    )
    
    collection_description = fields.Text(
        string="Descripción de la Colección",
        help="Texto completo descriptivo para la página de la colección.",
        translate=True
    )

    # --- Lógica de Slugs ---
    @api.onchange('name')
    def _onchange_name_generate_slug(self):
        if not self.collection_key and self.name:
            # Genera un slug simple: 'Earth Collection' -> 'earth-collection'
            self.collection_key = self.name.lower().strip()

    _sql_constraints = [
        ('collection_key_unique', 'unique(collection_key)', 'La Key (Slug) de la colección debe ser única.')
    ]
