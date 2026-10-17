# Adam Royal — standalone 3D game

Adam Royal is a standalone Unreal Engine game project, separate from any UEFN island or Fortnite Creative project.

## Initial implementation

- Unreal Engine C++ project/module skeleton.
- Replicated third-person character foundation.
- Server-authoritative hitscan firing request.
- Replicated health and elimination state placeholders.
- Keyboard/mouse input mappings (WASD, mouse look, Space jump, left-click hitscan fire).
- C++ third-person camera boom/follow camera and baseline movement tuning.
- Game mode foundation with a 100-player design target.

## Not implemented yet

- The Manila district generator now produces a real-geography GLB from OpenStreetMap data and packages it with procedural facade atlases and Wikimedia Commons facade reference photos. This is source geometry, not yet a native Unreal .umap level, and the reference photos are not yet mapped onto building meshes.
- Loot, inventory, production weapon models/animations, HUD, lobby, matchmaking, shrinking storm, bots, persistence, dedicated-server deployment, anti-cheat, audio, and optimization remain unfinished.
- The existing player model is `assets/saeed.glb` (about 17 MB). The workflow now stages this exact file as `Content/Characters/Saeed.glb` in the downloadable artifact. It is not yet a native Unreal skeletal-mesh asset: it must be imported through Unreal's glTF-capable pipeline (or converted in Blender), checked for skeleton/skin/animations, and assigned to the character mesh before the model is visible in gameplay.
- Controller mappings and console certification work.

## Verification truth

GitHub Actions can check source files and package source artifacts, but cannot compile Unreal C++ without a matching Unreal Engine installation and build toolchain. This code has not yet been compiled in Unreal Editor. Treat it as a starting implementation until a real Unreal build and multiplayer PIE test pass.

## First local validation

1. Install Unreal Engine using Epic Games Launcher on Windows.
2. Download a fresh, openly licensed city-area extract (not the old GLB) and save the source data in the repository.
3. Convert/import the new map data into Unreal assets and inspect scale, origin, roads, building geometry, and materials.
4. Save a real `.umap` level, add PlayerStarts and lighting, and set SaeedRoyaleGameMode as the map GameMode.
5. Import `Content/Characters/Saeed.glb` into Unreal (or convert it through Blender if required), verify the skeletal mesh, skeleton, materials and animations, and assign the resulting Unreal skeletal mesh to `ASaeedRoyaleCharacter`/a character Blueprint.
6. Compile the editor target and test Play-in-Editor before producing gameplay screenshots.
7. Use Play > Number of Players = 2 and run as a listen server to test replication and server-side damage.

## Platform plan

1. Windows prototype and repeatable multiplayer tests.
2. Battle-royale vertical slice: spawn flow, loot, inventory, weapons, storm, eliminations, win condition.
3. Dedicated-server and network/load tests.
4. PS5 only after approved PlayStation developer access and Sony SDK/tool access.

Official Unreal multiplayer guide: https://dev.epicgames.com/documentation/unreal-engine/multiplayer-programming-quick-start-for-unreal-engine

Official PS5 access requirements: https://dev.epicgames.com/documentation/unreal-engine/development-for-playstation-5-in-unreal-engine


## Real-world Manila district source

The map-generation workflow downloads current OpenStreetMap ways for a bounded central-Manila area, builds extruded building footprints and road geometry, and exports a GLB plus a provenance report into the workflow artifact `Adam-Royal-Manila-Central-District`. This is actual mapped geography, but buildings are procedural extrusions rather than photo-scanned assets. The workflow does not claim that Unreal has compiled or imported the GLB into a packaged game; the GLB is placed in the Unreal project's `Content/Maps` path in the generated artifact for editor import and review.

Map data © OpenStreetMap contributors, available under ODbL 1.0. See https://www.openstreetmap.org/copyright.

## City-data and texture workflow

The current automated pipeline is a **source-data generator and validation step**, not yet an Unreal gameplay build:

