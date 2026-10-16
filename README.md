# Saeed Fortnite

مشروع مستقل لتجهيز شخصية **Saeed** كـ NPC داخل جزيرة Fortnite باستخدام Unreal Editor for Fortnite (UEFN).

## الهدف

- استيراد نموذج Saeed الأصلي والتحقق من توافقه مع UEFN.
- إعداد NPC مخصص داخل جزيرة UEFN، وليس Fortnite Battle Royale skin.
- ربط الشخصية بالحركات المناسبة واختبار الخامات والهيكل العظمي.
- إضافة سلوك NPC عبر Verse بعد التحقق من واجهات UEFN المستخدمة.

## أصل الشخصية

تم نسخ ملف الشخصية الأصلي من مستودع `saeedhub101/Saeed-V2.0` إلى:

`assets/Saeed_AI-3D.glb`

الحجم المتوقع للنسخة المصدرية: **17,232,556 bytes**. اجتاز الاستيراد الآلي فحص حجم الملف وترويسة GLB (`glTF`). هذا لا يثبت بعد توافق النموذج أو كل الحركات وMorph Targets مع UEFN.

## الحالة الحالية

- [x] تجهيز المستودع المستقل والفرع `main`.
- [x] إضافة ملف الشخصية الأصلي إلى `assets/Saeed_AI-3D.glb`.
- [x] إضافة أداة Python لفحص بنية GLB وتقرير الحجم وSHA-256 والعُقد والهيكل والحركات وMorph Targets.
- [x] إضافة اختبارات وحدات للأداة وفحص آلي عبر GitHub Actions.
- [x] إضافة مسودة Verse أولية لحركة NPC؛ لم تُترجم أو تُختبر داخل UEFN بعد.
- [x] إضافة دليل إعداد UEFN وقائمة تحقق للاستيراد.
- [ ] إنشاء مشروع/جزيرة UEFN على جهاز Windows باستخدام UEFN.
- [ ] استيراد النموذج الفعلي وفحص المواد والـ skeleton والـ morph targets.
- [ ] ربط نموذج NPC بتعريف الشخصية وNPC Spawner.
- [ ] اختبار الحركات والسلوك داخل الجزيرة وجلسة Fortnite.

## أدوات المطور

- `assets/Saeed_AI-3D.glb`: نموذج الشخصية المصدر.
- `Verse/saeed_npc_behavior.verse`: مسودة حركة تجوال محدودة حول نقطة الظهور.
- `Tools/Download-SaeedAsset.ps1`: أداة اختيارية لإعادة جلب الأصل من المستودع المصدر والتحقق من ترويسة الملف وحساب SHA-256.
- `Tools/validate_glb.py`: فحص بنيوي لملفات GLB دون مكتبات خارجية.
- `Tests/test_validate_glb.py`: اختبارات آلية للحالات الصحيحة والتالفة.
- `.github/workflows/asset-tooling.yml`: يشغّل الاختبارات وفحص صياغة أداة Windows.
- `.github/workflows/import-saeed-character.yml`: مسار استيراد الأصل إلى هذا المستودع.

تشغيل أدوات الفحص محلياً يتطلب Python للمطور فقط؛ لا توجد متطلبات Python للمستخدم النهائي أو للاعب.

## حدود مهمة

فحص بنية GLB لا يثبت أن UEFN يدعم كل الحركات أو الخامات أو Morph Targets. GitHub Actions لا ينشئ جزيرة UEFN ولا يختبرها داخل Fortnite. يلزم الاستيراد الفعلي في UEFN على Windows قبل إعلان توافق الأصل أو نجاح الـ NPC.

راجع `Docs/UEFN-SETUP.md` و`Docs/IMPORT-CHECKLIST.md` لإكمال الاستيراد وتسجيل نتائج الاختبارات الفعلية.
