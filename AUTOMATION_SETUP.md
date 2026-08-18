# 🤖 CalliQ-AI - Automation Setup Guide

## 🚀 خيارين للأتمتة المتاحة:

### الخيار 1: GitHub Actions (أتمتة كاملة تلقائية)
- يتم تشغيله تلقائياً عند كل push إلى main
- يتطلب إعداد GitHub secrets
- الأفضل للنشر المستمر

### الخيار 2: السكريبت المحلي (تحكم يدوي)
- تشغيل من جهازك المحلي
- يتطلب إعداد متغيرات البيئة
- الأفضل للنشر عند الطلب

---

## 🔑 الخطوة 1: الحصول على مفاتيح API

### 1.1 Render API Key (مطلوب للأتمتة)
1. اذهب إلى: https://dashboard.render.com/user/settings
2. سجل الدخول بحسابك
3. اضغط "Create API Key"
4. أعطِ اسماً للمفتاح (مثلاً: "CalliQ-AI Automation")
5. انسخ المفتاح الذي سيظهر (يظهر مرة واحدة فقط!)

### 1.2 Groq API Key (مطلوب للتطبيق)
1. اذهب إلى: https://console.groq.com/keys
2. سجل الدخول أو أنشئ حساب جديد (مجاني)
3. اضغط "Create API Key"
4. أعطِ اسماً للمفتاح
5. انسخ المفتاح

### 1.3 Gemini API Key (اختياري)
1. اذهب إلى: https://aistudio.google.com/apikey
2. سجل الدخول بحساب Google
3. اضغط "Create API Key"
4. انسخ المفتاح

---

## 🤖 الخيار 1: إعداد GitHub Actions

### الخطوة 1: إضافة GitHub Secrets
1. اذهب إلى مستودع GitHub: https://github.com/krymjwdh098-cmyk/CalliQ-AI
2. اضغط على "Settings"
3. في القائمة اليسرى، اضغط "Secrets and variables" → "Actions"
4. اضغط "New repository secret"
5. أضف الأسرار التالية:

#### السر الأول: RENDER_API_KEY
- **Name**: `RENDER_API_KEY`
- **Value**: المفتاح الذي حصلت عليه من Render
- اضغط "Add secret"

#### السر الثاني: GROQ_API_KEY (اختياري - سيتم إضافته لاحقاً)
- **Name**: `GROQ_API_KEY`
- **Value**: المفتاح الذي حصلت عليه من Groq
- اضغط "Add secret"

### الخطوة 2: تشغيل الـ Workflow يدوياً (لأول مرة)
1. في مستودع GitHub، اضغط على "Actions"
2. اختر workflow "Render Auto-Deploy"
3. اضغط "Run workflow"
4. اختر فرع "main"
5. اضغط "Run workflow" الأخضر

### الخطوة 3: مراقبة النشر
1. انتظر حتى يكتمل الـ workflow (قد يستغرق 5-10 دقائق)
2. يمكنك رؤية التقدم مباشرة
3. بعد النجاح، ستظهر الخدمات في Render Dashboard

### الخطوة 4: إضافة مفاتيح LLM في Render
بعد نجاح النشر الأول:
1. اذهب إلى: https://dashboard.render.com
2. اختر خدمة "calliq-api"
3. اضغط "Environment"
4. أضف:
   - **Key**: `GROQ_API_KEY`
   - **Value**: مفتاح Groq
5. أضف (اختياري):
   - **Key**: `GEMINI_API_KEY`
   - **Value**: مفتاح Gemini
6. اضغط "Save Changes"
7. اضغط "Manual Deploy" → "Clear build cache & deploy"

---

## 💻 الخيار 2: إعداد السكريبت المحلي

### على Windows:
```powershell
# 1. افتح PowerShell كمسؤول

# 2. اضبط متغيرات البيئة
$env:RENDER_API_KEY = "your-render-api-key"
$env:GROQ_API_KEY = "your-groq-api-key"
$env:GEMINI_API_KEY = "your-gemini-api-key" # اختياري

# 3. شغّل السكريبت
.\auto-deploy.ps1
```

### على Linux/Mac:
```bash
# 1. اجعل السكريبت قابلاً للتنفيذ
chmod +x auto-deploy.sh

# 2. اضبط متغيرات البيئة
export RENDER_API_KEY="your-render-api-key"
export GROQ_API_KEY="your-groq-api-key"
export GEMINI_API_KEY="your-gemini-api-key" # اختياري

# 3. شغّل السكريبت
./auto-deploy.sh
```

---

## 🔍 التحقق من النشر

### بعد النشر، تحقق من الخدمات:
1. **Frontend**: https://calliq-frontend.onrender.com
2. **Backend API**: https://calliq-api.onrender.com
3. **API Docs**: https://calliq-api.onrender.com/api/docs
4. **Health Check**: https://calliq-api.onrender.com/health

### تسجيل الدخول:
- **Email**: `demo@company.com`
- **Password**: `demo1234`

---

## 🛠️ حل المشاكل

### مشكلة: RENDER_API_KEY غير صالح
**الحل**:
- تأكد من نسخ المفتاح بشكل صحيح
- تأكد من أن المفتاح نشط في Render Dashboard
- إذا نسيت المفتاح، أنشئ واحداً جديداً

### مشكلة: GitHub Actions يفشل
**الحل**:
- تحقق من أن Secrets تمت إضافتها بشكل صحيح
- راجع logs الـ workflow في GitHub
- تأكد من أن render.yaml صالح

### مشكلة: السكريبت المحلي يفشل
**الحل**:
- تأكد من تثبيت Render CLI
- تحقق من متغيرات البيئة
- تأكد من الاتصال بالإنترنت

### مشكلة: الخدمات لا تعمل بعد النشر
**الحل**:
- تحقق من logs الخدمات في Render Dashboard
- تأكد من إضافة مفاتيح LLM API
- حاول manual deploy بعد إضافة المفاتيح

---

## 📞 الدعم

- **Render Docs**: https://docs.render.com
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Render CLI Docs**: https://render.com/docs/cli
- **مشروع GitHub**: https://github.com/krymjwdh098-cmyk/CalliQ-AI

---

## 🎉 التالي بعد النشر

بعد نجاح النشر:
1. ✅ اختبر التطبيق بالكامل
2. ✅ أضف مستخدمين حقيقيين
3. ✅ قم بتخصيص الـ UI حسب احتياجاتك
4. ✅ اضبط إعدادات الـ LLM حسب تفضيلاتك
5. ✅ قم بإعداد النسخ الاحتياطي (إذا升级 للـ paid plan)

---

## 💰 تذكير التكلفة

هذا التكوين مصمم ليكون **مجاناً بالكامل**:
- GitHub Actions: Free tier
- Render Free Tier: $0/شهر
- Groq API: Free tier
- Gemini API: Free tier

**التكلفة الشهرية المتوقعة**: $0

---

## 🔄 التحديثات المستقبلية

عندما تريد تحديث التطبيق:
- **GitHub Actions**: فقط push إلى main، والباقي تلقائي!
- **السكريبت المحلي**: شغّل `auto-deploy.ps1` أو `auto-deploy.sh` مرة أخرى

---

## 🚀 أنت جاهز الآن!

ابدأ بالخطوات أعلاه وسيتم نشر تطبيق CalliQ-AI الخاص بك تلقائياً! 🎊
