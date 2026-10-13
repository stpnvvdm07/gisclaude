# ГИС Коньково (территория № 2): чистые слои для ручного анализа.
#
# Что делает: берёт результаты анализа (vector/konkovo_v16, analiz_v16, problems_v16) и собирает из них
#   GIS/data/<группа>/<слой>.gpkg — каждый слой отдельным файлом (имена файлов и слоёв латиницей, поля по-русски),
#                                    стиль сохранён внутри файла: перетащите его в любой проект QGIS — откроется раскрашенным;
#                                    папки: 1_base, 2_cells_entries, 3_paths, 4_control_osv, 5_problems, 6_preconditions, 0_basemap;
#   GIS/konkovo_gis.qgz — проект QGIS с группами: Основа, Дворы и входы, Пути, Контроль и освоенность, Проблемы, Предпосылки,
#                         Подложка (OSM и линии чертежа вокруг территории, спутник Яндекса и карта OSM — тайлами).
#
# Как запустить:
#   в QGIS: Модули → Консоль Python → «Показать редактор» → открыть этот файл → «Запустить» (▶).
#           Слои сразу добавятся в открытый проект группой «Коньково — ГИС».
#   без QGIS-окна (если стоит QGIS с Python):  python3 konkovo_gis.py
#
# Пересчитать сам анализ (нужны geopandas и scipy):  python3 analysis/s1_base.py, s2_network.py, s3_control_osv_flags.py.
import os, sys

from qgis.core import (QgsApplication, QgsProject, QgsVectorLayer, QgsVectorFileWriter, QgsFields, QgsField, QgsFeature,
                       QgsCoordinateTransformContext, QgsSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer,
                       QgsSingleSymbolRenderer, QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings,
                       QgsVectorLayerSimpleLabeling, QgsProperty, QgsSymbolLayer, QgsLayerTreeGroup, QgsWkbTypes, QgsUnitTypes)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QVariant

HEADLESS = QgsApplication.instance() is None
if HEADLESS:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _app = QgsApplication([], False); _app.initQgis()


def project_root():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:                                    # запуск из редактора консоли QGIS
        home = QgsProject.instance().homePath()
        if home and os.path.exists(os.path.join(home, "vector", "konkovo_v16.gpkg")): return home
        from qgis.PyQt.QtWidgets import QFileDialog
        return QFileDialog.getExistingDirectory(None, "Папка proektsem (где лежит konkovo_gis.py)")


ROOT = project_root()
V = os.path.join(ROOT, "vector"); OUT_DIR = os.path.join(ROOT, "GIS"); os.makedirs(OUT_DIR, exist_ok=True)
DATA = os.path.join(OUT_DIR, "data"); QGZ = os.path.join(OUT_DIR, "konkovo_gis.qgz")       # в путях — только латиница
K, A, P = (os.path.join(V, f) for f in ("konkovo_v16.gpkg", "analiz_v16.gpkg", "problems_v16.gpkg"))

# ----------------------------------------------------------------------------- цвета (как на картах презентации)
C = dict(bld="#D3CABD", edge="#3A3842", pink="#DA71D7", dark="#14131A", green="#5EC46E", lgreen="#BFE3B4", red="#D62828",
         dred="#B13840", orange="#E08A2B", purple="#6852A0", lilac="#A68CC6", blue="#4A74C9", lblue="#94ACD6", grey="#8B877F",
         lgrey="#C9C4BA", yellow="#E9D68A", water="#8FD3E0", olive="#2A9D4B", brown="#6B4A3A")

# ----------------------------------------------------------------------------- стили
def fill(color, outline=None, width=0.3, alpha=1.0, dash=False):
    return ("fill", dict(color=color, outline=outline, width=width, alpha=alpha, dash=dash))
def line(color, width=0.6, dash=False):
    return ("line", dict(color=color, width=width, dash=dash))
def point(color, size=2.0, outline="#FFFFFF", shape="circle"):
    return ("point", dict(color=color, size=size, outline=outline, shape=shape))
def cat(field, cats, kind, other=None, **kw):
    """Раскраска по значению поля (или выражению): cats = [(значение, подпись, цвет, толщина/размер)]."""
    return ("cat", dict(field=field, cats=cats, kind=kind, other=other, **kw))


