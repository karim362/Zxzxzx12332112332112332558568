import asyncio
from pyppeteer import launch
import random
import string
import json
import os
import logging
from pyppeteer.errors import TimeoutError, ElementHandleError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

REFERRAL_URL = os.environ.get('REFERRAL_URL', 'https://gamersunivers.com/default.aspx?u=1206990')
NAVIGATION_TIMEOUT = int(os.environ.get('NAVIGATION_TIMEOUT', 60000)) # 60 seconds default

def generate_email():
    """Generate a random email."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '@gmail.com'

def generate_password():
    """Generate a random password."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

def load_stats():
    """Load stats from JSON file."""
    stats_path = 'stats.json'
    if not os.path.exists(stats_path):
        return {'success': 0, 'failed': 0, 'last_email': '', 'last_error': '', 'captchas': {}}
    try:
        with open(stats_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        logging.error(f"Error loading stats file: {e}")
        return {'success': 0, 'failed': 0, 'last_email': '', 'last_error': '', 'captchas': {}}

def save_stats(stats):
    """Save stats to JSON file."""
    stats_path = 'stats.json'
    try:
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving stats file: {e}")

def log_stats(success, email='', reason='', keyword=''):
    """Update stats based on registration attempt result."""
    stats = load_stats()

    if success:
        stats['success'] += 1
        stats['last_email'] = email
        if 'captchas' not in stats or not isinstance(stats['captchas'], dict):
             stats['captchas'] = {}
        stats['captchas'][keyword] = stats['captchas'].get(keyword, 0) + 1
        stats['last_error'] = ''
        logging.info(f"[✔] Success: {email} (Captcha: {keyword})")
    else:
        stats['failed'] += 1
        stats['last_error'] = reason
        logging.error(f"[✘] Failed: {reason}")
        if keyword and 'captchas' in stats and isinstance(stats['captchas'], dict):
             stats['captchas'][keyword] = stats['captchas'].get(keyword, 0) + 1

    save_stats(stats)

async def register_with_referral():
    """Execute a single account registration step."""
    browser = None
    try:
        logging.info(f"Starting new registration attempt using referral link: {REFERRAL_URL}")
        browser = await launch(headless=True, args=['--no-sandbox', '--disable-gpu', '--no-zygote', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = await browser.newPage()

        await page.goto(REFERRAL_URL, {'timeout': NAVIGATION_TIMEOUT})
        logging.info("Navigated to referral page.")

        await page.waitForSelector('#registerButton', {'timeout': 10000})
        await page.click('#registerButton')
        logging.info("Clicked register button.")

        await page.waitForNavigation({"waitUntil": "networkidle2", 'timeout': NAVIGATION_TIMEOUT})
        logging.info("Navigated to registration page.")

        email = generate_email()
        password = generate_password()

        await page.waitForSelector('#ctl00_MainContentPlaceHolder_ctl00_Email', {'timeout': 10000})
        await page.type('#ctl00_MainContentPlaceHolder_ctl00_Email', email)
        await page.type('#ctl00_MainContentPlaceHolder_ctl00_Password', password)
        await page.type('#ctl00_MainContentPlaceHolder_ctl00_ConfirmPassword', password)
        logging.info("Filled email and password fields.")

        await page.click('#TermsCheckBox')
        await page.click('#PrivacyCheckBox')
        logging.info("Agreed to terms.")

        keyword = ''
        try:
            await page.waitForSelector('.visualCaptcha-explanation', {'timeout': 10000})
            explanation = await page.Jeval('.visualCaptcha-explanation', '(el) => el.textContent')
            keyword = explanation.split('Click or touch the ')[-1].strip().lower()
            logging.info(f"Required captcha keyword: {keyword}")

            await page.waitForSelector('.visualCaptcha-possibilities .img img', {'timeout': 10000})
            images = await page.querySelectorAll('.visualCaptcha-possibilities .img img')
            found = False
            for img in images:
                src = await page.evaluate('(el) => el.getAttribute("src")', img)
                if keyword in src.lower():
                    await img.click()
                    found = True
                    logging.info(f"Found and clicked matching captcha image ({keyword}).")
                    break

            if not found:
                random_img = random.choice(images)
                await random_img.click()
                logging.warning(f"Matching captcha image not found ({keyword}), clicked randomly.")
                keyword = f"random_{keyword}" if keyword else "random"

        except TimeoutError:
             logging.warning("Captcha element wait failed (Timeout).")
             log_stats(False, reason='Captcha element wait timeout', keyword=keyword if keyword else "unknown")

        except Exception as e:
             logging.error(f"Error during captcha processing: {e}")
             log_stats(False, reason=f'Captcha processing error: {e}', keyword=keyword if keyword else "unknown")


        await page.click('#ctl00_MainContentPlaceHolder_ctl00_CreateUserButton')
        logging.info("Clicked create user button.")

        await asyncio.sleep(5)

        content = await page.content()
        if "hesabınız oluşturuldu" in content or "teşekkür ederiz" in content or "تم إنشاء حسابك بنجاح" in content:
            with open("accounts.txt", "a") as f:
                f.write(f"{email}:{password}\n")
            log_stats(True, email=email, keyword=keyword)

        else:
            error_message = "Unknown failure after registration attempt"
            try:
                error_element = await page.try_select('span[style*="color:Red"]')
                if error_element:
                    error_message_text = await page.evaluate('(el) => el.textContent', error_element)
                    error_message = f"Registration failed: {error_message_text.strip()}"
                elif "البريد الإلكتروني مستخدم بالفعل" in content:
                    error_message = "Registration failed: Email already in use"
            except Exception:
                 pass

            log_stats(False, reason=error_message, keyword=keyword if keyword else "unknown")
            logging.error(f"[✘] Registration failed: {error_message}")


    except TimeoutError as e:
        log_stats(False, reason=f"Timeout error: {e}")
        logging.error(f"[!] Timeout error during registration: {e}")
    except ElementHandleError as e:
        log_stats(False, reason=f"Element handle error: {e}")
        logging.error(f"[!] Element handle error during registration: {e}")
    except Exception as e:
        log_stats(False, reason=f"General error during registration: {e}")
        logging.error(f"[!] General error during registration: {e}")

    finally:
        if browser:
            await browser.close()
            logging.info("Browser closed.")

async def main_loop():
    """Main loop to continuously run the bot."""
    logging.info("Starting bot main loop...")
    while True:
        await register_with_referral()
        await asyncio.sleep(30)
    logging.info("Bot main loop finished.")

# هذا السطر يجعل البوت يعمل تلقائياً عند تشغيل الملف مباشرةً
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main_loop())