1. GitHub Actions checks out the repository and installs Python plus `requests`, `shapely`, `trimesh`, `mapbox-earcut`, `scipy`, `numpy`, and `pillow`.
2. `StandaloneBattleRoyale/Tools/build_manila_district.py` retrieves real mapped building footprints and road ways for the configured central-Manila bounding box from OpenStreetMap/Overpass, then creates 3D building extrusions and roads and exports `Manila-Central-District.glb` plus a JSON provenance/metrics report.
3. The generator creates procedural facade texture atlases (`Manila-Facade-Texture-*.jpg`) with Python Pillow. These add generic windows/concrete variation; they are **generated textures, not photographs of the actual buildings**.
4. `StandaloneBattleRoyale/Tools/fetch_manila_facade_photos.py` queries Wikimedia Commons for building-specific reference photos, downloads eligible files, and records source page, author and license details in `Content/Maps/Real-Facade-Photos/manifest.json`.
5. Quality checks verify that the GLB/report exist and contain a minimum number of buildings and roads, then upload the GLB, report, procedural texture atlases and reference-photo folder as the `Adam-Royal-Manila-Central-District` workflow artifact (retained for 30 days).

### Where the real-world data and images come from

- **Building footprints and roads:** OpenStreetMap via Overpass API. Attribution: © OpenStreetMap contributors; ODbL 1.0. https://www.openstreetmap.org/copyright
- **Building facade reference photographs:** Wikimedia Commons categories/pages for First United Building, Regina Building and Afable Building, accessed through the public Commons API. Each downloaded image must be checked against its own manifest entry for its source page, author and license; licenses and attribution requirements can differ by image. https://commons.wikimedia.org/
- **Procedural textures:** generated by the repository's Python/Pillow map-generation script; they are not downloaded photo textures and do not reproduce a specific facade.
- **No API key is intended to be required** for these OpenStreetMap/Overpass and Wikimedia Commons requests. External services can rate-limit or temporarily fail, so the workflow must be checked for a successful run and non-empty outputs.

### Important current limitation

The Wikimedia photos are currently **reference assets** packaged beside the GLB. They are not yet projected onto the corresponding 3D building meshes, and the generated facade atlases remain procedural. Therefore the current artifact does not yet guarantee authentic building signage, exact facade colors, or photogrammetric-level realism. Also, placing a GLB under `Content/Maps` does not by itself make it a native Unreal `.umap` level: import it in Unreal, inspect materials/collision/scale, configure lighting and gameplay actors, then test in Play-in-Editor before calling it playable. The GitHub workflow does not currently compile Unreal or capture actual gameplay screenshots.



## Street imagery collection and additional city-data sources (2026-10-17)

### Implemented in this repository

- `StandaloneBattleRoyale/Tools/fetch_manila_street_imagery.py` samples a grid across the same Manila district and queries the public KartaView / OpenStreetCam nearby-photo API. It attempts to download geolocated street-level photos (up to 180 images) from different grid points, records available coordinates, heading, capture date and source URL, and writes `Content/Maps/Street-Imagery/manifest.json`.
- `.github/workflows/validate-standalone-game.yml` runs this collector and includes the resulting `Street-Imagery` folder in the `Adam-Royal-Manila-Central-District` artifact.
- Wikimedia Commons collection remains in `StandaloneBattleRoyale/Tools/fetch_manila_facade_photos.py`. It searches for photos of First United Building, Regina Building and Afable Building, then records attribution/license metadata in `Real-Facade-Photos/manifest.json`. If Commons returns no usable photos, the step warns and continues; a successful workflow therefore does **not** guarantee that any photographs were downloaded.
- OpenStreetMap/Overpass supplies the currently implemented road and building-footprint geometry. Pillow-generated facade atlases are fallback procedural materials, not real photographs.
- The photo collectors create reference libraries only. They do **not** yet automatically match every photo to a specific building, reconstruct 3D buildings from photos, or apply the photos as in-game materials. Their manifests report downloaded assets separately from assets actually rendered in the game.

### Other useful sources evaluated for expanding coverage

These are documented as potential future inputs; they are **not** all integrated into the current generator:

