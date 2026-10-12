Версия v8 - всё пересобрано по чертежу dxf/yacheiki_1_v8.dxf. EPSG:32637.

konkovo_v8.gpkg
  boundary            граница квартала из чертежа (GRANICA_UCHASTKA)
  cells, cells_excluded, buildings, entries_territory, fences, trees - без изменений (совпадают с чертежом)
  entrances_buildings подъезды = треугольники слоя "подъезды" чертежа (111), id - номер здания
  playgrounds         площадки из PL_* чертежа (type, area)
  parking, garbage, gates, arches, crossings - стоянки, мусорные площадки, ворота/шлагбаумы, арки, переходы из чертежа
  green               деревья = кроны (прежний слой) + ZEL_LES_DREVESNYE; трава = остальное озеленение

analiz_v8.gpkg
  network             оси дорожек и проездов, построенные по двойным кромкам чертежа.
                      type, ped - число пешеходных путей, group - группа, veh/vgroup - то же для машин, razdel - разделённость, length
  roads_tree(+_start) транспортное дерево путей (on_path = да: машины вынужденно идут по дорожке)
  facades             фасады жилых домов: с подъездом (30 м) / без подъезда (15 м) / торец (15 м)
  control_zones       АЖ / ПЖ / АП / ПП (source - от чего отложена зона), control - итоговые классы, competition
  playgrounds_zones, heights, ped_exits, veh_exits

dxf/konkovo_analiz_v8.dxf - то же в координатах чертежа: слои AN_* и исправленная зелень ZEL_*_ISPR
