# Saeed Fortnite

تجهيز أصل شخصية Saeed وتجربة استخدامه كـ NPC داخل جزيرة Fortnite باستخدام Unreal Editor for Fortnite (UEFN).

## الأصل والأدوات

- `assets/saeed.glb`: الأصل الأصلي، احتفظ به دون تعديل.
- [تنزيل GLB مباشرة](https://raw.githubusercontent.com/saeedhub101/Saeed-Fortnite-/main/assets/saeed.glb)
- `Tools/Download-SaeedAsset.ps1`: تنزيل الأصل والتحقق من ترويسة الملف وبصمة SHA-256.
- `Tools/validate_glb.py`: فحص بنية GLB؛ لا يثبت توافق UEFN.
- `Tests/test_validate_glb.py`: اختبارات أداة الفحص.
- `Verse/saeed_npc_behavior.verse`: مسودة سلوك تجوال، لم تُترجم داخل UEFN بعد.
- `Docs/UEFN-SETUP.md`: خطوات تجهيز الأصل والاستيراد وربط NPC.
- `Docs/IMPORT-CHECKLIST.md`: قائمة قبول يجب إكمالها داخل المحرر.

## الحالة الفعلية

- [x] حفظ أصل GLB في هذا المستودع وتوحيد الاسم.
- [x] إضافة أدوات فحص آلية وGitHub Actions.
- [x] نجاح الفحوصات الآلية الحالية الخاصة ببنية الملف وأدواته.
- [ ] تجهيز وتأكيد صيغة استيراد متوافقة مع إصدار UEFN المثبت.
- [ ] إنشاء/تحديث مشروع جزيرة UEFN فعلي.
- [ ] ربط المظهر المدعوم بـ NPC Character Definition وNPC Spawner.
- [ ] ترجمة Verse واختبار NPC داخل جلسة لعب.

## حدود واضحة

GitHub Actions تفحص الملفات والنصوص فقط؛ لا تشغّل UEFN ولا تستورد الشخصية داخل جزيرة ولا تترجم Verse باستخدام محرر Epic. لا يوجد في المستودع حتى الآن مشروع جزيرة UEFN موثق أو FBX تم التحقق من مطابقته. لذلك لا يجوز وصف سعيد بأنه ظهر داخل Fortnite قبل نجاح الاختبار داخل المحرر.

ابدأ من [دليل الإعداد](Docs/UEFN-SETUP.md) ثم أكمل [قائمة التحقق](Docs/IMPORT-CHECKLIST.md).
