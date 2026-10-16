# إعداد شخصية Saeed كـ NPC داخل جزيرة UEFN

> **تنبيه مهم:** وجود `assets/saeed.glb` في GitHub لا يعني أن الشخصية أصبحت داخل الجزيرة. يجب تنفيذ الاستيراد داخل Unreal Editor for Fortnite (UEFN) على Windows. كما أن دعم استيراد GLB مباشرةً يختلف عن مسار استيراد Skeletal Mesh؛ لا تفترض أن GLB يمكن تعيينه مباشرةً إلى NPC.

## 1. تجهيز الأصل

من جذر نسخة المستودع على Windows:

```powershell
powershell -ExecutionPolicy Bypass -File Tools/Download-SaeedAsset.ps1
python Tools/validate_glb.py assets/saeed.glb --json
```

احتفظ بنسخة أصلية غير معدلة من GLB. افتحه في Blender وافحص:
- أن المجسم والـ Armature ظاهرين وأن الـ mesh مرتبط بالـ armature الصحيح.
- اتجاه المحور، القياس، نقطة الارتكاز، والوقوف على الأرض.
- أسماء العظام وتسلسلها، ووجود Skin weights سليمة.
- الخامات والصور والعيون والأسنان واللسان.
- الحركات وShape Keys/Morph Targets.

## 2. إنشاء نسخة استيراد متوافقة

1. افتح Blender واستورد `assets/saeed.glb` من **File → Import → glTF 2.0**.
2. لا تغيّر الأصل مباشرةً؛ نفّذ أي تعديل على نسخة عمل منفصلة.
3. إذا كان إصدار UEFN لديك لا يقبل GLB كسكِلِتون/مجسم قابل للاستخدام، جهّز نسخة FBX من Blender عبر **File → Export → FBX** وفق مسار Unreal Engine الموثق لإصدارك.
4. قبل التصدير، اختر الـ mesh والـ armature المطلوبين فقط، وتأكد من أن الـ mesh مرتبط بالـ armature وأن الـ transforms والـ rest pose صحيحة. اضبط إعدادات FBX وفق متطلبات Unreal/UEFN الحالية.
5. اختبر الاستيراد أولًا في مشروع تجريبي. لا تفترض أن Shape Keys أو جميع الحركات أو المواد ستنتقل؛ سجل ما فُقد وما يحتاج إعادة إعداد.

**لا يوجد حتى الآن ملف FBX معتمد أو إثبات أن تحويل GLB إلى FBX يحافظ على كل خصائص سعيد.** لا تستبدل الأصل الأصلي ولا تعلن نجاح التحويل قبل معاينة الناتج.

## 3. استيراد الأصل في UEFN

1. افتح UEFN وأنشئ مشروع جزيرة تجريبيًا أو افتح مشروعك.
2. من Content Browser استورد ملف FBX/الأصل الذي أثبتت صلاحيته في الخطوة السابقة، واتبع نافذة Import Options.
3. تحقق من ظهور Skeletal Mesh والـ Skeleton والمواد. افتح الـ Skeleton وتأكد من سلامة hierarchy والـ weights.
4. استورد الحركات بصورة منفصلة إن لزم، مع اختيار الـ Skeleton المطابق تمامًا. اختبر كل حركة منفردة.
5. إذا فشل الاستيراد، احتفظ برسالة الخطأ وسجل UEFN قبل تغيير الملف.

## 4. إعداد NPC داخل الجزيرة

1. أنشئ NPC Character Definition من القوالب/الأدوات المتاحة في إصدار UEFN المثبت.
2. اختر مظهرًا أو Character Asset يدعمه نظام NPC في هذا الإصدار. **لا تفترض أن أي Skeletal Mesh مخصص يمكن تعيينه مباشرةً إلى NPC Fortnite**؛ إذا لم يظهر خيار تعيين المجسم المستورد، فهذا قيد توافق يجب حله أولًا وليس خطأ في ملف Verse.
3. أضف NPC Spawner إلى الجزيرة واضبط Character Definition وموقع الظهور.
4. أضف `Verse/saeed_npc_behavior.verse` إلى مشروع Verse في UEFN. اربط السلوك بتعريف الشخصية عبر الواجهة التي يوفرها الإصدار.
5. اضغط Build/Compile في Verse وأصلح أخطاء المترجم كما هي؛ هذا المستودع لا يستطيع ترجمة Verse باستخدام GitHub Actions وحدها.
6. ابدأ جلسة UEFN واختبر ظهور NPC والملاحة والتصادم والرسوم. تحقق أن نقطة التجوال تقع ضمن أرض قابلة للمشي.

## 5. شروط إعلان النجاح

لا تعتبر المهمة مكتملة إلا بعد حفظ دليل على:
- إصدار UEFN المستخدم واسم مشروع الجزيرة.
- أسماء الأصول التي أنشأها الاستيراد وأي تحذيرات.
- نجاح Verse Build/Compile.
- ظهور سعيد في جلسة لعب فعلية، وصحة المظهر والحجم والاتجاه.
- نجاح الملاحة وإعادة الظهور.
- نتيجة فحص كل حركة وخامة وShape Key مطلوب.

## مراجع

- [Create custom NPC behavior in UEFN](https://dev.epicgames.com/documentation/fortnite/create-custom-npc-behavior-in-unreal-editor-for-fortnite?lang=en-US)
- [Importing assets into Unreal Editor for Fortnite](https://dev.epicgames.com/documentation/fortnite/importing-assets-in-unreal-editor-for-fortnite)
- [IMPORT-CHECKLIST.md](IMPORT-CHECKLIST.md)
