# Отрисовка моделей ворот в установленном PZ

Область выводов: IsoObject/spriteModel и shader door в проверенной сборке.
Другие пути (машины, персонажи, оружие) требуют отдельной сверки.
Пути `art/`, `research/` и `mod/` ниже отсчитываются от корня SlidingGates.
`render-audit/` в историческом описании означает `research/render-audit/`.
Скрипты извлечения и native probe находятся в `research/`; см. также
[workspace-workflow.md](workspace-workflow.md).

Проверено 2026-10-04 на `E:\SteamLibrary\steamapps\common\ProjectZomboid`.
SHA256 текущего `projectzomboid.jar`:
`E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`.

Использован CFR из `E:\git\PZMining\tools\cfr.jar`, но классы извлечены
из текущего игрового JAR. Некоторые классы PZMining, включая Core и
ModelManager, отличаются. Сравнение — в `render-audit/manifest.txt`.
Скрипт воспроизведения: `extract-render-code.ps1`. Декомпиляция — представление
байткода, а не оригинальные исходники; выборочные проверки дополнены запуском
настоящего JNI-импортера игры, без запуска игрового мира.

## Что подтверждено кодом

### Деревянные ворота (2026-10-10)

Fingerprint установленного JAR совпадает с указанным выше. Текущие
`entity_wood_walllvl1/2/3.txt` задают Woodwork 2/4/6, health 450/550/650,
skillBaseHealth 20 и sprites `walls_exterior_wooden_01_44/45`, `40/41`, `24/25`.
`entity_wood_doubledoor.txt` требует Woodwork 4 и два Base.Doorknob.
Пороги деревянных откатных ворот 4/5/7 — согласованное решение мода.

Текущий `generated/items/normal.txt`, item Doorknob: Icon DoorKnob,
WorldStaticModel DoorKnob, MetalValue 10 и tag base:hasmetal. Native FBX/texture
находятся в `media/models_X/WorldItems/DoorKnob.fbx` и
`media/textures/WorldItems/DoorKnob.png`. Деревянность ворот не означает
деревянную штатную ручку. Подтверждено импортом FBX в Blender и чтением recipes.

Бинарный `media/newtiledefinitions.tiles` прочитан по текущему tdef v1:
carpentry_01_48/49 имеют doorW/doorN и MaterialType Wood, без doorTrans;
50/51 — открытые sprites без doorW/doorN. Это обосновывает деревянные непрозрачные
collision carriers; финальные vision/cutaway в мире ещё требуют игровой проверки.
Текущий `lua/shared/Moveables/ISMoveableDefinitions.lua` определяет material Wood
и разборку через молоток/Perks.Woodwork. Собственный material yield мода
по-прежнему подавляет штатную выдачу от carrier sprites.

`research/probe-wood-native.py` успешно проверяет 56 model scripts,
48 animationMeshes, 208 spriteModels и шесть CraftRecipe с Woodwork 4/5/7
через текущие ScriptManager/ScriptBucketCollection. Native JNI импорт всех
56 GLB: `art/wood_native_import.txt`; проба сообщает counts и один vertex/normal/UV.
`research/probe-gate-tiles.py` теперь проверяет все 184 preview sprites,
PNG 1024×5888, `.tiles` и spriteModel bindings. Прежние indices 0..95 сохранены.
Проверки не являются подтверждением игрового вида или реального MP.

### Стадии повреждения ворот (2026-10-10)

Fingerprint установленного JAR совпадает с указанным выше. В текущем
`IsoThumpable` доступны `getHealth()` и `getMaxHealth()`; прочность принадлежит
отдельному объекту двери. Использование минимального отношения у частей ворот
и сохранение самой тяжёлой наблюдавшейся стадии — решение мода.

`IsoObject.setSpriteModelName` сбрасывает кеш SpriteModel, но не вызывает
`invalidateRenderChunkLevel`. При смене стадии мод явно помечает чанк флагом
256 (тот же флаг использует IsoObjectAnimations при завершении анимации).
`IsoObjectAnimations.update` удаляет завершённый AnimatedObject после вызова
`onAnimationFinished`; это обосновывает отложенную смену модели до окончания
нативного трека, а не один принудительный `setAnimating(false)`.

