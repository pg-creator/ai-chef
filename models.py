from __future__ import annotations

from datetime import date
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, conint, confloat


class Ingrediente(BaseModel):
    nombre: str = Field(..., description="Nombre del ingrediente, en singular y sin mayúsculas innecesarias")
    cantidad: confloat(gt=0) = Field(..., description="Cantidad numérica referida a una persona (raciones_base=1)")
    unidad: str = Field(..., description="Unidad de medida, por ejemplo: g, ml, ud, cda")
    nota: Optional[str] = Field(None, description="Detalle opcional, por ejemplo: picado, en rodajas")


class Receta(BaseModel):
    tipo: Literal["receta"] = "receta"
    titulo: str
    raciones_base: conint(gt=0) = 1
    tiempo_min: conint(gt=0)
    ingredientes: List[Ingrediente]
    pasos: List[str]


class RecetaMenu(BaseModel):
    """Versión simplificada de receta para usar dentro del menú semanal."""

    titulo: str
    tiempo_min: conint(gt=0)
    ingredientes: List[Ingrediente]
    pasos: List[str]


class ComidaDia(BaseModel):
    tipo: str = Field(..., description="Tipo de comida: desayuno, comida, cena, snack, etc.")
    receta: RecetaMenu


class DiaMenu(BaseModel):
    fecha: date
    comidas: List[ComidaDia]


class ItemListaCompra(BaseModel):
    nombre: str
    cantidad: confloat(gt=0)
    unidad: str
    notas: Optional[List[str]] = None


class MenuSemanal(BaseModel):
    tipo: Literal["menu_semanal"] = "menu_semanal"
    week_start: date
    comidas_por_dia: conint(gt=1)
    dias: List[DiaMenu]
    lista_compra: List[ItemListaCompra]


def receta_json_schema() -> dict:
    """Devuelve el JSON Schema para una receta individual."""
    return Receta.model_json_schema()


def menu_semanal_json_schema() -> dict:
    """Devuelve el JSON Schema para un menú semanal con lista de compra incluida."""
    return MenuSemanal.model_json_schema()