1. **Overture Maps** — global building and transportation datasets, useful for broad building/road coverage and cross-checking OSM. Documentation: https://docs.overturemaps.org/guides/buildings/ ; explorer: https://explore.overturemaps.org/
2. **Microsoft Global ML Building Footprints** — large-scale building-footprint dataset; footprints alone do not provide real facade textures or complete 3D buildings. https://github.com/microsoft/GlobalMLBuildingFootprints
3. **OpenStreetMap / Overpass Turbo** — editable road/building map data and query interface. https://www.openstreetmap.org/ ; https://overpass-turbo.eu/
4. **KartaView** — street-level imagery; the collector above attempts public API access, but actual coverage and successful downloads vary by location/API availability. https://kartaview.org/ ; terms: https://kartaview.org/terms
5. **Mapillary** — another large street-level imagery source. API access, attribution, licensing and permitted reuse must be checked before automated download or redistribution. https://www.mapillary.com/ ; developer information: https://www.mapillary.com/developer
6. **Panoramax** — open street-level photo ecosystem; coverage depends on the city. https://panoramax.fr/
7. **Wikimedia Commons** — individually licensed building/street photographs with source and attribution metadata. https://commons.wikimedia.org/
8. **OpenAerialMap / Humanitarian OpenStreetMap Team imagery catalog** — aerial imagery useful for roofs, blocks and context, not a substitute for street-level facade photos. Check each imagery item's license and attribution. https://openaerialmap.org/ ; https://imagery.hotosm.org/
9. **OpenBuildingMap** — building-footprint/attribute exploration that can help identify buildings and compare data coverage. https://www.openbuildingmap.org/
10. **Google Photorealistic 3D Tiles** — visually rich 3D city coverage, but requires Google Maps Platform setup/API key and is governed by service-specific terms and usage restrictions. Do not scrape or bulk-extract tiles into the game; review official terms first. https://developers.google.com/maps/documentation/tile/3d-tiles

### Attribution and usage checks

- OSM data: © OpenStreetMap contributors, ODbL 1.0; https://www.openstreetmap.org/copyright
- Wikimedia Commons and street-photo assets: retain the source URL, creator, license and any attribution requirements for each item. Do not assume every image shares the same license.
- Before shipping downloaded imagery or embedding it in a distributable game, verify each asset's current license and the source service's terms. Publicly viewable does not automatically mean unrestricted redistribution.
- The build artifact is an intermediate research/source package, not proof that the images have been imported into Unreal or are visible during gameplay. A true gameplay screenshot still requires an Unreal project with the map and materials imported and rendered in the running game.

## سياسة حفظ خريطة مانيلا وإعادة استخدامها (2026-10-17)

- تم توليد خريطة مانيلا المركزية مرة واحدة وحفظ الناتج في المستودع تحت `Content/Maps`، بما يشمل `Manila-Central-District.glb` وتقرير البيانات وخامات الواجهات الإجرائية.
- **البناء العادي يعيد استخدام الملفات المحفوظة ولا يعيد تنزيل بيانات الخريطة أو توليدها من جديد.** يجب أن يبقى البناء قابلاً للتكرار من الأصول المخزنة في Git.
- لا تُحدّث الخريطة أو الخامات إلا عند طلب تغيير فعلي للخريطة أو إضافة/تعديل محتواها، ثم تُراجع النتيجة وتُحفظ النسخة الجديدة في المستودع لإعادة استخدامها في عمليات البناء التالية.
- خيار التشغيل اليدوي `refresh_map_assets` مخصص فقط عندما نقرر صراحة إعادة توليد الخريطة والخامات. لا تفعّله في عمليات البناء الاعتيادية.
- صور واجهات المباني وصور الشوارع أصول مرجعية منفصلة عن الخريطة. خيار `refresh_reference_photos` مخصص لتحديث هذه الصور فقط، ولا يعني أن الصور طُبقت على المجسمات داخل اللعبة.
- إذا كانت ملفات الخريطة المحفوظة مفقودة أو تالفة، يجب إظهار فشل واضح والتنبيه إلى الحاجة لاستعادة الأصول أو تشغيل تحديث مقصود؛ لا ينبغي اعتبار إعادة التوليد الصامتة سلوكاً عادياً.

## سياسة لقطات التحقق من اللعبة