`research/probe-gate-damage.py` проверяет регистрацию 36 model scripts и
144 spriteModels через текущие ScriptManager/ScriptBucketCollection и настоящие
ParseScript/LoadScripts. Коллекции установленного ScriptManager называются
`models`, `animationMeshes`, `spriteModels`. Отчёт:
`research/render-audit/gate-damage-native.txt`. Все 36 GLB также проверены
установленным JNI-импортёром; `art/damage_native_import.txt`.

Эти проверки подтверждают парсинг и импорт, но не внешний вид в игре и не
бесшовность смены модели после сетевой анимации. Мод откладывает смену
повреждённой модели до окончания движения; реальный MP требует игровой проверки.

### Качество строительства и предпросмотр (2026-10-10)

Fingerprint установленного JAR совпадает с указанным выше. В текущих игровых
`media/lua/server/CraftRecipeCode/CraftRecipe_BuildMenu.lua` функции
`woodenWallLvl1Test/2Test/3Test` фильтруют отдельные рецепты по навыку и принимают
`{ player, recipe, shouldShowAll }`; Show All обходит фильтр видимости.
`media/lua/client/Entity/ISUI/CraftRecipe/ISRecipeScrollingListBox.lua`,
`addGroup`, вызывает `getOnAddToMenu()` через `callLuaBool` с этими параметрами.
Это фильтр списка, а не серверная проверка навыка/качества: дополнительная
проверка ворот выполняется модом до расхода материалов.

`research/probe-gate-quality.py` использует текущие ScriptManager/ScriptBucketCollection
для обоих entity-файлов, с отдельным ParseScript на файл и штатным
`ScriptParser.stripComments`, как в игровом загрузчике. Проверены все шесть
CraftRecipe, уровни MetalWelding 4/6/8, строки OnAddToMenu и наличие всех шести
entity UI styles в объединённом Base.default. Отчёт:
`research/render-audit/gate-quality-native.txt`. Это проверка парсинга и
регистрации, не визуальное подтверждение меню в игре.

`research/probe-gate-tiles.py` теперь проверяет 96 carriers, включая новые
уникальные footprints качества 48..95: metadata/PNG, tdef и наличие spriteModel
у всех 96 sprites через текущие игровые парсеры. Номера файла/tileset 6842/1
и старые индексы сохранены. Размер пустого атласа — 1024×3072. Проверка не
устанавливает внешний вид игрового курсора; отчёт обновлён в
`research/render-audit/gate-tiles-native.txt`.

### MP: нативная анимация и серверный таймер (2026-10-06)

Fingerprint совпадает с указанным выше. Проверены текущие `IsoObjectAnimations`,
заново извлечённые `IsoThumpable` и `IsoObject`:
`IsoObjectAnimations.addObject/update` сразу возвращаются на `GameServer.server`.
Клиентский `AnimatedObject` выставляет track speed 1.5 и обновляется через
`GameTime.getTimeDelta`. Поэтому серверный контроллер завершает движение по
времени клипа при той же скорости, а не по `IsoObject.isAnimating`.
`IsoThumpable.syncIsoObjectReceive` при смене `open` вызывает private
`PlayAnimation`, затем `OnContainerUpdate`. Предварительная смена `open` клиентом
перед пакетом может подавить этот запуск; moving-state уведомление мода не
подменяет нативную смену флага. Late-join snapshot выставляет конечную позу.
`IsoObject.renderModel` берёт animationPlayer из менеджера независимо от
boolean `animating`: один `setAnimating(false)` не отменяет клиентский track.
MP-контроллер проверен Lua mock-тестами; реальный порядок пакетов/вид в игре
ещё не проверены. Дополнительные контракты: `research/multiplayer-integration.md`.

### Отказ ToggleDoor и ложное завершение анимации (2026-10-06)

Fingerprint JAR совпадает с указанным выше. `IsoThumpable.class` заново
извлечён из установленного JAR и декомпилирован CFR в
`research/render-audit/source/zombie/iso/objects/IsoThumpable.java`.
`ToggleDoorActual` проверяет `isObstructed()` до изменения `open` и вызова
`PlayAnimation`, в обе стороны; при отказе возвращается без изменения состояния.
`ToggleDoor` имеет результат `void`: успех нужно устанавливать сравнением
`IsOpen()` до/после вызова. Сообщение Blocked само по себе не означает движение.
На успешном пути `OnContainerUpdate` вызывается перед `PlayAnimation`.