def make_symbol(geom, kind, color, size=None, outline=None, alpha=1.0, dash=False, shape="circle"):
    from qgis.core import Qgis
    s = QgsSymbol.defaultSymbol(geom); sl = s.symbolLayer(0)
    if geom == QgsWkbTypes.PolygonGeometry:
        if kind == "outline" or color is None:                          # только контур
            sl.setBrushStyle(0); sl.setStrokeColor(QColor(outline or color)); sl.setStrokeWidth(size or 0.4)
        else:
            sl.setFillColor(QColor(color))
            if outline: sl.setStrokeColor(QColor(outline)); sl.setStrokeWidth(size or 0.2)
            else: sl.setStrokeStyle(0)
        if dash: sl.setStrokeStyle(2)
    elif geom == QgsWkbTypes.LineGeometry:
        s.setColor(QColor(color)); s.setWidth(size or 0.6)
        if dash: sl.setPenStyle(2)
    else:
        s.setColor(QColor(color)); s.setSize(size or 2.0); sl.setStrokeColor(QColor(outline or "#FFFFFF")); sl.setStrokeWidth(0.2)
        if shape != "circle":
            sl.setShape({"square": Qgis.MarkerShape.Square, "triangle": Qgis.MarkerShape.Triangle,
                         "diamond": Qgis.MarkerShape.Diamond, "star": Qgis.MarkerShape.Star}[shape])
    s.setOpacity(alpha)
    return s


def apply_style(lyr, st):
    geom = lyr.geometryType(); kind, o = st
    if kind == "fill":
        s = make_symbol(geom, "outline" if o["color"] is None else "fill", o["color"], o["width"], o["outline"], o["alpha"], o["dash"])
        lyr.setRenderer(QgsSingleSymbolRenderer(s))
    elif kind == "line":
        lyr.setRenderer(QgsSingleSymbolRenderer(make_symbol(geom, "line", o["color"], o["width"], dash=o["dash"])))
    elif kind == "point":
        lyr.setRenderer(QgsSingleSymbolRenderer(make_symbol(geom, "point", o["color"], o["size"], o["outline"], shape=o["shape"])))
    elif kind == "cat":
        cats = []
        for val, label, color, size in o["cats"]:
            s = make_symbol(geom, o["kind"], color, size, o.get("outline"), o.get("alpha", 1.0), o.get("dash", False))
            cats.append(QgsRendererCategory(val, s, label))
        if o["other"]:
            label, color, size = o["other"]
            cats.append(QgsRendererCategory(None, make_symbol(geom, o["kind"], color, size, o.get("outline"), o.get("alpha", 1.0)), label))
        lyr.setRenderer(QgsCategorizedSymbolRenderer(o["field"], cats))


def apply_labels(lyr, expr, size=8, color="#14131A"):
    pl = QgsPalLayerSettings(); pl.fieldName = expr; pl.isExpression = True
    tf = QgsTextFormat(); tf.setSize(size); tf.setColor(QColor(color))
    bf = QgsTextBufferSettings(); bf.setEnabled(True); bf.setSize(0.8); bf.setColor(QColor("#FFFFFF")); tf.setBuffer(bf)
    pl.setFormat(tf)
    if lyr.geometryType() == QgsWkbTypes.LineGeometry:                            # вдоль линии
        from qgis.core import Qgis
        pl.placement = Qgis.LabelPlacement.Line if hasattr(Qgis, "LabelPlacement") else QgsPalLayerSettings.Line
    lyr.setLabeling(QgsVectorLayerSimpleLabeling(pl)); lyr.setLabelsEnabled(True)


def size_by(lyr, expr):
    """Размер точки — по выражению (для мест выхода на улицу)."""
    key = getattr(QgsSymbolLayer, "PropertySize", None)
    if key is None: key = QgsSymbolLayer.Property.Size
    lyr.renderer().symbol().symbolLayer(0).setDataDefinedProperty(key, QgsProperty.fromExpression(expr))


