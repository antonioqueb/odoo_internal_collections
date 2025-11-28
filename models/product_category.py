from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = 'product.category'

    # --- Configuración ---
    is_collection = fields.Boolean(
        string="Es una Colección Pública",
        default=False,
        help="Marca si esta categoría debe salir en el sitio web."
    )

    collection_key = fields.Char(
        string="Key / Slug (JSON)",
        help="Clave única para la URL (ej: alloys, metalicus).",
        copy=False
    )

    # --- Textos ---
    collection_title_display = fields.Char(
        string="Título Público",
        help="Nombre visual en el frontend."
    )
    
    collection_description = fields.Text(
        string="Descripción",
        translate=True
    )

    # --- Generación Automática de Slug ---
    @api.onchange('name')
    def _onchange_name_generate_slug(self):
        if not self.collection_key and self.name:
            self.collection_key = self.name.lower().strip().replace(" ", "-")

    _sql_constraints = [
        ('collection_key_unique', 'unique(collection_key)', 'La Key (Slug) debe ser única.')
    ]