В моде запрос через slave мог записывать целевой `sgOpen`, хотя master отказал
из-за машины у закрытой створки; завершение затем выставляло открытую позу через
`ToggleDoorSilent`. Исправление проверяет препятствие у leaf в обе стороны и
подтверждение нативного переключения до записи состояния/запуска движения.
Lua regression для ширин 2/4 воспроизводит отказ у leaf с пустым карманом,
запрос через slave и отказ нативного toggle после preflight. Исправление ещё
требует повторения пользовательского сценария в игре; mock не проверяет Bullet.

### Render3DItem и строительный призрак (2026-10-06)

Fingerprint совпадает с указанным выше; проверены текущие извлечённые классы
`LuaManager$GlobalObject`, `WorldItemModelDrawer`, `ItemModelRenderer`.
`LuaManager.GlobalObject.Render3DItem(InventoryItem, IsoGridSquare, float x,
float y, float z, float rotation)` вызывает `WorldItemModelDrawer.renderMain`,
который использует `ItemModelRenderer`. Это путь предмета инвентаря: для обычного
WorldStaticModel `ItemModelRenderer.renderMain` получает modelScript через
`item.getWorldStaticItem()`, учитывает `modelScript.scale`, `item.worldScale`,
повороты и цвет предмета. Он не принимает SpriteModel или аргументы Open/Close,
animationTime и translate из наших spriteModel definitions.
Ванильный `ISPlace3DItemCursor.lua` использует его при размещении предметов
через `ISDropWorldItemAction`; `ISBuildIsoEntity.lua` рисует строительные тайлы
через `RenderGhostTileColor`. Не подменять один контракт другим только по имени
«3D»: предпросмотр ворот через InventoryItem-прокси возможен как отдельный
непроверенный вариант, которому нужны собственные размещение/поза/цвет.
Собственные тайлы не являются общим обязательным условием любого 3D-превью;
в текущем моде они обслуживают entity footprint и нативный spriteModel cursor.

### Собственные тайлы и строительный призрак (2026-10-06)

Fingerprint JAR совпадает с указанным выше. Текущие классы извлечены из установленной
игры; проверки форматов выполнены её настоящими Java-парсерами без игрового мира/GL.

- `IsoSprite.RenderGhostTileColor`: при наличии `spriteModel` вызывает
  `IsoObjectModelDrawer.renderMain` в `(x+0.5,y+0.5,z)`, RGB берёт из аргументов,
  alpha устанавливает в **1.0**, `bOutline=false`, `bApplySurfaceAlpha=false`.
  При статусе Ready/Loading возвращается до растрового fallback. Наличие модели
  не гарантирует полупрозрачность или цветной контур.
- `media/lua/server/BuildingObjects/ISBuildIsoEntity.lua`, `cacheSprites`:
  `IsoSprite.new()` + `LoadSingleTexture(name)` создают копию только с текстурой.
  Текущий `IsoSprite.LoadSingleTexture` не переносит `spriteModel`. Для модовых
  ворот кеш курсора заменён на зарегистрированные `getSprite(name)`; одного
  `spriteModels.txt` без этой поправки недостаточно для этого entity-курсора.
- `SpriteModelManager.init`: ищет модовый файл исключительно в
  `mod.mediaFile.common.absoluteFile/spriteModels.txt`, т.е. `common/media/`.
  Это отличается от обычного поиска version/common ресурсов через файловую систему.
- `ZomboidFileSystem.loadModPackFiles/loadModTileDefs`: загрузка через `pack=` и
  `tiledef=NAME NUMBER` в `mod.info`; pack в `media/texturepacks/`, `.tiles` в `media/`.
  Текущий `ChooseGameInfo.readModInfoAux` допускает tiledef numbers **100..8189**.
  CFR обычным режимом не разобрал метод; повтор с forcetopsort/ignoreexceptions
  показывает формат аргументов, но имеет предупреждение о восстановлении exceptions.
  Не переносить его восстановленное управление ошибками как доказанный исходник.
