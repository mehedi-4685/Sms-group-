import asyncio
import aiohttp
import sys
import json
import hashlib
import re
import random
import phonenumbers  

# টার্মিনাল UTF-8 ফিক্স
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# ==================== আপনার তথ্য ====================
BOT_TOKEN = "8972113205:AAGSRFuSRVtg2W_Vplmh9Xk32vQy8AcQo9w"   
GROUP_CHAT_ID = "-1003770458235"

PANEL_API_KEY = "nxa_ec8d6f8f5697df75d20622332f35e86df2acb89c"

# লগইন তথ্য
USER_EMAIL = "mehedihasan706261@gmail.com"
USER_PASS = "mehedi706261"

# ডাইনামিক সেশন টোকেন
SESSION_TOKEN = "" 
DEVICE_ID = "40ec7e14451cf909833ee25741b83839"
BASE_URL = "http://63.141.255.227" 

POLL_INTERVAL = 8 # ৫-১০ সেকেন্ডের মাঝে

# ==================== প্যানেলের জন্য রেঞ্জ (ইচ্ছামত বাড়াতে পারেন) ====================
PANEL_RANGES = ["99298XXX"]   # আপনি এখানে আরও রেঞ্জ যোগ করতে পারেন, যেমন "12345XXX", "67890XXX"

seen_entries = {
    "console1": set(),
    "console2": set(),
    "console3": set(),
    "panel_api": set() 
}

login_lock = asyncio.Lock()

# ======================== অটোমেটিক সকল দেশের পতাকা ও কোড ========================
def get_country_info(phone: str) -> tuple:
    try:
        clean_num = str(phone).upper().replace('X', '0').replace('*', '0').replace('-', '').replace(' ', '')
        if not clean_num.startswith('+'): 
            clean_num = '+' + clean_num
            
        parsed_num = phonenumbers.parse(clean_num, None)
        region = phonenumbers.region_code_for_number(parsed_num) 
        
        if region:
            flag = "".join(chr(ord(c) + 127397) for c in region)
            return flag, region
    except Exception:
        pass
    
    return "🌍", "GLOBAL"

# ==================== স্মার্ট রিয়েল ও ফেক ওটিপি এক্সট্রাক্টর ====================
def extract_otp(text: str, backup_otp: str = None) -> str | None:
    if not text: return backup_otp
    
    ast_match = re.search(r'[\*★]{4,8}', text)
    if ast_match:
        return ''.join(random.choices('0123456789', k=len(ast_match.group(0))))
        
    g_match = re.search(r'G[- ]?(\d{6})', text, re.IGNORECASE)
    if g_match: return g_match.group(1)
        
    clean_text = re.sub(r'https?://\S+', '', str(text))
    clean_text = re.sub(r'\+?\d{10,}', '', clean_text) 
    
    matches = re.findall(r'(?<!\d)\d{4,8}(?!\d)', clean_text)
    for match in matches:
        if not re.match(r'^0+$', match): 
            return match
            
    return backup_otp

def format_range_number(phone_range: str) -> str:
    phone_range = str(phone_range).strip()
    return re.sub(r'[Xx\*★]', lambda _: str(random.randint(0, 9)), phone_range)

def generate_skypro_number(phone: str) -> str:
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) >= 6: return f"{digits[:3]}SKYPRO{digits[-3:]}"
    elif len(digits) > 3: return f"{digits[:3]}SKYPRO"
    return f"SKYPRO{digits}"

def detect_advanced_category(app_name, sms_text):
    combined = f"{str(app_name)} {str(sms_text)}".upper()
    if "WHATSAPP" in combined or "V-WHATSAPP" in combined: return "WHATSAPP", "WA"
    if "INSTAGRAM" in combined or " IG " in combined or "IG-" in combined: return "INSTAGRAM", "IG"
    if "FACEBOOK" in combined or " FB " in combined or "FB-" in combined: return "FACEBOOK", "FB"
    if "TELEGRAM" in combined: return "TELEGRAM", "TG"
    if "TIKTOK" in combined: return "TIKTOK", "TK"
    if "GOOGLE" in combined or " G-" in combined: return "GOOGLE", "GL"
    
    match = re.search(r'CODE FOR ([A-Z0-9]+)', combined)
    if match: return match.group(1).strip(), match.group(1).strip()[:6] 
        
    valid_app_name = str(app_name).strip().upper()
    invalid_names = ["", "******", "AUTHMSG", "FAILED CALLS", "AIRCOMM SA", "IRISTEL", "NONE", "NULL"]
    if valid_app_name and valid_app_name not in invalid_names: return valid_app_name, valid_app_name[:6]
    return "UNKNOWN", "UKN"

