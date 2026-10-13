# Общие функции v14: поворот плана как на картах команды, быстрый просмотр слоёв (matplotlib).
import math
CENTER = (407724.5, 6167314.9); ROT = math.radians(26.75)
def plan_xy(x, y):
    dx, dy = x - CENTER[0], y - CENTER[1]
    return dx * math.cos(ROT) - dy * math.sin(ROT), dx * math.sin(ROT) + dy * math.cos(ROT)
def to_plan(g):
    from shapely.ops import transform
    return transform(lambda x, y, z=None: plan_xy(x, y), g)
def world_xy(px, py):
    """План -> UTM (обратный поворот)."""
    x = px * math.cos(ROT) + py * math.sin(ROT); y = -px * math.sin(ROT) + py * math.cos(ROT)
    return x + CENTER[0], y + CENTER[1]
METRO_EXIT_PLAN = (-421, -81)                         # выход метро «Беляево» на территорию (отметка команды на схеме)
METRO_SQUARE_PLAN = [(-437, 4), (-359, 4), (-359, -157), (-437, -157)]   # площадь у выхода метро
MALL_CROSSING_PLAN = (48, -243)                      # большой пешеходный переход через ул. Миклухо-Маклая к ТЦ с «Ашаном»
