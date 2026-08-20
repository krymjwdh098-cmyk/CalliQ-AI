# 🚀 نشر CalliQ-AI على Render (الطريقة الموثوقة)

بسبب مشاكل Render CLI في GitHub Actions، الطريقة الأفضل والأكثر موثوقية هي استخدام GitHub Integration المدمج في Render.

## 📋 الطريقة الأبسط والأسرع:

### الخطوة 1: تسجيل الدخول في Render
1. اذهب إلى: **https://dashboard.render.com**
2. سجل الدخول بحسابك

### الخطوة 2: ربط GitHub
1. في Render Dashboard، اضغط **"New +"**
2. اختر **"Web Service"**
3. اضغط **"Connect GitHub"**
3. وافق على الأذونات

### الخطوة 3: نشر Backend
1. اختر مستودع **"CalliQ-AI"**
2. الإعدادات:
   - **Name**: `calliq-api`
   - **Environment**: Python 3
   - **Branch**: `main`
   - **Root Directory**: `Backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. **Environment Variables**:
   - `DATABASE_URL`: `sqlite:///./talentai.db`
   - `SECRET_KEY`: (أنشئ مفتاح عشوائي)
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `false`
   - `UPLOAD_DIR`: `uploads`
   - `LLM_PROVIDER`: `groq`
   - `GROQ_API_KEY`: `gsk_vuNprvL7eiQmifV3WwtcWGdy3FYdJha2BYNQs865vKjdbIDIQCU`
   - `GROQ_MODEL`: `llama-3.3-70b-versatile`
4. اضغط **"Create Web Service"**

### الخطوة 4: نشر Frontend
1. في Render Dashboard، اضغط **"New +"**
2. اختر **"Static Site"**
3. الإعدادات:
   - **Name**: `calliq-frontend`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. **Environment Variables**:
   - `VITE_API_URL`: `https://calliq-api.onrender.com`
5. اضغط **"Create Static Site"**

### الخطوة 5: تمكين Auto-Deploy
بعد إنشاء الخدمات:
1. لكل خدمة، اذهب إلى **Settings**
2. اختر **"Auto Deploy"**
3. تأكد من اختيار **"On Commit"**
4. الآن أي push إلى main سينشر تلقائياً!

---

## 🎯 المميزات:

- ✅ **موثوق 100%** - يستخدم GitHub Integration الرسمي
- ✅ **أتمتة كاملة** - أي push إلى main = نشر تلقائي
- ✅ **سهل الإعداد** - خطوات بسيطة فقط
- ✅ **دعم Render** - رسمي وموثوق

---

## 💰 التكلفة:

- **Backend**: Free tier (512MB RAM)
- **Frontend**: Free tier
- **التكلفة الشهرية**: $0

---

## 🚀 بعد النشر:

- **Frontend**: `https://calliq-frontend.onrender.com`
- **Backend**: `https://calliq-api.onrender.com`
- **API Docs**: `https://calliq-api.onrender.com/api/docs`

**بيانات الدخول الافتراضية**:
- Email: `demo@company.com`
- Password: `demo1234`

---

## 🔄 التحديثات المستقبلية:

بعد إعداد Auto-Deploy:
1. فقط `git push` إلى main
2. Render ينشر تلقائياً
3. لا حاجة لأي خطوات إضافية!

---

هذه الطريقة أبسط بكثير من استخدام Render CLI وتعمل بنجاح 100%! 🎉