- `IsoWorld.LoadTileDefinitions`: `tdef` magic, little-endian version=1/count,
  строки с LF (CRLF отвергается), размеры сетки, tileset number, tile count,
  число и пары свойств для каждого тайла. Модовый tileset number 1..512 и
  максимум 512 тайлов. Текстовый `.tiles.txt` в этом пути не загружается.
- `TexturePackDevice.initMetaData/readPage`: `PZPK` magic, LE version=1/page count,
  строки с LE длиной, page name/count/alpha, subtexture name и восемь LE int:
  x,y,w,h,offsetX,offsetY,originalWidth,originalHeight; затем LE длина PNG и PNG.
  Явные untrimmed записи позволяют сохранить полностью прозрачные носители.
  Это доказательство для нашего генератора v1, не универсальная реализация TileZed.
- `IsoWorld.getSpriteID`: для модов `0x100000+(fileNumber-2)*262144+
  (tilesetNumber-1)*512+tileIndex`. Стабильность имён не заменяет стабильность
  числовых идентификаторов; их нужно сохранять для совместимости сохранений.

Реализация: `tools/build_gate_tiles.py`, `art/tiles/README.md`. Номер 6842 не обнаружен
у других локальных модов и в установленном Steam Workshop на дату проверки; это
не глобальная регистрация номера и не гарантия для любой будущей комбинации модов.
`research/probe-gate-tiles.py` проверил все 16 subtexture entries, PNG 1024×512,
загрузку всех 16 tile definitions и привязку всех 16 spriteModels настоящими
`TexturePackDevice`, ImageIO, `IsoWorld.LoadTileDefinitions`,
`SpriteModelsFile.parseFile`/`Tileset.initSprites`. Результат:
`research/render-audit/gate-tiles-native.txt`. Это не проверка OpenGL, меню или
визуального размещения в запущенной игре.

| Этап | Реальное поведение | Требование к нашим моделям |
| --- | --- | --- |
| GLB | Jassimp: MAKE_LEFT_HANDED, LIMIT_BONE_WEIGHTS, TRIANGULATE, OPTIMIZE_MESHES, REMOVE_REDUNDANT_MATERIALS, JOIN_IDENTICAL_VERTICES | Не зеркалить оси и UV вручную поверх преобразований игры |
| Выбор меша | Без явного имени выбирается первый меш с костями, иначе первый меш; обычный путь не рисует все меши GLB | Створку объединять в один skinned mesh; для деталей — отдельные статические GLB |
| Нормали | ImportedStaticMesh/ImportedSkinnedMesh копируют нормали; при их отсутствии ставят (0,1,0). Генерации smooth normals в стандартных флагах нет | Экспортировать корректные outward normals и заранее задавать сглаживание |
| Скиннинг | Формат вершин содержит четыре веса/индекса; веса нормализуются | Наши вершины имеют вес 1 на DoorBone |
| UV | Импортированные V превращаются в 1−V перед загрузкой VBO | Проверять полный маршрут, а не переворачивать PNG по одному этому выражению |
| Материал | Model загружает внешний PNG и shader из modelScript. door.frag использует albedo, нормали, ambient, направленные источники, tint, alpha | Blender roughness/metallic, normal maps, AO-узлы и Studio lighting не переносятся этим шейдером; нужную фактуру записывать в PNG |
| Масштаб | undoCoreScale умножает scale на 0.6666667; камера добавляет 1.5. translate применяется как (−X,Y,Z)/1.5 | Сохранять текущие калиброванные игровые anchors; не менять их по виду Blender |
| Камера | Ортографическая, повороты 30° вокруг X и 135° вокруг Y в координатах PZ | Проверять характерный игровой ракурс |
| Отсечение граней | Шейдеры с door используют FRONT вне текущего chunk render и BACK внутри него. Прочие шейдеры зависят от cullFace и состояния рендера | Не переворачивать корректную геометрию ради одного режима. Статическим деталям теперь явно назначен door, использующий door_static.vert |
| Depth/alpha | depth test и depth writes включены; fragment alpha <0.01 отбрасывается | Геометрические отверстия сетки безопаснее полупрозрачного полотна; прозрачную замену необходимо отдельно проверять по depth/sorting |