def format_telegram_message(otp_code: str, phone: str, category_short: str) -> str:
    flag, country_short = get_country_info(phone)
    skypro_number = generate_skypro_number(phone)
    inner_text = f"{flag} {country_short}➔{category_short}➔[ {skypro_number} ]"
    top_line = "┏━━━━━━━━━━━━━━━━━━━━━━━┓"
    mid_line = f"┃ {inner_text} ┃"
    bot_line = "┗━━━━━━━━━━━━━━━━━━━━━━━┛"
    return f"{top_line}\n{mid_line}\n{bot_line}\n\n🕋 **𝙿𝙾𝚆𝙴𝚁𝙴𝙳 𝙱𝚈 [𝐒𝐊𝐘](https://t.me/SKYSMSOWNER)** 🕋"

# ==================== টেলিগ্রাম সেন্ডার (Aiohttp) ====================
async def send_to_telegram(session, otp_code: str, phone: str, category_full: str, category_short: str, log_badge: str):
    text = format_telegram_message(otp_code, phone, category_short)
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": f" {otp_code}", "copy_text": {"text": otp_code}, "style": "success"}],
            [
                {"text": "‼️ 𝑷𝑨𝑵𝑬𝑳", "url": "https://t.me/SKYSMSPRO_BOT", "style": "danger"},
                {"text": "📞 𝑪𝑯𝑨𝑵𝑵𝑬𝑳", "url": "https://t.me/SKYOFFICIALCHANNEL1", "style": "primary"}
            ]
        ]
    }
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": GROUP_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(reply_markup),
        "disable_web_page_preview": True
    }
    
    for attempt in range(5):
        try:
            async with session.post(url, json=payload, timeout=15) as resp:
                if resp.status == 200:
                    print(f"[{log_badge}] ✅ ফরোয়ার্ড হয়েছে: {otp_code} | {category_full} | Num: {phone}")
                    return True
                elif resp.status == 429: 
                    resp_json = await resp.json()
                    retry_after = resp_json.get("parameters", {}).get("retry_after", 5)
                    await asyncio.sleep(retry_after + 1) 
                else:
                    await asyncio.sleep(2)
        except Exception:
            await asyncio.sleep(2)
    return False

# ==================== অটো লগইন সিস্টেম ====================
async def auto_login(session):
    global SESSION_TOKEN
    print("\n🔄 সেশন এক্সপায়ার হয়েছে! অটো-লগইন করে নতুন টোকেন আনা হচ্ছে...")
    
    payload = {"email": USER_EMAIL, "password": USER_PASS}
    
    possible_urls = [
        f"{BASE_URL}/api/v1/login", 
        f"{BASE_URL}/api/auth/login",
        f"{BASE_URL}/api/user/login",
        f"{BASE_URL}/login"
    ]

    for login_url in possible_urls:
        try:
            async with session.post(login_url, json=payload, timeout=8) as r:
                if r.status == 200:
                    if await extract_and_set_token(r, session, login_url): return True
        except Exception: pass
        try:
            async with session.post(login_url, data=payload, timeout=8) as r:
                if r.status == 200:
                    if await extract_and_set_token(r, session, login_url): return True
        except Exception: pass

    print("❌ অটো-লগইন ব্যর্থ! ওয়েবসাইটের লগইন লিংক পাল্টেছে হয়তো।")
    return False

async def extract_and_set_token(response, session, url):
    global SESSION_TOKEN
    try:
        data = await response.json()
        new_token = data.get("session_token") or data.get("token") or data.get("data", {}).get("token") or data.get("access_token") 
    except:
        new_token = None

    if not new_token:
        cookies = session.cookie_jar.filter_cookies(BASE_URL)
        if "session_token" in cookies: new_token = cookies["session_token"].value
        elif "token" in cookies: new_token = cookies["token"].value

    if new_token:
        SESSION_TOKEN = new_token
        print("✅ অটো-লগইন সফল! নতুন টোকেন সেট হয়ে গেছে।\n")
        return True
    return False

def get_headers(referer="/"):
    return {
        "Accept": "application/json", 
        "Cookie": f"device_id={DEVICE_ID}; session_token={SESSION_TOKEN}; token={SESSION_TOKEN}",
        "Referer": f"{BASE_URL}{referer}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Session-Token": SESSION_TOKEN,
        "Authorization": f"Bearer {SESSION_TOKEN}" 
    }

# ==================== API লগ প্রসেসিং (ফেক ওটিপির জন্য) ====================
def extract_valid_logs(obj):
    logs = []
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict) and ("number" in item or "number_raw" in item or "sms" in item or "message" in item):
                logs.append(item)
            else:
                logs.extend(extract_valid_logs(item))
    elif isinstance(obj, dict):
        if "data" in obj and isinstance(obj["data"], list):
            logs.extend(extract_valid_logs(obj["data"]))
        else:
            for val in obj.values(): logs.extend(extract_valid_logs(val))
    return logs

