# 🚀 نشر CalliQ-AI على Replit (مجاني بالكامل)

## 📋 لماذا Replit؟

- ✅ **مجاني بالكامل** - لا يحتاج بطاقة ائتمان
- ✅ **سهل جداً** - واجهة بسيطة وسهلة الاستخدام
- ✅ **يدعم Python** - مثالي لمشروع FastAPI
- ✅ **قاعدة بيانات مجانية** - PostgreSQL مجاني
- ✅ **دعم Git** - يربط مباشرة بـ GitHub

---

## 🎯 الخطوات البسيطة:

### الخطوة 1: إنشاء حساب Replit
1. اذهب إلى: **https://replit.com**
2. اضغط **"Sign up"**
3. سجل باستخدام:
   - Email
   - أو Google
   - أو GitHub

### الخطوة 2: إنشاء Replit جديد
1. بعد تسجيل الدخول، اضغط **"+ Create Repl"**
2. اختر **"Import from GitHub"**
3. اربط حساب GitHub إذا طلب ذلك
4. ابحث عن مستودع: **`CalliQ-AI`**
5. اضغط **"Import"**

### الخطوة 3: إعداد Backend
1. سيقوم Replit باستيراد المشروع تلقائياً
2. في شريط الأدوات، اضغط **"Files"**
3. افتح ملف **`Backend/main.py`**
4. في الجزء العلوي، اضغط **"Run"**

### الخطوة 4: إضافة متغيرات البيئة
1. في شريط الأدوات، اضغط **"Secrets"** (أيقونة القفل)
2. أضف المتغيرات التالية:

#### المتغيرات المطلوبة:
- **Key**: `DATABASE_URL`
  - **Value**: `sqlite:///./talentai.db`

- **Key**: `SECRET_KEY`
  - **Value**: أنشئ مفتاح عشوائي (يمكنك استخدام: `python -c "import secrets; print(secrets.token_urlsafe(64))"`)

- **Key**: `GROQ_API_KEY`
  - **Value**: `gsk_vuNprvL7eiQmifV3WwtcWGdy3FYdJha2BYNQs865vKjdbIDIQCU`

#### المتغيرات الاختيارية:
- **Key**: `GEMINI_API_KEY`
  - **Value**: (إذا كان لديك مفتاح Gemini)

- **Key**: `ENVIRONMENT`
  - **Value**: `production`

- **Key**: `DEBUG`
  - **Value**: `false`

### الخطوة 5: تثبيت الاعتماديات
1. Replit سيكتشف تلقائياً ملف `requirements.txt`
2. سيقوم بتثبيت الحزم تلقائياً
3. انتظر حتى يكتمل التثبيت

### الخطوة 6: تشغيل التطبيق
1. في شريط الأدوات، اضغط **"Run"**
2. سيبدأ التطبيق تلقائياً
3. ستحصل على رابط ويب: `https://your-repl-name.username.replit.co`

### الخطوة 7: نشر Frontend (اختياري)
للأسف، Replit لا يدعم نشر Frontend React بسهولة مع Backend في نفس الـ Repl.

**الخيارات:**
1. **استخدم Backend فقط** - واجهة API فقط
2. **افصل Frontend** - انشئ Replit منفصل للـ Frontend
3. **استخدم Netlify** - نشر Frontend مجاناً على Netlify

---

## 🎯 الوصول إلى التطبيق:

بعد التشغيل، ستحصل على:
- **Backend API**: `https://your-repl-name.username.replit.co`
- **API Docs**: `https://your-repl-name.username.replit.co/api/docs`

---

## 🔧 حل المشاكل:

### إذا لم يعمل التطبيق:
1. تحقق من تثبيت الاعتماديات
2. تأكد من متغيرات البيئة
3. راجع logs في Terminal

### إذا ظهرت أخطاء في قاعدة البيانات:
1. حذف ملف `talentai.db` في مجلد Backend
2. أعد تشغيل التطبيق

---

## 💰 التكلفة:

**مجاناً بالكامل!** $0/شهر

---

## 🚀 مميزات Replit:

- ✅ بيئة تطوير متكاملة
- ✅ دعم Git مدمج
- ✅ قاعدة بيانات PostgreSQL مجانية
- ✅ سهولة المشاركة
- ✅ واجهة جميلة وسهلة

---

## 📝 الخطوة التالية بعد النشر:

1. اختبر الـ API: `https://your-repl-name.username.replit.co/api/docs`
2. استخدم بيانات الدخول الافتراضية:
   - Email: `demo@company.com`
   - Password: `demo1234`

---

## 🎉 تهانينا!

بعد إكمال هذه الخطوات، سيكون تطبيق CalliQ-AI الخاص بك يعمل على Replit مجاناً!

---

## 🔄 التحديثات:

عندما تريد تحديث التطبيق:
1. ادفع التغييرات إلى GitHub
2. في Replit، اضغط **"Git"** → **"Pull"**
3. Replit سيحدث التطبيق تلقائياً
