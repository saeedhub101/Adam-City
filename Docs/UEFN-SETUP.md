# إعداد جزيرة Saeed داخل UEFN

هذه الخطوات تجهز أصل الشخصية ثم تختبره داخل Unreal Editor for Fortnite على Windows. ملفات GitHub وحدها لا تنشئ مشروع UEFN أو جزيرة قابلة للتشغيل.

## 1. جلب ملف الشخصية

من جذر نسخة مستودع `Saeed-Fortnite-` على Windows، شغّل:

```powershell
powershell -ExecutionPolicy Bypass -File Tools/Download-SaeedAsset.ps1
```

سيتم تنزيل الأصل المعتمد من هذا المستودع نفسه:
`assets/saeed.glb`

رابط التنزيل المباشر:
https://raw.githubusercontent.com/saeedhub101/Saeed-Fortnite-/main/assets/saeed.glb

يفحص السكربت ترويسة GLB ويطبع بصمة SHA-256. لا يحتاج اللاعب أو المستخدم النهائي إلى Python أو Node.js أو PowerShell؛ هذه أداة إعداد للمطور فقط.

## 2. استيراد الأصل في UEFN

1. افتح UEFN وأنشئ مشروع جزيرة حقيقياً أو افتح مشروعك الحالي.
2. استورد `saeed.glb` من متصفح المحتوى/مسار الاستيراد الذي يدعمه إصدار UEFN لديك.
3. تحقق من رسالة الاستيراد، والخامات، والاتجاه، والحجم، والـ skeleton، والـ morph targets.
4. افحص كل حركة مستوردة في المحرر. لا تفترض أن جميع حركات GLB أو Morph Targets مدعومة.
5. إذا رفض UEFN GLB أو لم يستورد الهيكل كما يلزم، استخدم مسار التحويل الذي يدعمه إصدار UEFN المثبت، ثم أعد اختبار الأصل المحول.

## 3. إعداد NPC

1. أنشئ/اختر NPC Character Definition مدعوماً في إصدار UEFN.
2. اربط نموذج الشخصية بعد التأكد من توافق الـ skeleton؛ لا تفترض أن أي GLB يمكن استخدامه مباشرةً كـ NPC.
3. أضف NPC Spawner إلى الجزيرة واضبطه على تعريف الشخصية.
4. أضف ملف Verse `Verse/saeed_npc_behavior.verse` إلى مشروع Verse في UEFN، ثم عالج أي اختلافات يطلبها مترجم الإصدار الفعلي.
5. اربط سلوك NPC بتعريف الشخصية أو آلية الإسناد التي يدعمها الإصدار.

## 4. الاختبار داخل جلسة اللعب

- شغّل Compile في UEFN وأصلح أخطاء Verse أو استيراد الأصول.
- ابدأ جلسة لعب واختبر ظهور NPC والملاحة والتوقف وعدم الخروج عن الجزيرة.
- اختبر الحركات والوجه والمواد، وسجّل أي شيء لم ينتقل من GLB.
- لا تعتبر نجاح GitHub Actions بديلاً عن هذا الاختبار الفعلي.

## مراجع

- https://dev.epicgames.com/documentation/fortnite/create-custom-npc-behavior-in-unreal-editor-for-fortnite?lang=en-US
- `Docs/IMPORT-CHECKLIST.md`
