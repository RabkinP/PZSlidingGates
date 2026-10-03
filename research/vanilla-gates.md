# Ванильные ворота B42 — разбор

Декомпилированные классы: `research/decompiled/` (IsoThumpable, IsoDoor, IsoObjectAnimations, SpriteModel*). Остальное — `E:\git\PZMining\decompiled`.

## Как рисуются ворота
- Тайл (спрайт) ↔ 3D-модель связываются в `media/spriteModels.txt`: `modelScript`, `translate`, `rotate`, `scale`, `animation` (`Open`/`Close`), `animationTime`.
- Для ворот (`fixtures_doors_fences_01`) закрытый и открытый тайлы разные: `_0/_1` — `animation = Open`, `_2/_3` — `animation = Close` (W и N).
- `modelScript` — `scripts/generated/models_isoobject.txt`: `mesh`, `texture`, `animationsMesh`, `shader = door`, `static = false`.
- Модели: `models_X/IsoObject/*.glb` (+ `.blend` в `blender/`). В glb лежат анимации `Open` и `Close` (0.5 с), каналы translation/rotation/scale на костях `DoorBone` и `PostBone`.

## Как открываются
`IsoThumpable.ToggleDoorActual`:
1. проверки (баррикада, замок, `isObstructed()` → «Blocked»),
2. `open = !open`, спрайт меняется на `openSprite`/`closedSprite`,
3. `square.RecalcAllWithNeighbours`, `sync(open?1:0)`, `PolygonalMap2.squareChanged`,
4. `PlayAnimation()` → `IsoObjectAnimations.addObject(obj, spriteModel, "Open"|"Close")` — анимация проигрывается один раз клиентом (на сервере не выполняется).
После анимации отрисовывается спрайт нового состояния (со своей `animation`/позой).

## Коллизия
- `getSpriteEdge(ignoreOpen)`: закрытая дверь — ребро N/W; открытая — другое ребро (N→W, W→N) либо E/S по флагам `attachedE/attachedS` тайла. Коллизия двери — логика ребра в Java, не флаги спрайта.
- Есть механизм «двойной двери»: свойство тайла `DOUBLE_DOOR`, `IsoDoor.toggleDoubleDoor`, `isDoubleDoorObstructed` — несколько клеток переключаются вместе.

## Вывод про offsetX/Y (результат прототипа)
- `IsoObject.getSpriteModel() != null` → объект рисуется через `IsoObjectModelDrawer.renderMain(...)`; `offsetX/offsetY` в этом пути **не используются**. Поэтому `setOffsetX/Y` на ванильной калитке ничего не делает (лог прототипа: slide стартовал без ошибок, на экране без изменений).
- Работающий путь для анимации — анимации внутри glb (кость `DoorBone`, translation), запускаемые через `IsoObjectAnimations`/спрайт-модель.

## Открытые вопросы
1. Выходит ли модель за пределы своей клетки без обрезки (FBO render chunk) и как с сортировкой глубины.
2. Можно ли из Lua запустить `IsoObjectAnimations.addObject` или нужно триггерить сменой спрайта/`ToggleDoor`.
3. Регистрация своих `spriteModels` и `modelScript` из мода: нужен ли собственный tileset (`.tiles` + текстура) для тайлов-носителей.
4. Какие ванильные тайлы — двухклеточные ворота (кандидаты: `fixtures_doors_fences_01_128..131`, entity `MetalWireFenceGate`; `_0/_1` — калитка 1 клетка).

## Результат прототипа с моделью из Blender (SG_ChainLink)
- Свой `.glb` + `modelScript` + `spriteModel` из скриптов мода работают: модель рисуется, `Open`/`Close` анимируются, 2-клеточный лист не обрезается за пределами своей клетки. Носитель — любой тайл, модель подменяется `setSpriteModelName`; статичные детали — `IsoObject` с тем же приёмом.
- **Ось X зеркальна:** модельный +X (Blender X) в игре идёт в мир −x (для N-ребра). Вдоль оси ворот сборку раскладываем в −x; `Right` (положительный ход) открывается в −x. Смещение носителя при размещении: `translate_x = b − 0.5 − k`, где `b` — Blender X объекта, `k` — сдвиг носителя в клетках в −x.
- В экспортах Blender нет объектных трансформаций (только локальная геометрия): положение объекта (`location`) надо задавать смещением `spriteModel`.
- **Ось Z тоже зеркальна** (модель в игре повёрнута на 180° вокруг вертикали: X и Z меняют знак). Для статичных деталей со смещением по Z относительно листа знак `translate_z` противоположен Blender: привод с Blender `y = −0.22` (внутренняя сторона листа) в игре ставится как `translate_z = −0.5 − 0.22`. Проверка по скриншоту: шток привода должен быть направлен на рейку листа, а ящик не должен закрывать сетку.