Доказательства в `render-audit/source/`:
`FileTask_LoadMesh.loadGLTF`, `ProcessedAiScene.findMesh`,
`ImportedStaticMesh.processAiScene`, `ImportedSkinnedMesh`, `Model` constructor,
`ModelScript.Load`, `IsoObjectModelDrawer.renderMain/renderModel`,
`FBORenderChunkCamera.pushModelViewMatrix`.
Шейдеры — в `media/shaders/door.{vert,frag}`, `door_static.vert` установленной игры.

## Свет и цвет

IsoObjectModelDrawer берёт ambient RGB из переданного ColorInfo. Перед каждым
рисованием пять источников сбрасываются; при обычном освещении задаётся один
добавочный источник (индекс 4): направление PZ `(0,5,-2)`, цвет `ambient * 0.375`,
радиус 5000. Shader.setLight дополнительно умножает цвет на `1−sqrt(29)/5000`.
Для обычного объекта без tint/hue изменения:

`RGB = PNG_RGB × min(ambient + ambient × 0.375 × attenuation × max(dot(N,L),0), 1)`.

Это простое ambient + Lambert освещение, без спекуляра, PBR и взаимных теней
деталей в этом shader path. При высоком ambient ограничение до 1 дополнительно
уменьшает различие освещённых граней. Исправление нормалей необходимо, но само
по себе не воспроизводит контраст студийного света Blender.

TextureID по умолчанию загружает модельный PNG в GL_RGBA (либо сжатый RGBA),
а не sRGB internal format. В шейдере нет sRGB→linear декодирования и обратного
преобразования. Для диагностического сравнения нужны Non-Color sampling и Raw
output в Blender; обычный PBR + AgX не является эталоном цвета PZ.

ModelManager.getTextureFlags в этой сборке не добавляет mipmap bit 0x40;
базовый модельный sampler получается линейным, без mipmaps, с возможным
сжатием и ограничением размера. Это отличается от последующего sampler
готовой текстуры чанка. Debug overrides и runtime texture settings могут
менять поведение: нельзя объявлять все текстуры игры NEAREST.

## Где теряются мелкие детали

FBORenderLevels.getTextureScale: при включённой опции highResChunkTextures
и zoom <0.75 текстура чанка становится вдвое крупнее; иначе scale=1.
FBORenderChunk.renderInWorldMainThread выбирает magnification NEAREST,
кроме zoom ровно 0.75 (LINEAR). Minification зависит от режима mipMaps;
промежуточный world/chunk rendering и debug overrides также влияют на результат.

При Core.tileScale=2, scale=1, undoCoreScale=true плотность для нашего GLB:
`1920 × Core.scale × 1.5 × (2/3) = 128/sqrt(2) ≈ 90.51 пикселя/единицу`
в плоскости камеры. Вдоль X створки проекция равна 64 пикселям/клетку.
Диаметр проволоки 0.01 даёт **не более 0.91 пикселя** в обычной текстуре;
в highRes — около 1.81 пикселя. Точный поперечный размер зависит от направления
проволоки и камеры. Увеличение PNG не добавляет покрытие геометрии пикселями.

Практический порядок работы:

1. Проверить геометрию, нормали, UV, веса и габариты до экспорта.
2. Оценить native-density preview; слабый свет и малое число пикселей учитывать
   при выборе толщины/частоты сетки, размеров крепежа и контраста.
3. При необходимости добавлять широкие локальные затемнения и износ в albedo.
   Тонкий случайный шум, больший polycount и большая текстура не заменяют
   читаемый силуэт. Не имитировать сильный глобальный свет в текстуре.
4. Финально проверить в PZ при обычном/дальнем зуме, движении, другом освещении,
   у стен и границ чанка. Скриншот не раскрывает все runtime debug settings.

## Обнаруженная и исправленная ошибка

В build_chainlink.py функция box создавала ВСЕ шесть граней прямоугольника
с направленными внутрь нормалями. Исправлен winding; теперь каждый box при
построении проверяет знак dot(face normal, face centre − box centre).
Круглые детали уже использовали отдельное сглаживание боков и плоские торцы.
Статическим деталям назначен явный door shader для согласованного пути
отсечения граней, UV offset и освещения. Изменённые GLB установлены в мод.

`probe-assimp.py` генерирует минимальный JVM probe без установки JDK и запускает
родной jassimp64.dll с флагами игры. На SG_Drive до исправления подтверждён
UV-переход: GLB V=0.9 → AiMesh V=0.1 → PZ VBO V=0.9. Двойного ручного flip нет.
Результаты для текущих экспортов — `render-audit/native-import-probes.txt`.