# ----------------------------------------------------------------------------- слои: (группа, название, файл, слой, {поле: новое имя}, стиль, подписи)
FUNC = [("обслуживающий", "обслуживающий", C["orange"], None), ("не связан", "не связан с жильём", C["grey"], None)]
ORG = [("организован", "организован (арка, ворота, калитка, разрыв до 30 м)", C["olive"], 2.6), ("не организован", "не организован", C["red"], 2.6)]
INT = [("высокая", "4 пути и больше", C["dred"], 1.2), ("низкая", "2–3 пути", C["orange"], 0.8), ("один путь", "один путь", "#6F6A62", 0.4)]
CTL = [("контролируемая", "контролируемая", "#7BC47F", None), ("частично контролируемая", "частично контролируемая", "#F2D27A", None),
       ("неконтролируемая", "неконтролируемая", "#E58A84", None)]
OSV = [("освоенная", "освоенная", "#7BC47F", None), ("частично освоенная", "частично освоенная", "#F2D27A", None),
       ("неосвоенная", "неосвоенная", "#E58A84", None), ("не оценивается", "не оценивается (школы, детсады, вне ячеек)", "#E6E2DA", None)]
CLS = [("высокая", "высокая (6 и больше)", C["red"], None), ("средняя", "средняя (4–5)", C["orange"], None), ("низкая", "низкая (до 3)", C["yellow"], None)]
FL = {f"p{a}_{b}": f"п{a}_{b}" for a, b in ((1, 1), (1, 2), (1, 3), (1, 4), (2, 1), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3), (3, 4))}

