# Saeed Fortnite

مستودع مستقل لتجهيز شخصية **Saeed** كـ NPC داخل جزيرة Fortnite باستخدام Unreal Editor for Fortnite (UEFN).

## أصل الشخصية

ملف الشخصية موجود في هذا المستودع:

`assets/saeed.glb`

رابط التنزيل المباشر:
https://raw.githubusercontent.com/saeedhub101/Saeed-Fortnite-/main/assets/saeed.glb

يُستخدم هذا المستودع الآن كمصدر استرجاع الشخصية؛ لا يحتاج سكربت التنزيل إلى الرجوع إلى مستودع `Saeed-V2.0`.

## الحالة

- [x] نسخ أصل الشخصية إلى هذا المستودع وتوحيد اسمه إلى `saeed.glb`.
- [x] توفير رابط تنزيل مباشر من مستودع Fortnite.
- [x] توفير سكربت Windows لتنزيل الأصل والتحقق من ترويسة GLB وحساب SHA-256.
- [x] إضافة أداة فحص بنية GLB واختبارات وحدات وGitHub Actions.
- [x] إضافة مسودة سلوك Verse أولية.
- [ ] إنشاء مشروع/جزيرة UEFN فعلية على Windows.
- [ ] التحقق من استيراد الهيكل والخامات والحركات وMorph Targets.
- [ ] ربط NPC Character Definition وNPC Spawner.
- [ ] اختبار NPC داخل جلسة Fortnite.

## أدوات المطور

- `assets/saeed.glb`: ملف الشخصية.
- `Tools/Download-SaeedAsset.ps1`: تنزيل الأصل من مستودع Fortnite الحالي.
- `Tools/validate_glb.py`: فحص بنيوي لملفات GLB.
- `Tests/test_validate_glb.py`: اختبارات آلية.
- `Verse/saeed_npc_behavior.verse`: مسودة تجوال NPC؛ لم تُترجم أو تُختبر داخل UEFN بعد.
- `Docs/UEFN-SETUP.md` و`Docs/IMPORT-CHECKLIST.md`: خطوات الإعداد والاختبار.

## حدود مهمة

فحص GLB آلياً لا يثبت أن UEFN يدعم كل الحركات أو الخامات أو Morph Targets. يجب الاستيراد الفعلي داخل UEFN ثم اختبار NPC في جلسة لعب قبل اعتبار الجزيرة جاهزة.
