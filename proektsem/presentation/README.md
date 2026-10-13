# Презентация «Средовой анализ придомовых территорий: проблемы и предпосылки» (Коньково №2, анализ v15)

Готовые файлы: **`deck.pptx`** (редактируемая: PowerPoint, Keynote, Google Slides; в Figma Slides — «Импорт → PowerPoint»),
`deck.pdf`, `deck.html`, `png/sNN.png`. План — `../doc_plan_презентация.md`. Требования с доски Холста — `../design/holst_board/NOTES.md`.

Сборка с нуля:

```
cd ../analysis && python3 s1_base.py && python3 s2_network.py && python3 s3_control_osv_flags.py && cd -   # анализ v15
python3 deck_data15.py              # числа из ../vector/*_v15.gpkg -> deck_data15.json
python3 map_scripts/run_all.py      # все карты (или одна: python3 map_scripts/09_потоки_людей.py) -> maps/c_*.png + maps15.json
python3 sketch3d.py                 # 3D-вид ячеек (этаж 3 м) -> maps/sketch_vert.png + ../vector/3d/cells_vert_v15.dae (SketchUp)
python3 deck.py                     # разметка слайдов -> deck.json (печатает замечания проверки наложений)
python3 render_html.py && python3 export.py   # deck.html, png/, deck.pdf (Chromium)
python3 export_pptx.py              # deck.pptx — текст, фигуры и линии редактируются, карты — картинки
```

Шрифт — SF Pro Display (`../design/san-francisco-pro-display/`): установите его, чтобы PPTX выглядел как PDF.
Места под фото — серые фигуры «ФОТО: …»: правый клик → «Заменить рисунок» / вставить фото поверх.

Визуальная система:

- сетка и приёмы — из презентаций «Митино», «Торжок», «Красная Пресня»: блоки встык, тёмная шапка, крупные числа на мазке, бледные номера, таблицы с чередованием строк;
- цвета команды: #14131A, #DA71D7, #F4F3EA, белый; тематические цвета только в картах и их легендах;
- карты — в шаблоне команды: шапка 192, колонка легенды 440, логотип 440, карта 1480×888 (`s*`); карта 1280×720 с розовой колонкой (`m*`); пары 960×540; итоговая карта 1920×864;
- мазки — присланные элементы `../design/brush/1..5.png`, перекрашиваются в `assets/brush/`;
- места под фото — серые плашки «фото: …» (в разметке у них `name = "ФОТО: …"`), источников на слайдах нет.
