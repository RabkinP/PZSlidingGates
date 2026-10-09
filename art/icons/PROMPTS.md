# Иконки Sliding Gates

Пять отдельных PNG с настоящей прозрачностью. Общий стиль: небольшие предметные
иконки под Project Zomboid, приглушённая палитра и читаемый силуэт. Генерация —
встроенным image_gen, по одной иконке за вызов. Сохранять оригиналы в `generated/`;
не подменять игровые иконки до проверки размера и читаемости в интерфейсе.

Референсы при генерации:
- Электромотор — без входных изображений.
- Привод и пульт — `generated/electric-motor.png` только для стиля, палитры и света.
- Ворота 2 — электромотор для стиля, `../SG_PZ_Preview_2x.png` для общего вида
  створки и столбов. Привод, фон и длинный выступающий рельс из превью исключаются.
- Ворота 4 — `generated/build-gate-2.png` для стиля, ракурса и конструкции;
  физическая ширина удваивается, высота сохраняется.

Каждый референс перед вызовом просмотрен. Его роль явно указывается в дополнении
к соответствующему промпту. Каждый агент создаёт одну отдельную иконку; следующий
запускается только после завершения предыдущего.

## 1. Электромотор — electric-motor.png

```text
Use case: stylized-concept
Asset type: a single inventory item icon for the Project Zomboid mod Sliding Gates.
Subject: one salvaged electric motor from a 1990s washing machine or tumble dryer, suitable for a homemade gate drive through a reduction gearbox. A compact heavy cylindrical gray steel body, dark end caps, a short exposed output shaft, two mounting feet and a small attached terminal block. The shaft and mounting feet must make it immediately recognizable as an electric motor rather than a battery or generator. No belt, appliance cabinet, loose wires or extra parts.
Style: restrained low-resolution game inventory sprite, muted utilitarian 1990s industrial appearance, chunky pixel-like edges and simplified painted shading. Limited gray, charcoal and subdued olive palette. A readable silhouette with two or three broad value groups, sparse worn-metal marks. Not photorealistic, not glossy, not a vector pictogram.
Composition: one isolated object centered on a square canvas, three-quarter view from slightly above, shaft pointing toward the lower right. Fill about 80 percent of the canvas with comfortable transparent padding. Design for readability when displayed at 32 or 64 pixels; remove microdetail rather than adding noise.
Lighting: soft directional light from upper left; darker lower-right faces; subtle dark edge definition; no external cast shadow.
Background: genuinely transparent alpha everywhere outside the object, including openings. No checkerboard drawn into the image, floor, backdrop, frame, text, numbers, labels, logos or watermark. Deliver exactly one icon, not a sheet or comparison board.
```

## 2. Привод — gate-drive.png

```text
Use case: stylized-concept
Asset type: a single inventory item icon for the Project Zomboid mod Sliding Gates.
Subject: one portable homemade sliding-gate drive assembly. A squat olive-gray rectangular steel motor housing on a short dark mounting base, a restrained row of ventilation slots, a small side gearbox and a short exposed drive pinion on an output shaft beside the housing. It must read as a rugged electromechanical drive, clearly different from a cylindrical bare motor, car battery and generator. Keep the case closed. No gate, rail, battery, remote, cables, antenna or loose components.
Style: restrained low-resolution game inventory sprite, muted utilitarian 1990s industrial appearance, chunky pixel-like edges and simplified painted shading. Limited gray, charcoal and subdued olive palette. A readable silhouette with two or three broad value groups, sparse worn-metal marks. Not photorealistic, not glossy, not a vector pictogram.
Composition: one isolated object centered on a square canvas, three-quarter view from slightly above. The top, front and pinion-bearing side are visible. Fill about 80 percent of the canvas with comfortable transparent padding. Design for readability when displayed at 32 or 64 pixels; the box and protruding pinion matter more than tiny screws.
Lighting: soft directional light from upper left; darker lower-right faces; subtle dark edge definition; no external cast shadow.
Background: genuinely transparent alpha everywhere outside the object, including openings. No checkerboard drawn into the image, floor, backdrop, frame, text, numbers, labels, logos or watermark. Deliver exactly one icon, not a sheet or comparison board.
```

## 3. Пульт-брелок — gate-remote.png