def make_entry_key(entry):
    entry_str = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(entry_str.encode('utf-8')).hexdigest()

async def process_engine(session, key, label, endpoint, referer="/"):
    global SESSION_TOKEN
    
    url = f"{BASE_URL}{endpoint}"
    if "?" not in url:
        url += "?limit=50"
        
    headers = get_headers(referer)
    
    entries = None
    try:
        async with session.get(url, headers=headers, timeout=20) as r:
            if r.status == 401 or r.status == 403: 
                entries = None 
            elif r.status == 200:
                data = await r.json()
                entries = extract_valid_logs(data) or []
            else:
                entries = []
    except Exception as e:
        entries = []
    
    if entries is None:
        async with login_lock:
            if not await auto_login(session): return 
        
        headers = get_headers(referer)
        try:
            async with session.get(url, headers=headers, timeout=20) as r:
                if r.status == 200:
                    data = await r.json()
                    entries = extract_valid_logs(data) or []
                else:
                    entries = []
        except:
            entries = []

    if not entries: return

    new_entries = []
    for e in entries:
        if not isinstance(e, dict): continue
        key_str = make_entry_key(e)
        if key_str not in seen_entries[key]:
            new_entries.append(e)
            seen_entries[key].add(key_str)

    if len(seen_entries[key]) > 5000:
        to_remove = list(seen_entries[key])[:2000]
        for it in to_remove: seen_entries[key].discard(it)

    if new_entries:
        new_entries.sort(key=lambda x: x.get("delivered_at") or x.get("time") or x.get("created_at") or "")
        for e in new_entries:
            raw_number = e.get("number") or e.get("number_raw") or e.get("phone") or ""
            raw_sms = e.get("sms") or e.get("text") or e.get("message") or ""
            app_name = e.get("app_name") or e.get("service") or e.get("service_name") or ""
            backup_otp = e.get("otp") or e.get("code")

            if not raw_number: continue
            
            real_looking_number = format_range_number(raw_number).replace("+", "")
            otp = extract_otp(raw_sms, backup_otp)

            if otp and real_looking_number:
                cat_full, cat_short = detect_advanced_category(app_name, raw_sms)
                if cat_full != "UNKNOWN":
                    if random.random() < 0.30: 
                        await send_to_telegram(session, otp, real_looking_number, cat_full, cat_short, label)
                        await asyncio.sleep(5.1)

async def run_console_loop(session, key, label, endpoint, referer):
    while True:
        await process_engine(session, key, label, endpoint, referer)
        await asyncio.sleep(POLL_INTERVAL)

