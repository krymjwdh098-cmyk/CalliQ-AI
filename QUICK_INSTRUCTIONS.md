# 🚀 تعليمات سريعة لنشر CalliQ-AI

## الخطوة 1: إضافة Render API Key كـ GitHub Secret

1. اذهب إلى: https://github.com/krymjwdh098-cmyk/CalliQ-AI/settings/secrets/actions
2. اضغط "New repository secret"
3. أدخل:
   - **Name**: `RENDER_API_KEY`
   - **Value**: `rnd_wuOuHV7KM7TWYpPHi8DEm0JNGp5`
4. اضغط "Add secret"

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

## الخطوة 4: إضافة مفاتيح LLM

بعد نجاح النشر:
1. اذهب إلى: https://dashboard.render.com
2. اختر خدمة "calliq-api"
3. اضغط "Environment"
4. أضف `GROQ_API_KEY` من: https://console.groq.com/keys
5. أضف `GEMINI_API_KEY` (اختياري) من: https://aistudio.google.com/apikey
6. اضغط "Save Changes"
7. اضغط "Manual Deploy"

## 🎉 النتيجة

- **Frontend**: https://calliq-frontend.onrender.com
- **Backend**: https://calliq-api.onrender.com
- **API Docs**: https://calliq-api.onrender.com/api/docs

**الآن جاهز للاستخدام!** 🚀