```text
Use case: stylized-concept
Asset type: a single inventory item icon for the Project Zomboid mod Sliding Gates.
Subject: one compact 1990s radio remote key fob for a sliding gate. A charcoal plastic rounded rectangular body with exactly one large subdued red rubber button, and one small metal split key ring threaded through an integrated eyelet at the top. The ring is attached to the body, not floating beside it. It should look simple, sturdy and slightly used. No keys, screen, number pad, antenna, battery, cable or extra buttons.
Style: restrained low-resolution game inventory sprite, muted utilitarian 1990s appearance, chunky pixel-like edges and simplified painted shading. Charcoal and medium gray with one restrained red accent and dull steel for the ring. A readable silhouette with two or three broad value groups. Not photorealistic, not glossy, not a vector pictogram.
Composition: one isolated object centered on a square canvas, three-quarter view from slightly above, a gentle diagonal from upper left to lower right. The button face and complete ring are plainly visible. Fill about 80 percent of the canvas with comfortable transparent padding. Design for readability when displayed at 32 or 64 pixels; keep the button large and the ring opening clear.
Lighting: soft directional light from upper left; darker lower-right faces; subtle dark edge definition; no external cast shadow.
Background: genuinely transparent alpha everywhere outside the object and through the ring opening. No checkerboard drawn into the image, floor, backdrop, frame, text, numbers, labels, logos or watermark. Deliver exactly one icon, not a sheet or comparison board.
```

## 4. Строительство ворот на 2 клетки — build-gate-2.png

```text
Use case: stylized-concept
Asset type: a single construction-menu icon for a two-cell sliding chain-link gate in the Project Zomboid mod Sliding Gates.
Subject: one CLOSED single-leaf chain-link sliding gate with a two-cell-wide opening. A muted gray-green rectangular tubular frame filled with a simplified diagonal diamond wire mesh, a catcher post at the left edge and a guide post at the right edge, two small bottom wheels on a straight ground rail. One small handle on the left end frame tube. A short roller bracket on the guide post. The moving leaf ends at the two posts and has no rear tail. This is a single translating leaf, not two hinged leaves. Show the manual construction without a motor. Keep the rail compact and visually subordinate.
Style: restrained low-resolution isometric construction sprite matching muted Project Zomboid inventory art. Chunky pixel-like edges, simplified painted shading, gray/charcoal/subdued olive palette. Use a coarse readable diamond mesh rather than hundreds of hairline wires. Not photorealistic, not glossy, not a vector pictogram.
Composition: one isolated assembly on a square canvas, three-quarter isometric view from slightly above, front face extending from upper left toward lower right. The height remains substantial relative to the short two-cell opening. Center the assembly and fill roughly 85 percent of the available width with transparent padding. Clear at 64 pixels. No scene, fence extending beyond the gate or dimension markers.
Lighting: soft directional light from upper left; darker lower-right faces; subtle dark edge definition; no external cast shadow.
Constraints: one leaf only; closed pose; two edge posts; no central split, hinges, swing arc, overhead beam, tall gantry, moving upper carriage or electric drive. No text, numbers, labels, logos, watermark, background, floor or drawn checkerboard. Genuine transparent alpha outside the assembly and through the mesh. Deliver exactly one icon, not a sheet.
```

## 5. Строительство ворот на 4 клетки — build-gate-4.png

```text
Use case: stylized-concept
Asset type: a single construction-menu icon for a four-cell sliding chain-link gate in the Project Zomboid mod Sliding Gates.
Subject: one CLOSED single-leaf chain-link sliding gate with a four-cell-wide opening, twice the physical opening width of the two-cell variant at the same physical height. A muted gray-green rectangular tubular frame filled with simplified diagonal diamond wire mesh, with structural uprights across the longer leaf. A catcher post at the left edge and a guide post at the right edge, small bottom wheels on a straight ground rail. Two small handles on the two outer end frame tubes, on the same visible face. A short roller bracket on the guide post. The moving leaf ends at the two posts and has no rear tail. This is a single translating leaf, not two hinged leaves. Show the manual construction without a motor. Keep the rail compact and visually subordinate.
Style: restrained low-resolution isometric construction sprite matching muted Project Zomboid inventory art. Chunky pixel-like edges, simplified painted shading, gray/charcoal/subdued olive palette. Use a coarse readable diamond mesh rather than hundreds of hairline wires. Not photorealistic, not glossy, not a vector pictogram.
Composition: one isolated assembly on a square canvas, three-quarter isometric view from slightly above, front face extending from upper left toward lower right. It must have a visibly longer and lower horizontal silhouette than the two-cell icon; preserve the wide gate's proportions instead of stretching its height to fill the square. Center the assembly and fill roughly 85 percent of the available width with transparent padding. Clear at 64 pixels. No scene, fence extending beyond the gate or dimension markers.
Lighting: soft directional light from upper left; darker lower-right faces; subtle dark edge definition; no external cast shadow.
Constraints: one leaf only; closed pose; two edge posts; no central split, hinges, swing arc, overhead beam, tall gantry, moving upper carriage or electric drive. No text, numbers, labels, logos, watermark, background, floor or drawn checkerboard. Genuine transparent alpha outside the assembly and through the mesh. Deliver exactly one icon, not a sheet.
```
