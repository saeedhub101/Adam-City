# النسخ المحسّنة لأجزاء المباني الأربعة

هذا المجلد يحتوي على نسخ إضافية مستقلة من أجزاء المباني الأربعة المستخدمة في صفحة `test.html`. **الملفات الأصلية في `../part1` إلى `../part4` لم تُستبدل**.

## الملفات

- `part1-detailed.glb` + `part1-detailed-report.json`
- `part2-detailed.glb` + `part2-detailed-report.json`
- `part3-detailed.glb` + `part3-detailed-report.json`
- `part4-detailed.glb` + `part4-detailed-report.json`
- `enhancement-report.json`: التقرير الإجمالي.

## طريقة الإنشاء

من جذر المستودع:

```bash
python3 -m pip install numpy trimesh shapely pyproj pillow mapbox-earcut
python3 complete_data/OSM/scripts/enhance_existing_glb_parts.py
```

يعتمد السكريبت على بصمات `complete_data/OSM/data/buildings/ermita-building-footprints.geojson`، وعلى المولّد المرجعي `ermita/scripts/generate_roxas_boulevard_buildings.py`. يحمّل كل GLB أصلي ويضيف طبقات تفاصيل جديدة إلى المشهد، ثم يحفظ الناتج هنا؛ ولا يكتب فوق ملفات GLB الأصلية.

## أنواع التفاصيل

- نوافذ كصفائح رباعية رقيقة مع خصائص PBR للزجاج.
- طبقات إجرائية للواجهة والمواد بحسب دوال المولّد المرجعي.
- زخارف واجهة وتفاصيل خاصة عند انطباق شروط الهوية/الوسوم.

## الإحداثيات

تستخدم النواتج أصل الإحداثيات نفسه لكل جزء أصلي. ملف الأصل المرجعي لكل جزء موجود في `../partN/partN-origin.json`. يقوم السكريبت بإزاحة هندسة الإضافات إلى الإطار المحلي ذاته ولا يقصد تعديل إحداثيات الهندسة الأصلية.

## تنبيه مهم

هذه طبقات إجرائية مضافة وليست إعادة بناء فوتوغرامترية لكل مبنى. تبقى هندسة ومواد GLB الأصلي موجودة؛ قد تظهر طبقات متداخلة حسب ترتيب العرض أو خصائص المشهد. يجب اختبار كل زر على صفحة `test.html` بعد النشر وعدم اعتبار نجاح التوليد إثباتًا للمطابقة البصرية.

لخريطة كل البيانات والفهارس والأرقام وخطوات العمل والقيود، راجع:
`../BUILDING-DATA-AUDIT-AND-ENHANCEMENT-LOG.md`.
