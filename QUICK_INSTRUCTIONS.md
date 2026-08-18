# 🚀 تعليمات سريعة لنشر CalliQ-AI

## الخطوة 1: إضافة المفاتيح كـ GitHub Secrets

### Secret 1: Render API Key
1. اذهب إلى: https://github.com/krymjwdh098-cmyk/CalliQ-AI/settings/secrets/actions
2. اضغط "New repository secret"
3. أدخل:
   - **Name**: `RENDER_API_KEY`
   - **Value**: `rnd_wuOuHV7KM7TWYpPHi8DEm0JNGp5`
4. اضغط "Add secret"

### Secret 2: Groq API Key
1. في نفس الصفحة، اضغط "New repository secret" مرة أخرى
2. أدخل:
   - **Name**: `GROQ_API_KEY`
   - **Value**: `gsk_vuNprvL7eiQmifV3WwtcWGdy3FYdJha2BYNQs865vKjdbIDIQCU`
3. اضغط "Add secret"

## الخطوة 2: تشغيل الـ Workflow يدوياً

1. اذهب إلى: https://github.com/krymjwdh098-cmyk/CalliQ-AI/actions
2. اختر workflow "Render Auto-Deploy"
3. اضغط "Run workflow"
4. اختر فرع "main"
5. اضغط "Run workflow" الأخضر

## الخطوة 3: مراقبة النشر

1. انتظر حتى يكتمل الـ workflow (5-10 دقائق)
2. راقب التقدم مباشرة في GitHub Actions
3. بعد النجاح، ستظهر الخدمات في Render Dashboard

## 🎉 النتيجة

- **Frontend**: https://calliq-frontend.onrender.com
- **Backend**: https://calliq-api.onrender.com
- **API Docs**: https://calliq-api.onrender.com/api/docs

**الآن جاهز للاستخدام!** 🚀