LAYERS = [
    # 1. Основа
    ("1 Основа", "Граница территории", K, "boundary", {}, fill(None, C["pink"], 0.8, dash=True), None),
    ("1 Основа", "Здания", K, "buildings", {"id": "id", "Адрес / ориентир": "адрес", "Тип здания": "тип", "Этажность": "этажность",
        "Количество подъездов": "подъездов", "Год постройки": "год", "Тип проекта": "проект", "Материал стен": "материал",
        "Степень изношенности": "износ_данные", "Наша оценка изношенности": "износ_оценка", "function": "функция", "danger": "опасность"},
        cat("тип", [("Жилое", "жилое", "#C9BBA8", None), ("Смешанное", "смешанное", "#B9A58C", None), ("Нежилое", "нежилое", "#D9D2C6", None)],
            "fill", other=("не указан", "#E3DED5", None), outline="#8B877F"), None),
    ("1 Основа", "Озеленение", K, "green", {"type": "тип", "area": "площадь_м2"},
        cat("тип", [("деревья", "деревья", "#9FD08F", None), ("трава", "трава", "#D7EBC6", None)], "fill"), None),
    ("1 Основа", "Стоянки и гаражи", K, "parking", {"kind": "вид", "area": "площадь_м2", "status": "статус"}, fill("#C9C4BA", C["grey"], 0.2), None),
    ("1 Основа", "Ограждения", K, "fences", {"podtip": "тип", "comment": "комментарий"},
        cat("тип", [("Ограждение — высокое сплошное", "высокое сплошное", C["dark"], 0.7), ("Ограждение — высокое решётчатое", "высокое решётчатое", "#5F5B66", 0.5),
                    ("Ограждение — низкое", "низкое", C["grey"], 0.3)], "line", other=("тип не указан", C["lgrey"], 0.3)), None),
    ("1 Основа", "Участки школ и детсадов", K, "cells_excluded", {"area": "площадь_м2"}, fill("#E6E2DA", C["grey"], 0.3, alpha=0.8), None),
    ("1 Основа", "Подъезды", K, "entrances_buildings", {"id": "id"}, point(C["dark"], 1.6), None),
    ("1 Основа", "Бизнес и сервисы", K, "business", {"Назначение": "назначение", "Название": "название", "adress": "адрес", "placement": "размещение",
        "function": "функция", "danger": "опасность", "isolation": "изоляция"},
        cat("опасность", [("благоприятный", "благоприятный", C["green"], 2.4), ("индифферентный", "индифферентный", C["lblue"], 2.4),
                          ("опасный", "опасный", C["red"], 2.8)], "point"), None),
    ("1 Основа", "Площадки", K, "playgrounds", {"type": "тип", "area": "площадь_м2", "danger": "опасность"},
        cat("тип", [("детская", "детская", "#F2B5D4", None), ("спортивная", "спортивная", "#9EC5E8", None), ("воркаут", "воркаут", "#A68CC6", None),
                    ("для собак", "для собак", "#E9D68A", None)], "fill", outline=C["dark"]), None),
    ("1 Основа", "Мусорные площадки", K, "garbage", {}, point(C["brown"], 2.2, shape="square"), None),
    ("1 Основа", "Наблюдения: людность", K, "people_dens", {"dens": "людей"},
        cat("людей", [("много", "много людей", "#7BC47F", None), ("мало", "мало людей", "#E58A84", None)], "fill", alpha=0.45), None),

    # 2. Дворы и входы
    ("2 Дворы и входы", "Ячейки (дворы) и комфорт", K, "cells", {"num": "номер", "in_scope": "в_анализе", "area": "площадь_м2", "perimeter": "периметр_м",
        "fasad_area": "площадь_фасадов_м2", "vert_koef": "вертикаль_коэф", "vertical": "вертикаль", "fasad_len": "длина_фасадов_м",
        "iso_koef": "замкнутость_коэф", "isolation": "замкнутость", "size": "размер_м", "planning": "размер", "comfort": "комфорт",
        "score": "баллы", "comfort_rule": "комфорт_по_баллам"},
        cat("CASE WHEN \"в_анализе\" = 0 THEN 'вне анализа' ELSE \"комфорт\" END",
            [("Комфортная", "комфортная (таблица команды)", "#BFE3B4", None), ("Некомфортная", "некомфортная", "#F3C9C3", None),
             ("вне анализа", "вне анализа (без подъездов / вне границ)", "#EEEAE3", None)], "fill", outline=C["edge"], alpha=0.75), "\"номер\""),
    ("2 Дворы и входы", "Входы во двор", K, "entries_territory", {"node": "номер", "podtip": "тип", "fix_class": "организация", "degree": "фиксация",
        "gap_m": "просвет_м", "cells": "ячейки", "src": "источник", "photo": "фото"}, cat("организация", ORG, "point"), None),
    ("2 Дворы и входы", "Незакреплённый фронт двора", K, "open_edge", {"length": "длина_м"}, line(C["red"], 0.8, dash=True), None),
    ("2 Дворы и входы", "Зоны загрузки", K, "loading_zones", {"area": "площадь_м2", "isolation": "изоляция", "objects": "объекты_рядом"},
        fill(C["orange"], C["dred"], 0.3, alpha=0.55), None),
    ("2 Дворы и входы", "Арки", K, "arches", {}, line(C["purple"], 1.2), None),
    ("2 Дворы и входы", "Ворота и калитки", K, "gates", {}, point(C["dark"], 2.0, shape="square"), None),

    # 3. Пути
    ("3 Пути", "Пешеходное дерево путей", A, "network", {"type": "тип", "ped": "путей_к_улице", "group": "интенсивность", "metro": "путей_к_метро",
        "mall": "путей_к_ТЦ", "load": "нагрузка_всего", "lgroup": "нагрузка", "veh": "транспорт_путей", "vgroup": "транспорт",
        "razdel": "разделённость", "length": "длина_м"},
        cat("интенсивность", INT, "line", other=("прочие дорожки и проезды", "#D9D4CB", 0.25)), None),
    ("3 Пути", "Транспортное дерево (roads_counts)", A, "roads_tree", {"workload": "путей", "group": "группа", "length": "длина_м"},
        cat("группа", [("высокая", "4 пути и больше", C["purple"], 1.2), ("низкая", "2–3 пути", C["lblue"], 0.8), ("один путь", "один путь", C["grey"], 0.4)], "line"),
        "CASE WHEN \"путей\" >= 2 THEN \"путей\" END"),
    ("3 Пути", "Начала путей: двери и площадки", A, "ped_origins", {"kind": "вид", "dist_m": "до_улицы_м"},
        cat("вид", [("подъезд", "подъезд", C["dark"], 1.4), ("вход в организацию", "вход в организацию", C["blue"], 1.4), ("площадка", "площадка", "#E07AB5", 1.4)], "point"), None),
    ("3 Пути", "Места выхода на улицу", A, "ped_exits", {"paths": "путей"}, point("#FFFFFF", 2.0, outline=C["dred"]), "\"путей\""),
    ("3 Пути", "Подсчёт потоков (обследование)", A, "flows", {"id": "номер", "type": "тип", "sat_human": "людей_сб_час", "mon_est": "людей_пн_оценка",
        "in_car": "машин_въезд", "out_car": "машин_выезд", "cls": "класс"},
        cat("класс", [("высокий", "высокий", C["red"], 3.4), ("средний", "средний", C["orange"], 2.8), ("низкий", "низкий", C["yellow"], 2.2)], "point"), "\"номер\""),
    ("3 Пути", "Транзит нежильцов (к метро и ТЦ)", A, "transit", {"mode": "вид", "type": "тип", "to_metro": "к_метро", "to_tc": "к_ТЦ", "load": "нагрузка",
        "cls": "класс"}, cat("класс", [("высокая", "высокая", C["purple"], 1.0), ("низкая", "низкая", C["lilac"], 0.5)], "line"), None),
    ("3 Пути", "Метро и переход к ТЦ", A, "metro", {"what": "что"}, fill("#BFD3F2", C["blue"], 0.4, alpha=0.7), None),

    # 4. Контроль и освоенность
    ("4 Контроль и освоенность", "Зоны контроля (АЖ, ПЖ, АП, ПП)", A, "control_zones", {"type": "вид", "source": "правило", "area": "площадь_м2"},
        cat("вид", [("АЖ", "АЖ — активный жилой, 30 м", "#2A9D4B", None), ("ПЖ", "ПЖ — пассивный жилой, 15 м", "#9FD08F", None),
                    ("АП", "АП — активный публичный, 15 м", "#4A74C9", None), ("ПП", "ПП — пассивный публичный, 7,5 м", "#A9C1EA", None)],
            "fill", alpha=0.45), None),
    ("4 Контроль и освоенность", "Контролируемость", A, "control", {"type": "класс", "area": "площадь_м2"}, cat("класс", CTL, "fill"), None),
    ("4 Контроль и освоенность", "Конкуренция контроля (АЖ × АП)", A, "competition", {}, fill(None, C["purple"], 0.5), None),
    ("4 Контроль и освоенность", "Площадки: удалённость и контроль", A, "playgrounds_zones", {"type": "тип", "d_pod": "до_подъезда_м", "zone": "зона",
        "control": "контроль", "problem": "нарушение"}, cat("зона", [("ближняя", "ближняя (до 30 м)", "#F2B5D4", None), ("средняя", "средняя (30–100 м)", "#9EC5E8", None),
        ("периферийная", "периферийная", "#E9D68A", None)], "fill", outline=C["dark"]), None),
    ("4 Контроль и освоенность", "Освоенность (шестиугольники 7 м)", A, "osvoennost", {"cls": "класс", "kind": "покрытие", "B": "обустроено",
        "B_why": "обустроено_почему", "U": "используется", "U_why": "используется_почему", "note": "примечание", "area": "площадь_м2"},
        cat("класс", OSV, "fill"), None),

    # 5. Проблемы
    ("5 Проблемы", "Сводный счёт по ячейкам", P, "viol_cells", {"num": "номер", "score": "нарушений", "cls": "класс", "comfort": "комфорт",
        **FL, "p3_4a": "п3_4_конкуренция", "p3_4b": "п3_4_неконтроль", "p3_4c": "п3_4_неосвоено",
        "nodes_non": "неорг_входов", "wear40": "зданий_износ40", "loading_m2": "загрузка_м2", "danger_obj": "опасных_объектов", "combined_m": "совмещение_м",
        "transit_res_m": "транзит_у_жилья_м", "biz_transit": "сервисов_на_транзите", "pg_out": "площадок_вне_контроля", "comp_pct": "конкуренция_проц",
        "unc_pct": "неконтроль_проц", "unosv_pct": "неосвоено_проц"},
        cat("класс", CLS, "fill", outline=C["edge"], alpha=0.8), "\"номер\" || ' (' || \"нарушений\" || ')'"),
    ("5 Проблемы", "1.1 Некомфортные ячейки", P, "p1_1_cells", {"num": "номер", "comfort": "комфорт", "vertical": "вертикаль", "isolation": "замкнутость",
        "planning": "размер"}, fill("#F3C9C3", C["dred"], 0.4, alpha=0.6), None),
    ("5 Проблемы", "1.2 Неорганизованные входы", P, "p1_2_nodes", {"node": "номер", "podtip": "тип"}, point(C["red"], 2.6), None),
    ("5 Проблемы", "1.3 Территории вне зафиксированных границ", P, "p1_3_cells", {"num": "номер"}, fill("#E6E2DA", C["grey"], 0.4, alpha=0.7), None),
    ("5 Проблемы", "1.4 Здания с износом 40 % и выше", P, "p1_4_wear", {"id": "id", "addr": "адрес", "wear": "износ", "src": "источник"},
        fill("#B13840", C["dark"], 0.3, alpha=0.7), None),
    ("5 Проблемы", "2.1 Зоны загрузки во дворах", P, "p2_1_loading", {"area": "площадь_м2", "objects": "объекты_рядом"}, fill(C["orange"], C["dred"], 0.4, alpha=0.6), None),
    ("5 Проблемы", "2.2 Опасные объекты", P, "p2_2_objects", {"kind": "вид", "Назначение": "назначение"}, point(C["red"], 2.6, shape="triangle"), None),
    ("5 Проблемы", "2.3 Совмещение потоков людей и машин", P, "p2_3_combined", {}, line(C["red"], 1.2), None),
    ("5 Проблемы", "3.1 Высокий транзит у жилья", P, "p3_1_transit", {}, line(C["purple"], 1.2), None),
    ("5 Проблемы", "3.2 Обслуживающие объекты у транзита", P, "p3_2_objects", {"Назначение": "назначение", "function": "функция"}, point(C["purple"], 2.4), None),
    ("5 Проблемы", "3.3 Площадки вне нужного контроля", P, "p3_3_places", {"type": "тип", "zone": "зона", "problem": "нарушение"}, fill("#F2B5D4", C["red"], 0.6), None),
    ("5 Проблемы", "3.4а Конкуренция контроля", P, "p3_4_competition", {"area": "площадь_м2"}, fill(C["purple"], None, alpha=0.5), None),
    ("5 Проблемы", "3.4б Неконтролируемая территория", P, "p3_4_uncontrolled", {"area": "площадь_м2"}, fill("#E58A84", None, alpha=0.6), None),
    ("5 Проблемы", "3.4в Неосвоенная территория", P, "p3_4_abandoned", {"area": "площадь_м2"}, fill("#8B877F", None, alpha=0.6), None),

    # 6. Предпосылки
    ("6 Предпосылки", "Освоено и под контролем", P, "pre_osv_ctl", {"area": "площадь_м2"}, fill("#7BC47F", None, alpha=0.6), None),
    ("6 Предпосылки", "Комфортные дворы", P, "pre_comfort_cells", {"num": "номер", "comfort_score": "баллы"}, fill(None, C["olive"], 0.8), "\"номер\""),
    ("6 Предпосылки", "Организованные входы", P, "pre_nodes", {"node": "номер", "podtip": "тип"}, point(C["olive"], 2.4), None),
    ("6 Предпосылки", "Главные пешеходные оси", P, "pre_axes", {"ped": "путей"}, line(C["olive"], 1.0), None),
    ("6 Предпосылки", "Благоприятные закрытые объекты", P, "pre_fav_closed", {"name": "название"}, point(C["green"], 2.4, shape="diamond"), None),
]

