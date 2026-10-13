# proektsem — средовой анализ дворов, Коньково, территория № 2 (v15, 13.10.2026)

## Что где лежит
| Папка / файл | Что внутри |
| --- | --- |
| `proektsem.qgz` | проект QGIS, все слои ссылаются на `*_v15.gpkg` |
| `vector/konkovo_v15.gpkg` | ячейки (40 в анализе, 14 и 28 — вне анализа), входы (46), открытый фронт, зоны загрузки (9), исходные слои обследования |
| `vector/analiz_v15.gpkg` | сеть путей с нагрузкой, зоны контроля, контролируемость, площадки, освоенность (шестиугольники 7 м) |
| `vector/problems_v15.gpkg` | нарушения 1.1–3.4 по ячейкам (`viol_cells`: score, класс), слои отдельных проблем, предпосылки |
| `vector/basemap`, `proektbase`, `people_dens.gpkg`, `pokrytiya_v9.gpkg` | исходные данные — не менять |
| `analysis/` | расчёт: `s1_base.py` → `s2_network.py` → `s3_control_osv_flags.py` (логи `log_s*.txt`), `dwg/` — слои из DWG |
| `presentation/` | презентация: `deck.pptx` (редактируемая), `deck.pdf`, `map_scripts/` — по скрипту на каждую карту, см. `presentation/README.md` |
| `qgis_plugin/konkovo_tools/` | плагин QGIS «Коньково»: обновить слои до последней версии, удалить ненужные слои |
| `tools/clean_project.py` | перевод `proektsem.qgz` на последние версии gpkg без запуска QGIS |
| `design/holst_board/` | скриншоты доски Холста и выжимка требований (`NOTES.md`) |
| `doc_plan_презентация.md` | план 31 слайда и итоговые числа |
| `_archive/` | старые версии (v8–v14), скрипты карт QGIS v13, аудит v12 |

## Как пересчитать всё
```
cd analysis && python3 s1_base.py && python3 s2_network.py && python3 s3_control_osv_flags.py
cd ../presentation && python3 deck_data15.py && python3 map_scripts/run_all.py && python3 deck.py && python3 export.py && python3 export_pptx.py
cd .. && python3 tools/clean_project.py
```

## Главные числа v15
- 40 дворов в анализе (31 га); ячейки 14 и 28 без подъездов — вне анализа; комфортных 18.
- Входы: 46, организованы 25 (8 арок, 8 ворот, 2 калитки, 7 разрывов ≤ 30 м); незакреплённый фронт 1045 м.
- Контроль: под контролем 43 %, частично 28 %, без контроля 28 %. Освоенность: 59 / 36 / 4 %.
- Нарушений 129; классы высокий / средний / низкий — 2 / 14 / 24; ядро при любых порогах — дворы 11 и 35.
