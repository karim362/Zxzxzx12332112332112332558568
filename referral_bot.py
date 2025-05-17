import asyncio
from pyppeteer import launch
import random
import string
import json
from datetime import datetime

def generate_email():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '@gmail.com'

def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

def log_stats(success, email='', reason='', keyword=''):
    stats_path = 'stats.json'
    try:
        with open(stats_path, 'r') as f:
            stats = json.load(f)
    except:
        stats = {'success': 0, 'failed': 0, 'last_email': '', 'last_error': '', 'captchas': {}}

    if success:
        stats['success'] += 1
        stats['last_email'] = email
        stats['captchas'][keyword] = stats['captchas'].get(keyword, 0) + 1
    else:
        stats['failed'] += 1
        stats['last_error'] = reason

    with open(stats_path, 'w') as f:
        json.dump(stats, f)

async def register_with_referral():
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()

    await page.goto('https://gamersunivers.com/default.aspx?u=1206990')

    try:
        await page.waitForSelector('#registerButton', {'timeout': 5000})
        await page.click('#registerButton')
    except Exception as e:
        log_stats(False, reason='زر التسجيل غير موجود')
        await browser.close()
        return

    await page.waitForNavigation({"waitUntil": "networkidle2"})

    email = generate_email()
    password = generate_password()

    try:
        await page.waitForSelector('#ctl00_MainContentPlaceHolder_ctl00_Email')
        await page.type('#ctl00_MainContentPlaceHolder_ctl00_Email', email)
        await page.type('#ctl00_MainContentPlaceHolder_ctl00_Password', password)
        await page.type('#ctl00_MainContentPlaceHolder_ctl00_ConfirmPassword', password)

        await page.click('#TermsCheckBox')
        await page.click('#PrivacyCheckBox')

        await page.waitForSelector('.visualCaptcha-explanation')
        explanation = await page.Jeval('.visualCaptcha-explanation', '(el) => el.textContent')
        keyword = explanation.split('Click or touch the ')[-1].strip().lower()

        await page.waitForSelector('.visualCaptcha-possibilities .img img')
        images = await page.querySelectorAll('.visualCaptcha-possibilities .img img')
        found = False
        for img in images:
            src = await page.evaluate('(el) => el.getAttribute("src")', img)
            if keyword in src.lower():
                await img.click()
                found = True
                break

        if not found:
            await random.choice(images).click()

        await page.click('#ctl00_MainContentPlaceHolder_ctl00_CreateUserButton')
        await asyncio.sleep(5)

        content = await page.content()
        if "hesabınız oluşturuldu" in content or "teşekkür ederiz" in content:
            with open("accounts.txt", "a") as f:
                f.write(f"{email}:{password}\n")
            log_stats(True, email=email, keyword=keyword)
            print(f"[✔] نجاح: {email}")
        else:
            log_stats(False, reason='فشل بعد محاولة التسجيل', keyword=keyword)
            print("[✘] فشل التسجيل")

    except Exception as e:
        log_stats(False, reason=str(e))
        print("[!] خطأ أثناء التسجيل:", e)

    await browser.close()

async def main_loop():
    while True:
        await register_with_referral()
        await asyncio.sleep(30)

asyncio.get_event_loop().run_until_complete(main_loop())