# подложка: OSM и линии чертежа вокруг территории (обрезка по охвату ± 500 м), спутник и карта OSM — тайлами
B = os.path.join(V, "basemap")
GREEN = [(k, k, "#D7EBC6", None) for k in ("park", "grass", "meadow", "recreation_ground", "allotments", "cemetery")] + \
        [("forest", "forest", "#C4E2B4", None), ("scrub", "scrub", "#C4E2B4", None)]
BASEMAP = [
    ("Линии чертежа (DWG)", os.path.join(B, "dwg_context_lines.gpkg"), "dwg_context_lines", "dwg_lines", line("#B9B4AA", 0.15)),
    ("OSM: остановки и метро", os.path.join(B, "Moscow_transport_points.gpkg"), "Moscow_transport_points", "osm_transport_points",
        cat("fclass", [("railway_station", "метро", C["red"], 3.0), ("bus_stop", "остановка", C["blue"], 1.8)], "point")),
    ("OSM: здания", os.path.join(B, "Moscow_building.gpkg"), "moscow_buildings", "osm_buildings", fill("#E2DCD1", "#CFC7BA", 0.1)),
    ("OSM: водотоки", os.path.join(B, "Moscow_waterways.gpkg"), "Moscow_waterways", "osm_waterways", line(C["water"], 0.5)),
    ("OSM: железные дороги", os.path.join(B, "Moscow_railways.gpkg"), "Moscow_railways", "osm_railways", line("#8B877F", 0.5, dash=True)),
    ("OSM: вода", os.path.join(B, "Moscow_water.gpkg"), "moscow_water", "osm_water", fill(C["water"])),
    ("OSM: дорожные площади", os.path.join(B, "Moscow_traffic_areas.gpkg"), "Moscow_traffic_areas", "osm_traffic_areas", fill("#ECE7DE")),
    ("OSM: зелень (землепользование)", os.path.join(B, "Moscow_landuse.gpkg"), "Moscow_landuse", "osm_landuse", cat("fclass", GREEN, "fill")),
]
TILES = [("Спутник (Яндекс)", "crs=EPSG:3395&format&type=xyz&url=https://core-sat.maps.yandex.net/tiles?l%3Dsat%26v%3D3.1025.0%26x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D%26scale%3D1%26lang%3Dru_RU&zmax=19&zmin=0"),
         ("Карта OSM", "type=xyz&url=https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0")]