## Изменяемая ширина и анимации (2026-10-04)

В проверенном `zombie/iso/SpriteModel.java` scale хранится как одно float
(`setScale(float)`), а animationName и animationTime выбирают клип/позу.
Это равномерный масштаб объекта, а не независимое изменение ширины секций.
`IsoObjectAnimations.addObject` создаёт проигрыватель на объект; оно не
предоставляет параметр «ширина ворот/амплитуда клипа» в model script.
Для произвольной амплитуды нельзя считать достаточно одного setScale.

Применённое решение SlidingGates: один параметрический генератор исходной
геометрии, отдельный GLB и ход Open/Close на каждую зарегистрированную ширину.
Общие статические столбы, привод и одноклеточный рельс переиспользуются.
Секции можно моделировать модульно и затем объединять перед экспортом.
Несколько движущихся моделей также возможны как отдельная архитектура,
но требуют согласованной анимации, размещения и клеточной логики; это не
запрет, связанный с самим наличием анимаций. Такой путь здесь не проверен.

## Предпросмотр ворот

`art/render_pz_preview.py` создаёт отдельную сцену SG_PZ_RenderPreview с
тем же объектным набором, формулой света выше, камерой 30° и native pixel density.
Ambient 0.70 — явно выбранное условие диагностики, не измерение клетки скриншота.
Результаты: SG_PZ_Preview_1x.png (480×320), SG_PZ_Preview_2x.png (960×640).
Workbench, исходный материал и игровой экспорт остаются отдельными от preview.

Это **не пиксельно точный эмулятор PZ**: EEVEE иначе растеризует грани,
не воспроизводятся framebuffer filtering, chunk depth/cutaways, тон клеток,
камера/зум конкретного кадра и финальные postprocessing/UI passes.
Его назначение — ранняя проверка формы, формулы света и размеров деталей.

## N/W assembly integration (2026-10-07)

Installed JAR SHA256 remains
`E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33`.
No Blender geometry or exported GLBs were changed.

- Current `IsoObjectModelDrawer.renderMain` builds the sprite transform with
  translate `(-tx,ty,tz)/1.5` followed by `rotateXYZ(rx,-ry,rz)` in radians.
  `SpriteModel.Load` parses the rotate vector; vanilla W doors also use Y=90.
  W placement derives from the calibrated N assembly: rotate `(0,90,0)` and
  translate `(tz,ty,-tx)`. With the W catcher/leaf cell convention the whole
  assembly maps world `(x,y)` to `(y,1-x)` relative to the catcher. Width and
  clip time/travel are unchanged. `tests/test_gate_tiles.py` independently
  compares the leaf/post/rail/drive anchors and gameplay/ghost bindings.
- Parsed the installed `media/newtiledefinitions.tiles` (tdef v1). W gate door
  carriers are `fixtures_doors_fences_01_128/130` (closed 128 has `doorW`,
  `doorTrans`); opaque W doors are `fixtures_doors_01_68/70` (68 has `doorW`
  without `doorTrans`). Physics carrier `fixtures_doors_fences_01_38` has
  `PhysicsShape=WallW` (the original 36 is WallN). Physics carriers remain
  hidden static objects, not native double-door assemblies.
- Current `ISBuildIsoEntity.rotateKey/getFace`: nSprite 1=W, 2=N; getFace
  skips unavailable faces. A single N face explains why R appeared inert.
  `ISBuildIsoEntity:new` accepts serialized nSprite; preserve it on authority
  reconstruction instead of forcing N. Original constructor parameter names
  and material consumption stay intact.
- Preview indices 0..15 stay numerically stable; reserved 6/7 and 12..15 now
  contain W footprints, appended 16..19 W statics, 20..23 reserved. Pack/tdef
  grows to 24 entries and 1024x768 PNG. Native parser probe passed all 24
  spriteModels and tile definitions; report `research/render-audit/gate-tiles-native.txt`.

Scope: engine transform and carrier properties are installed-game evidence;
anchor mathematics and gameplay/layout are automated tests. Actual W appearance,
Bullet collision, animations, and multiplayer packet delivery still require gameplay
acceptance. This does not establish support for left-opening assemblies.