- يجب التمييز بين **صورة/ملف مصدر الخريطة** وبين لقطة شاشة ملتقطة من لعبة تعمل فعلياً. وجود GLB أو صور مرجعية في المستودع لا يثبت أن اللعبة عرضتها.
- يجب أن تنتج اختبارات التشغيل الفعلية لقطات مستقلة تُظهر: (1) مشهداً داخل اللعبة، (2) الشخصية داخل العالم، و(3) مواقع مختلفة من خريطة مانيلا. تُحفظ اللقطات كـ GitHub Actions Artifacts لتسهيل مراجعتها.
- لا يُعلن نجاح تصوير اللعبة إلا بعد التحقق من ملفات الصور نفسها ومحتواها؛ ولا تُقبل صور الخريطة المصدرية أو صور Wikimedia بديلاً عن لقطات اللعب.
- **الوضع الحالي بعد Workflow run #43:** نجح فحص مصدر الخريطة، وسجّل التقرير 4,340 مبنى و3,028 طريقاً، لكن الـ Workflow الحالي لا يشغّل Unreal Engine ولا يلتقط صوراً من داخل اللعب. لذلك لم تُثبت بعد لقطات داخل اللعبة أو لقطات للشخصية أثناء اللعب.

### إصلاح التحقق من لقطات اللعب (2026-10-17)

أُضيف إلى Workflow فحص إلزامي بعد اختبارات المصدر: يجب وجود مستوى Unreal أصلي بامتداد `.umap` وثلاث لقطات شاشة على الأقل في `StandaloneBattleRoyale/Saved/GameplayScreenshots`، بحجم معقول، قبل اعتبار البناء ناجحاً. اللقطات المطلوبة يجب أن تُظهر اللعب والشخصية وموقعاً آخر من مانيلا؛ لا تُقبل صور المرجع أو ملفات GLB بدلاً منها.

**تنبيه تنفيذي:** هذا الفحص يمنع النجاح الكاذب لكنه لا يشغّل Unreal ولا يلتقط الصور بنفسه. المستودع حتى هذا التحديث لا يحتوي مستوى `.umap` جاهزاً، وبيئة GitHub-hosted الحالية لا تتضمن تثبيت Unreal Engine مُهيّأً للمشروع. لذلك من المتوقع أن يفشل الفحص الجديد إلى أن يُستورد GLB إلى مستوى Unreal قابل للتشغيل، وتُجهّز بيئة Windows بها Unreal Engine، ويُضاف مشغّل التقاط فعلي يحفظ الصور المطلوبة في المسار المحدد. لا يجوز وصف الصور بأنها أُنتجت حتى تظهر الملفات وتُراجع.

## Creating the native Manila Unreal level

The committed GLB is source geometry, not a native Unreal level. To create the actual binary `.umap` asset, use the matching Unreal Engine installation on Windows:

1. Open `StandaloneBattleRoyale/SaeedRoyale.uproject` in Unreal Editor and allow the enabled Python Editor Scripting and GLTF/Interchange plugins to initialize. If Unreal reports an unavailable plugin, enable the equivalent GLTF/Interchange importer shipped with that exact engine version and restart the editor.
2. Confirm `Content/Maps/Manila-Central-District.glb` exists. The workflow caches this file; do not redownload it for normal builds.
3. In Unreal Editor, open **Tools → Execute Python Script** and run `Tools/create_manila_playable_level.py` (path relative to this project folder).
4. The script attempts to import the GLB, create `/Game/Maps/ManilaCentral`, place imported static meshes, add lighting and a PlayerStart, and save the native level. It deliberately raises an error if import produces no usable static meshes; an empty level must not be reported as success.
5. Open `Content/Maps/ManilaCentral.umap` and inspect the district scale, mesh placement, road/building materials and player start. If the GLB importer returns separate meshes without preserving their source transforms, correct their placement before treating the level as playable.
6. The script does **not** claim the character GLB has been imported as a skeletal mesh or assigned to the pawn. That is a separate required Unreal Editor step before gameplay screenshots can prove the character is visible.

**Verification status:** committing this script and enabling plugins does not itself create the binary `.umap`. The level only exists after the script succeeds inside a compatible Unreal Editor. A hosted GitHub runner without Unreal Engine cannot generate a valid native level from the GLB alone.