# порядок групп в проекте сверху вниз (точки и линии — над полигонами, подложка — в самом низу); папки — латиницей
GROUP_ORDER = ["5 Проблемы", "6 Предпосылки", "3 Пути", "2 Дворы и входы", "4 Контроль и освоенность", "1 Основа", "0 Подложка"]
GROUP_DIR = {"1 Основа": "1_base", "2 Дворы и входы": "2_cells_entries", "3 Пути": "3_paths", "4 Контроль и освоенность": "4_control_osv",
             "5 Проблемы": "5_problems", "6 Предпосылки": "6_preconditions", "0 Подложка": "0_basemap"}


def export_layer(path, out_name, src, layer, fmap=None, rect=None):
    """Слой в отдельный файл GPKG: поля из fmap (новые имена, новый порядок) или все поля; rect — обрезка по охвату."""
    from qgis.core import QgsFeatureRequest
    s = QgsVectorLayer(f"{src}|layername={layer}", layer, "ogr")
    if not s.isValid(): print("  нет слоя:", layer, "в", os.path.basename(src)); return False
    sf = s.fields()
    keep = [(sf.indexOf(o), n) for o, n in fmap.items() if sf.indexOf(o) >= 0] if fmap is not None else [(i, sf.at(i).name()) for i in range(sf.count()) if sf.at(i).name() != "fid"]
    fields = QgsFields()
    for i, n in keep:
        f = QgsField(sf.at(i)); f.setName(n)
        if f.type() == QVariant.Bool: f = QgsField(n, QVariant.Int)
        fields.append(f)
    o = QgsVectorFileWriter.SaveVectorOptions(); o.driverName = "GPKG"; o.layerName = out_name; o.fileEncoding = "UTF-8"
    o.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    w = QgsVectorFileWriter.create(path, fields, s.wkbType(), s.crs(), QgsCoordinateTransformContext(), o)
    if w.hasError() != QgsVectorFileWriter.NoError: print("  ошибка записи:", out_name, w.errorMessage()); return False
    req = QgsFeatureRequest()
    if rect is not None: req.setFilterRect(rect)
    for ft in s.getFeatures(req):
        nf = QgsFeature(fields); nf.setGeometry(ft.geometry())
        nf.setAttributes([ft[i] if not isinstance(ft[i], bool) else int(ft[i]) for i, _ in keep]); w.addFeature(nf)
    del w
    return True


