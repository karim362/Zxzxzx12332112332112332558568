import asyncio
from pyppeteer import launch
import random
import string
import json
import os
import logging # استيراد مكتبة التسجيل
from pyppeteer.errors import TimeoutError, ElementHandleError # استيراد أخطاء محددة

# إعداد التسجيل (Logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# جلب رابط الإحالة من متغيرات البيئة أو استخدام قيمة افتراضية
REFERRAL_URL = os.environ.get('REFERRAL_URL', 'https://gamersunivers.com/default.aspx?u=1206990')
# مهلة انتظار التنقل بالمللي ثانية (يمكن تغييرها عبر متغير بيئة أيضاً إذا أردت)
NAVIGATION_TIMEOUT = int(os.environ.get('NAVIGATION_TIMEOUT', 60000)) # 60 ثانية افتراضياً

def generate_email():
    """توليد بريد إلكتروني عشوائي."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '@gmail.com'

def generate_password():
    """توليد كلمة مرور عشوائية."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

def load_stats():
    """تحميل الإحصائيات من ملف JSON."""
    stats_path = 'stats.json'
    if not os.path.exists(stats_path):
        return {'success': 0, 'failed': 0, 'last_email': '', 'last_error': '', 'captchas': {}}
    try:
        with open(stats_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        logging.error(f"خطأ عند تحميل ملف الإحصائيات: {e}")
        return {'success': 0, 'failed': 0, 'last_email': '', 'last_error': '', 'captchas': {}}

def save_stats(stats):
    """حفظ الإحصائيات إلى ملف JSON."""
    stats_path = 'stats.json'
    try:
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=4) # استخدم indent لتحسين تنسيق الملف
    except Exception as e:
        logging.error(f"خطأ عند حفظ ملف الإحصائيات: {e}")

def log_stats(success, email='', reason='', keyword=''):
    """تحديث الإحصائيات بناءً على نتيجة محاولة التسجيل."""
    stats = load_stats()

    if success:
        stats['success'] += 1
        stats['last_email'] = email
        # تأكد أن 'captchas' هو قاموس قبل الوصول إليه
        if 'captchas' not in stats or not isinstance(stats['captchas'], dict):
             stats['captchas'] = {}
        stats['captchas'][keyword] = stats['captchas'].get(keyword, 0) + 1
        stats['last_error'] = '' # مسح آخر خطأ عند النجاح
        logging.info(f"[✔] نجاح: {email} (كابتشا: {keyword})")
    else:
        stats['failed'] += 1
        stats['last_error'] = reason
        logging.error(f"[✘] فشل: {reason}")
        # إذا كان الفشل متعلق بالكابتشا ولكن لم يتم التقاط الكلمة المفتاحية
        if keyword and 'captchas' in stats and isinstance(stats['captchas'], dict):
             stats['captchas'][keyword] = stats['captchas'].get(keyword, 0) + 1 # لا يزال يحتسب محاولة الكابتشا

    save_stats(stats)