# ==================== নতুন প্যানেল API লুপ (আসল OTP) ====================
async def run_panel_api_loop(session):
    """
    প্যানেল থেকে আসল OTP আনার জন্য:
    1. PANEL_RANGES থেকে একটি রেঞ্জ নিবে
    2. POST /api/v1/numbers/get করে একটি নম্বর রিকোয়েস্ট করবে
    3. নম্বরের আইডি পেয়ে প্রতি ২ সেকেন্ডে OTP চেক করবে (সর্বোচ্চ ১০ মিনিট)
    4. OTP পেলে টেলিগ্রামে ফরোয়ার্ড করবে
    5. তারপর আবার নতুন নম্বর রিকোয়েস্ট করবে
    """
    # প্যানেল API এর জন্য হেডার
    api_headers = {
        "X-API-Key": PANEL_API_KEY,
        "Content-Type": "application/json"
    }

    while True:
        try:
            # এলোমেলোভাবে একটি রেঞ্জ সিলেক্ট করি (একাধিক রেঞ্জ থাকলে)
            selected_range = random.choice(PANEL_RANGES)
            print(f"[Panel API] রিকোয়েস্ট করছি রেঞ্জ: {selected_range}")

            # 1. নম্বর রিকোয়েস্ট
            get_number_url = f"{BASE_URL}/api/v1/numbers/get"
            payload = {
                "range": selected_range,
                "format": "national"   # অথবা "international" দরকার হলে পরিবর্তন করুন
            }
            try:
                async with session.post(get_number_url, json=payload, headers=api_headers, timeout=15) as resp:
                    if resp.status != 200:
                        print(f"[Panel API] নম্বর রিকোয়েস্ট ব্যর্থ: {resp.status}")
                        await asyncio.sleep(5)
                        continue
                    data = await resp.json()
                    # রেসপন্সে number_id এবং number থাকবে (উদাহরণ অনুযায়ী)
                    num_id = data.get("number_id")
                    raw_number = data.get("number")
                    if not num_id or not raw_number:
                        print(f"[Panel API] রিকোয়েস্ট সফল হলেও number_id/নাম্বার পাওয়া যায়নি: {data}")
                        await asyncio.sleep(5)
                        continue
                    print(f"[Panel API] নম্বর পাওয়া গেছে: {raw_number} (ID: {num_id})")
            except Exception as e:
                print(f"[Panel API] নম্বর রিকোয়েস্ট এরর: {e}")
                await asyncio.sleep(5)
                continue

            # 2. OTP এর জন্য পোলিং (সর্বোচ্চ ১০ মিনিট = ৩০০ বার * ২ সেকেন্ড)
            otp_found = None
            for attempt in range(300):
                await asyncio.sleep(2)   # প্রতি ২ সেকেন্ডে চেক
                sms_url = f"{BASE_URL}/api/v1/numbers/{num_id}/sms"
                try:
                    async with session.get(sms_url, headers=api_headers, timeout=10) as sms_resp:
                        if sms_resp.status == 200:
                            sms_data = await sms_resp.json()
                            real_otp = sms_data.get("otp")
                            raw_sms = sms_data.get("sms", "")
                            app_name = sms_data.get("service", "UNKNOWN")
                            
                            if real_otp:
                                # ডুপ্লিকেট চেক
                                key_str = hashlib.md5(f"{num_id}_{real_otp}".encode()).hexdigest()
                                if key_str not in seen_entries["panel_api"]:
                                    seen_entries["panel_api"].add(key_str)
                                    otp_found = real_otp
                                    # ক্যাটাগরি ডিটেক্ট
                                    cat_full, cat_short = detect_advanced_category(app_name, raw_sms)
                                    # ফরম্যাট করা নাম্বার (X এর জায়গায় র‍্যান্ডম ডিজিট)
                                    real_looking_number = format_range_number(raw_number).replace("+", "")
                                    # টেলিগ্রামে পাঠান (আসল OTP ১০০% সময় যাবে)
                                    await send_to_telegram(session, real_otp, real_looking_number, cat_full, cat_short, "Panel API")
                                    await asyncio.sleep(5.1)
                                    break   # OTP পেয়ে গেছি, এই নম্বরের কাজ শেষ
                        else:
                            # SMS এন্ডপয়েন্ট কাজ না করলে কিছু বলার দরকার নেই
                            pass
                except Exception as e:
                    # নীরবে ব্যর্থতা হ্যান্ডেল
                    pass

            if not otp_found:
                print(f"[Panel API] নম্বর {raw_number} (ID:{num_id}) এর জন্য ১০ মিনিটে কোনো OTP আসেনি। পরবর্তী নম্বর নিচ্ছি...")
                # এখানে নম্বর রিলিজ করার দরকার নেই, কারণ টাইমআউট হলে API নিজেই হ্যান্ডেল করবে
            # পরবর্তী নম্বর রিকোয়েস্টের জন্য লুপ কন্টিনিউ করবে

        except Exception as e:
            print(f"[Panel API] মেইন লুপে এরর: {e}")
            await asyncio.sleep(5)

# ==================== মেইন ফাংশন ====================
async def main():
    if BOT_TOKEN == "আপনার_বট_টোকেন_এখানে_দিন":
        print("❌ আপনি BOT_TOKEN বসাতে ভুলে গেছেন!")
        return
        
    if PANEL_API_KEY == "YOUR_API_KEY":
        print("⚠️ আপনি PANEL_API_KEY বসাননি! আসল ওটিপি আনতে সমস্যা হতে পারে।")

    print("🤖 অটো-লগইন + SKYPRO মাস্কিং + রিয়েল ওটিপি (100%) + ফেক ওটিপি কন্ট্রোল (30%) সিস্টেম রিস্টার্ট হচ্ছে...\n")

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        login_success = await auto_login(session)
        if not login_success:
            print("❌ প্রথম অটো-লগইন ব্যর্থ হয়েছে। লিংক বা পাসওয়ার্ড চেক করুন।")
        else:
            print("✅ লগইন সফল! কনসোল এবং প্যানেল API থেকে ডাটা আনা শুরু হয়েছে...\n")

        # সবগুলো লুপ একসাথে চলবে
        await asyncio.gather(
            run_console_loop(session, "console1", "Console 1", "/api/user/console-log", "/app/console"),
            run_console_loop(session, "console2", "Console 2", "/api/user/p2/console", "/app/console2"),
            run_console_loop(session, "console3", "Console 3", "/api/user/p3/console", "/app/console3"),
            run_panel_api_loop(session)  # নতুন প্যানেল লুপ (আসল OTP)
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 স্ক্রিপ্ট বন্ধ করা হয়েছে।")