def build():
    import shutil
    from qgis.core import QgsRasterLayer
    if os.path.isdir(DATA): shutil.rmtree(DATA)
    proj = QgsProject.instance()
    if HEADLESS:
        proj.clear(); proj.setCrs(QgsVectorLayer(f"{K}|layername=boundary", "b", "ogr").crs())
    root = proj.layerTreeRoot()
    top = root if HEADLESS else root.insertGroup(0, "Коньково — ГИС")
    groups = {g: top.addGroup(g) for g in GROUP_ORDER}
    n = 0

    def add(grp, name, path, out_name, style, labels=None):
        lyr = QgsVectorLayer(f"{path}|layername={out_name}", name, "ogr")
        apply_style(lyr, style)
        if labels: apply_labels(lyr, labels)
        lyr.saveStyleToDatabase("default", name, True, "")                    # стиль внутри файла слоя
        proj.addMapLayer(lyr, False); groups[grp].addLayer(lyr)
        return lyr

    for grp, name, src, layer, fmap, style, labels in LAYERS:                 # каждый слой — свой файл, имя латиницей
        d = os.path.join(DATA, GROUP_DIR[grp]); os.makedirs(d, exist_ok=True); path = os.path.join(d, f"{layer}.gpkg")
        if not export_layer(path, layer, src, layer, fmap): continue
        lyr = add(grp, name, path, layer, style, labels)
        if name == "Места выхода на улицу": size_by(lyr, "2 + 0.9 * sqrt(\"путей\")"); lyr.saveStyleToDatabase("default", name, True, "")
        n += 1
    # общая нагрузка — тот же слой сети другим стилем (в проекте)
    net = QgsVectorLayer(f"{os.path.join(DATA, GROUP_DIR['3 Пути'], 'network.gpkg')}|layername=network", "Сеть: общая нагрузка (двери + метро + ТЦ)", "ogr")
    apply_style(net, cat("нагрузка", [("высокая", "20 путей и больше", C["dred"], 1.2), ("низкая", "2–19 путей", "#E07AB5", 0.7),
                                      ("один путь", "один путь", "#6F6A62", 0.3)], "line", other=("без путей", "#D9D4CB", 0.25)))
    proj.addMapLayer(net, False); groups["3 Пути"].insertLayer(1, net).setItemVisibilityChecked(False)
    # подложка
    rect = QgsVectorLayer(f"{K}|layername=boundary", "b", "ogr").extent(); rect.grow(500)
    d = os.path.join(DATA, GROUP_DIR["0 Подложка"]); os.makedirs(d, exist_ok=True); nb = 0
    for name, src, layer, out_name, style in BASEMAP:
        path = os.path.join(d, f"{out_name}.gpkg")
        if os.path.exists(src) and export_layer(path, out_name, src, layer, None, rect): add("0 Подложка", name, path, out_name, style); nb += 1
    for name, uri in TILES:
        r = QgsRasterLayer(uri, name, "wms"); proj.addMapLayer(r, False); groups["0 Подложка"].addLayer(r).setItemVisibilityChecked(False)
    for g in GROUP_ORDER:                                                     # по умолчанию видны основа, дворы и подложка
        groups[g].setItemVisibilityChecked(g in ("1 Основа", "2 Дворы и входы", "0 Подложка"))
    if HEADLESS:
        proj.writeEntry("Paths", "/Absolute", False); proj.setTitle("Коньково — ГИС для ручного анализа")
        from qgis.core import QgsReferencedRectangle
        ext = QgsVectorLayer(f"{K}|layername=boundary", "b", "ogr").extent(); ext.scale(1.1)
        vs = proj.viewSettings(); vs.setDefaultViewExtent(QgsReferencedRectangle(ext, proj.crs()))
        if hasattr(vs, "setDefaultRotation"): vs.setDefaultRotation(-26.75)        # улицы по осям, как на картах команды
        proj.write(QGZ); print("проект:", QGZ)
    print(f"готово: {n} слоёв анализа и {nb} слоёв подложки (+ {len(TILES)} тайловых) в {DATA}")


build()
if HEADLESS: _app.exitQgis()
