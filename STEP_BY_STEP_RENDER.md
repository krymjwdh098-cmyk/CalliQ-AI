# 🎯 خطوة بخطوة - نشر CalliQ-AI على Render

## الخطوة 1: التسجيل في Render
1. افتح المتصفح واذهب إلى: **https://dashboard.render.com/register**
2. اختر "Sign up with GitHub"
3. سجل الدخول بحساب GitHub الخاص بك
4. الموافقة على الأذونات المطلوبة
5. تحقق من إيميلك إذا طلب ذلك

## الخطوة 2: إنشاء Blueprint جديد
1. بعد تسجيل الدخول، ستظهر لوحة التحكم (Dashboard)
2. اضغط على زر **"New +"** في أعلى اليمين
3. اختر **"Blueprint"** من القائمة
4. سيطلب منك ربط حساب GitHub (إذا لم يكن مربوطاً)
5. اضغط **"Connect"** لحساب GitHub

## الخطوة 3: اختيار المستودع
1. بعد ربط GitHub، ستظهر قائمة بمستودعاتك
2. ابحث عن مستودع **"CalliQ-AI"**
3. اضغط على **"Connect"** بجانب المستودع
4. Render سيقرأ ملف `render.yaml` تلقائياً

## الخطوة 4: مراجعة التكوين
سيظهر لك عرض لما سيتم إنشاؤه:
- **calliq-api**: خدمة Backend (Python)
- **calliq-frontend**: موقع Frontend (Static)
- SQLite database (مدمج، لا يحتاج إنشاء منفصل)

1. راجع التكوين الموجود
2. تأكد من أن المخطط (Plan) هو **"Free"** للخدمات
3. اضغط **"Apply"** في الأسفل لبدء الإنشاء

## الخطوة 5: إضافة مفاتيح API
بعد إنشاء الخدمات:

### الحصول على Groq API Key (مجاني)
1. افتح: **https://console.groq.com/keys**
2. سجل الدخول أو أنشئ حساب جديد (مجاني)
3. اضغط **"Create API Key"**
4. أعطِ اسماً للمفتاح (مثلاً: "CalliQ-AI")
5. انسخ المفتاح الذي سيظهر

### إضافة المفتاح في Render
1. في Render Dashboard، اذهب إلى خدمة **"calliq-api"**
2. اضغط على تبويب **"Environment"**
3. اضغط **"Add Environment Variable"**
4. أضف:
   - **Key**: `GROQ_API_KEY`
   - **Value**: المفتاح الذي نسخته من Groq
5. اضغط **"Save Changes"**

### (اختياري) إضافة Gemini API Key
1. افتح: **https://aistudio.google.com/apikey**
2. سجل الدخول بحساب Google
3. اضغط **"Create API Key"**
4. انسخ المفتاح
5. في Render، أضف متغير بيئة:
   - **Key**: `GEMINI_API_KEY`
   - **Value**: مفتاح Gemini

## الخطوة 6: إعادة النشر
بعد إضافة مفاتيح API:
1. في خدمة **"calliq-api"**، اضغط **"Manual Deploy"**
2. اختر **"Clear build cache & deploy"**
3. انتظر حتى يكتمل النشر (قد يستغرق 5-10 دقائق)

## الخطوة 7: الوصول للتطبيق
بعد اكتمال النشر، ستظهر روابط الخدمات:

- **Frontend**: `https://calliq-frontend.onrender.com`
- **Backend API**: `https://calliq-api.onrender.com`
- **API Documentation**: `https://calliq-api.onrender.com/api/docs`

## الخطوة 8: تسجيل الدخول
1. افتح رابط Frontend
2. استخدم بيانات الدخول الافتراضية:
   - **Email**: `demo@company.com`
   - **Password**: `demo1234`

## 🔍 مراقبة النشر
- في Render Dashboard، يمكنك رؤية **Logs** لكل خدمة
- اضغط على أي خدمة لرؤية السجلات المباشرة
- يمكن معرفة حالة النشر من تبويب **"Events"**

## ⚠️ حل المشاكل الشائعة

### إذا فشل النشر:
1. اذهب إلى تبويب **"Logs"** في الخدمة الفاشلة
2. اقرأ رسالة الخطأ
3. غالباً يكون المشكلة في:
   - مفاتيح API غير صحيحة
   - أخطاء في الاعتماديات (dependencies)
   - مشاكل في قاعدة البيانات

### إذا لم يعمل Frontend:
1. تأكد من أن Backend يعمل
2. تحقق من رابط API في متغيرات البيئة
3. تأكد من إعدادات CORS في Backend

### إذا كانت قاعدة البيانات فارغة:
1. قد تحتاج لتهيئة قاعدة البيانات يدوياً
2. في Render، أضف متغير بيئة `INIT_DB=true`
3. أعد نشر الخدمة

## 💰 تأكيد التكلفة
هذا التكوين مصمم ليكون **مجاناً بالكامل**:
- Backend Web Service: Free tier
- Frontend Static Site: Free tier
- Database: SQLite (مجاني)

**التكلفة الشهرية المتوقعة**: $0

## 📞 الدعم
إذا واجهت مشاكل:
- اقرأ سجلات (Logs) الخدمات في Render
- راجع دليل Render: https://docs.render.com
- افتح Issue في GitHub: https://github.com/krymjwdh098-cmyk/CalliQ-AI/issues

## 🎉 تهانينا!
بعد إكمال هذه الخطوات، سيكون تطبيق CalliQ-AI الخاص بك يعمل على الإنترنت مجاناً!