async def register_with_referral():
    """تنفيذ خطوة تسجيل حساب واحد."""
    browser = None # تهيئة المتصفح بـ None
    try:
        logging.info(f"بدء محاولة تسجيل جديدة باستخدام رابط الإحالة: {REFERRAL_URL}")
        browser = await launch(headless=True, args=['--no-sandbox', '--disable-gpu', '--no-zygote', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = await browser.newPage()

        await page.goto(REFERRAL_URL, {'timeout': NAVIGATION_TIMEOUT}) # استخدام المهلة المحددة

        # انتظر زر التسجيل وحاول النقر عليه
        await page.waitForSelector('#registerButton', {'timeout': 10000}) # مهلة خاصة للزر
        await page.click('#registerButton')
        logging.info("تم النقر على زر التسجيل.")

        # انتظر التنقل إلى صفحة التسجيل
        await page.waitForNavigation({"waitUntil": "networkidle2", 'timeout': NAVIGATION_TIMEOUT}) # استخدام المهلة المحددة
        logging.info("تم الانتقال إلى صفحة التسجيل.")

        email = generate_email()
        password = generate_password()

        # انتظار حقول النموذج وملئها
        await page.waitForSelector('#ctl00_MainContentPlaceHolder_ctl00_Email', {'timeout': 10000})
        await page.type('#ctl00_MainContentPlaceHolder_ctl00_Email', email)
        await page.type('#ctl00_MainContentPlaceHolder_ctl00_Password', password)
        await page.type('#ctl00_MainContentPlaceHolder_ctl00_ConfirmPassword', password)
        logging.info("تم ملء حقول البريد وكلمة المرور.")

        # النقر على مربعات الموافقة
        await page.click('#TermsCheckBox')
        await page.click('#PrivacyCheckBox')
        logging.info("تم الموافقة على الشروط.")

        # محاولة حل الكابتشا
        keyword = '' # تهيئة الكلمة المفتاحية
        try:
            await page.waitForSelector('.visualCaptcha-explanation', {'timeout': 10000})
            explanation = await page.Jeval('.visualCaptcha-explanation', '(el) => el.textContent')
            keyword = explanation.split('Click or touch the ')[-1].strip().lower()
            logging.info(f"كلمة الكابتشا المطلوبة: {keyword}")

            await page.waitForSelector('.visualCaptcha-possibilities .img img', {'timeout': 10000})
            images = await page.querySelectorAll('.visualCaptcha-possibilities .img img')
            found = False
            for img in images:
                src = await page.evaluate('(el) => el.getAttribute("src")', img)
                if keyword in src.lower():
                    await img.click()
                    found = True
                    logging.info(f"تم العثور على صورة الكابتشا المناسبة ({keyword}) والنقر عليها.")
                    break

            if not found:
                # اختيار عشوائي إذا لم يتم العثور على الكلمة (حسب طلبك)
                random_img = random.choice(images)
                await random_img.click()
                logging.warning(f"لم يتم العثور على صورة الكابتشا المناسبة ({keyword})، تم النقر عشوائياً.")
                # قد ترغب في تغيير الكلمة المفتاحية لتعكس النقر العشوائي في الإحصائيات
                keyword = f"عشوائي_{keyword}" if keyword else "عشوائي"


        except TimeoutError:
             logging.warning("فشل انتظار عناصر الكابتشا (Timeout).")
             log_stats(False, reason='فشل انتظار عناصر الكابتشا', keyword=keyword if keyword else "غير محدد")
             # قد ترغب في إعادة المحاولة أو تخطي هذه المرة إذا فشلت الكابتشا

        except Exception as e:
             logging.error(f"خطأ أثناء معالجة الكابتشا: {e}")
             log_stats(False, reason=f'خطأ في الكابتشا: {e}', keyword=keyword if keyword else "غير محدد")
             # قد ترغب في إعادة المحاولة أو تخطي هذه المرة إذا فشلت الكابتشا


        # النقر على زر إنشاء المستخدم
        await page.click('#ctl00_MainContentPlaceHolder_ctl00_CreateUserButton')
        logging.info("تم النقر على زر إنشاء المستخدم.")

        # قد تحتاج إلى انتظار قصير هنا أو انتظار علامة نجاح
        await asyncio.sleep(5) # انتظار قصير للسماح بالمعالجة

        # التحقق من نجاح التسجيل
        content = await page.content()
        # استخدام كلمات مفتاحية أكثر دقة إن وجدت، وهذه مجرد أمثلة
        if "hesabınız oluşturuldu" in content or "teşekkür ederiz" in content or "تم إنشاء حسابك بنجاح" in content:
            with open("accounts.txt", "a") as f:
                f.write(f"{email}:{password}\n")
            log_stats(True, email=email, keyword=keyword)

        else:
            # محاولة جلب رسالة خطأ إذا كانت موجودة على الصفحة
            error_message = "فشل غير محدد بعد محاولة التسجيل"
            try:
                # ابحث عن عنصر يحتوي على رسالة خطأ (تحتاج إلى فحص هيكل الصفحة)
                error_element = await page.try_select('span[style*="color:Red"]') # مثال لمحدد CSS
                if error_element:
                    error_message_text = await page.evaluate('(el) => el.textContent', error_element)
                    error_message = f"فشل التسجيل: {error_message_text.strip()}"
                elif "البريد الإلكتروني مستخدم بالفعل" in content: # مثال لخطأ محدد
                    error_message = "فشل التسجيل: البريد الإلكتروني مستخدم بالفعل"
                # أضف المزيد من الشروط للأخطاء الشائعة الأخرى التي قد تجدها في محتوى الصفحة

            except Exception:
                 pass # تجاهل أخطاء محاولة العثور على رسالة الخطأ

            log_stats(False, reason=error_message, keyword=keyword if keyword else "غير محدد")
            logging.error(f"[✘] فشل التسجيل: {error_message}")


    except TimeoutError as e:
        log_stats(False, reason=f"خطأ في المهلة: {e}")
        logging.error(f"[!] خطأ في المهلة أثناء التسجيل: {e}")
    except ElementHandleError as e:
        log_stats(False, reason=f"خطأ في التعامل مع العنصر: {e}")
        logging.error(f"[!] خطأ في التعامل مع العنصر أثناء التسجيل: {e}")
    except Exception as e:
        log_stats(False, reason=f"خطأ عام أثناء التسجيل: {e}")
        logging.error(f"[!] خطأ عام أثناء التسجيل: {e}")

    finally:
        if browser:
            await browser.close()
            logging.info("تم إغلاق المتصفح.")

async def main_loop():
    """الحلقة الرئيسية لتشغيل البوت باستمرار."""
    logging.info("بدء الحلقة الرئيسية للبوت...")
    while True:
        await register_with_referral()
        await asyncio.sleep(30) # انتظر 30 ثانية بين المحاولات
    logging.info("انتهاء الحلقة الرئيسية للبوت.")

# ملاحظة: تم إزالة السطر الذي يشغل main_loop تلقائياً هنا.
# سيتم تشغيل main_loop الآن بواسطة لوحة التحكم عند الضغط على الزر.
