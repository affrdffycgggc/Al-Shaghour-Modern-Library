import os
import sys
import json
import asyncio
import uuid
import logging
import traceback
import threading
import html
import time
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# ================= إعدادات التسجيل (Logging) =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# ================= الإعدادات العامة =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8395651089:AAEfbnpVCy0AJL2pI1X57Zlv5cP7CySOo5s")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8410208108"))
DB_FILE = os.environ.get("DB_FILE", "data.json")
UPLOADS_DIR = os.environ.get("UPLOADS_DIR", "uploads")

_data_lock = threading.RLock()

try:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
except Exception as e:
    logging.warning(f"تعذر إنشاء مجلد الرفعات: {e}")

DEFAULT_LOGO = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgdmlld0JveD0iMCAwIDIwMCAyMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiMwRjBGMEYiLz48Y2lyY2xlIGN4PSIxMDAiIGN5PSIxMDAiIHI9IjkwIiBzdHJva2U9IiNDOUE5NjEiIHN0cm9rZS13aWR0aD0iMyIvPjxwYXRoIGQ9Ik02MCA2MEwxMDAgODBMMTQwIDYwVjE0MEwxMDAgMTIwTDYwIDE0MFoiIGZpbGw9IiNDOUE5NjEiLz48cmVjdCB4PSI5NiIgeT0iNjAiIHdpZHRoPSI4IiBoZWlnaHQ9IjgwIiBmaWxsPSIjMEYwRjBGIi8+PC9zdmc+"

# ==========================================
# 1. وحدة قاعدة البيانات (المشتركة)
# ==========================================
class Database:
    def __init__(self):
        self._memory_db = None

    def load(self):
        with _data_lock:
            if self._memory_db is not None:
                return self._memory_db
            
            if os.path.exists(DB_FILE):
                try:
                    with open(DB_FILE, 'r', encoding='utf-8') as f:
                        self._memory_db = json.load(f)
                        # التأكد من وجود جميع الحقول الجديدة
                        defaults = self._default_data()
                        for key, val in defaults.items():
                            if key not in self._memory_db:
                                self._memory_db[key] = val
                        return self._memory_db
                except Exception:
                    logging.warning("ملف البيانات تالف. سيتم إنشاء بيانات افتراضية.")
            
            self._memory_db = self._default_data()
            self._write_to_disk(self._memory_db)
            return self._memory_db

    def save(self, data):
        with _data_lock:
            self._memory_db = data
            self._write_to_disk(data)

    def _write_to_disk(self, data):
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            logging.warning("تعذر الكتابة على القرص. سيتم استخدام الذاكرة المؤقتة.")

    def _default_data(self):
        return {
            "maintenance_mode": False,
            "maintenance_message": "نحن حالياً نقوم بأعمال تطوير وصيانة لتحسين تجربتكم. سنعود قريباً بأفضل مما كنا!",
            "announcements": "مرحباً بكم في مكتبة الشاغور الحديثة | توصيل سريع لجميع المحافظات | عروض حصرية على القرطاسية",
            "about_text": "مكتبة الشاغور الحديثة، وجهتك الأولى للقرطاسية والمستلزمات الفنية والمكتبية في سوريا. نقدم منتجات بجودة عالية وأسعار منافسة.",
            "slider_text": "وجهتك الأولى للقرطاسية والمستلزمات الفنية في سوريا",
            "logo_url": DEFAULT_LOGO,
            "icon_url": DEFAULT_LOGO,
            "library_address": "سوريا - دمشق - الشاغور",
            "working_hours": "السبت - الخميس: 9 صباحاً - 9 مساءً",
            "phone_number": "+963 11 123 4567",
            "slider_images": [
                "https://images.unsplash.com/photo-1507842217343-583bb7270b0f?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80",
                "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80"
            ],
            "video_url": "https://cdn.coverr.co/videos/cover2-coverr-co-writing-on-a-notebook-1080p.mp4",
            "categories": [
                {"id": "cat1", "name": "قرطاسية مدرسية", "img": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80", "products": [
                    {"id": "p1", "name": "دفتر سلك", "price": "15,000", "img": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80"},
                    {"id": "p2", "name": "قلم حبر جاف", "price": "2,500", "img": "https://images.unsplash.com/photo-1583485088034-697b5bc36b92?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80"}
                ]},
                {"id": "cat2", "name": "أدوات مكتبية", "img": "https://images.unsplash.com/photo-1497032628192-86f99bcd76bc?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80", "products": []},
                {"id": "cat3", "name": "أدوات فنية", "img": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80", "products": []},
                {"id": "cat4", "name": "كتب ودفاتر", "img": "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80", "products": []},
                {"id": "cat5", "name": "اكسسوارات هواتف", "img": "https://images.unsplash.com/photo-1572569511254-d8f925fe2cbb?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80", "products": []}
            ],
            "offers": [
                {"id": "off1", "title": "خصم 20% على الأقلام", "price": "10,000 ل.س", "desc": "عرض لفترة محدودة على جميع أنواع الأقلام", "img": "https://images.unsplash.com/photo-1583485088034-697b5bc36b92?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80"}
            ],
            "contacts": {"whatsapp": "963935123456", "instagram": "shaghour_library", "gmail": "info@shaghour.sy"},
            "notifications": []
        }

db = Database()

# ==========================================
# 2. وحدة الموقع (Web Server & HTML Templates)
# ==========================================
class WebServer:
    def __init__(self, db_instance):
        self.db = db_instance
        self.html_template = self._get_main_template()
        self.maintenance_template = self._get_maintenance_template()

    def _get_maintenance_template(self):
        return """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
    <title>صيانة | مكتبة الشاغور الحديثة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@200;400;600;800&family=Amiri:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body{margin:0;background:#0F0F0F;color:#C9A961;font-family:'Cairo',sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;text-align:center;overflow:hidden}
        .container{z-index:2;padding:20px}
        .gear{width:100px;height:100px;margin:0 auto 30px;border:3px solid #C9A961;border-radius:50%;border-top-color:transparent;animation:spin 2s linear infinite;display:flex;justify-content:center;align-items:center;box-shadow:0 0 30px rgba(201,169,97,0.3)}
        .gear svg{width:50px;height:50px;fill:#C9A961;animation:spin-rev 4s linear infinite}
        @keyframes spin{100%{transform:rotate(360deg)}}
        @keyframes spin-rev{100%{transform:rotate(-360deg)}}
        h1{font-family:'Amiri',serif;font-size:48px;margin-bottom:20px;text-shadow:0 0 20px rgba(201,169,97,0.5)}
        p{font-size:18px;max-width:600px;margin:0 auto;line-height:1.6;color:#8B8B8B}
        .bg-particles{position:absolute;top:0;left:0;width:100%;height:100%;z-index:1;pointer-events:none}
    </style>
</head>
<body>
    <canvas class="bg-particles" id="bg"></canvas>
    <div class="container">
        <div class="gear"><svg viewBox="0 0 24 24"><path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.91,5.35C9.32,5.59,8.79,5.92,8.29,6.29L5.9,5.33c-0.22-0.08-0.47,0-0.59,0.22L3.4,8.87 c-0.12,0.21-0.08,0.47,0.12,0.61l2.03,1.58C5.5,11.36,5.48,11.68,5.48,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.04,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/></svg></div>
        <h1>الموقع قيد الصيانة</h1>
        <p>%MAINTENANCE_MSG%</p>
    </div>
    <script>
        const c=document.getElementById('bg');const ctx=c.getContext('2d');c.width=innerWidth;c.height=innerHeight;let p=[];
        class P{constructor(){this.x=Math.random()*c.width;this.y=Math.random()*c.height;this.s=Math.random()*2+1;this.sx=Math.random()*0.5-0.25;this.sy=Math.random()*0.5-0.25;}
        u(){this.x+=this.sx;this.y+=this.sy;if(this.x<0||this.x>c.width)this.sx*=-1;if(this.y<0||this.y>c.height)this.sy*=-1;}
        d(){ctx.fillStyle='rgba(201,169,97,0.5)';ctx.beginPath();ctx.arc(this.x,this.y,this.s,0,Math.PI*2);ctx.fill();}}
        for(let i=0;i<30;i++)p.push(new P());
        function anim(){ctx.clearRect(0,0,c.width,c.height);p.forEach(e=>{e.u();e.d();});requestAnimationFrame(anim);}anim();
    </script>
</body>
</html>
"""

    def _get_main_template(self):
        return """
<!DOCTYPE html>
<html lang="ar" dir="rtl" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
    <meta name="description" content="مكتبة الشاغور الحديثة - وجهتك الأولى للقرطاسية والمستلزمات الفنية والمكتبية في سوريا">
    <meta property="og:title" content="مكتبة الشاغور الحديثة">
    <meta property="og:description" content="وجهتك الأولى للقرطاسية والمستلزمات الفنية في سوريا">
    <meta property="og:image" content="%LOGO_URL%">
    <meta property="og:type" content="website">
    <title>مكتبة الشاغور الحديثة | Al-Shaghour Modern Library</title>
    <link rel="icon" href="%ICON_URL%" type="image/x-icon">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@200;400;600;700;800;900&family=Amiri:wght@400;700&family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
    <style>
        :root {
            --primary-gold: #C9A961;
            --primary-gold-light: #E5C77C;
            --primary-gold-dark: #9B7D3F;
            --dark-bg: #0A0A0A;
            --dark-bg-2: #141414;
            --dark-bg-3: #1E1E1E;
            --text-light: #F5F1E8;
            --text-muted: #8B8B8B;
            --border-color: rgba(201, 169, 97, 0.2);
            --shadow-gold: 0 10px 40px rgba(201, 169, 97, 0.15);
            --glass-bg: rgba(20, 20, 20, 0.75);
            --transition-smooth: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            --max-width: 1400px;
            --notif-success: #2ecc71;
            --notif-info: #3498db;
            --notif-warning: #f39c12;
            --notif-error: #e74c3c;
        }
        [data-theme="light"] {
            --dark-bg: #F5F5F5;
            --dark-bg-2: #FFFFFF;
            --dark-bg-3: #EAEAEA;
            --text-light: #1A1A1A;
            --text-muted: #666666;
            --border-color: rgba(0, 0, 0, 0.12);
            --glass-bg: rgba(255, 255, 255, 0.85);
            --shadow-gold: 0 10px 40px rgba(201, 169, 97, 0.2);
        }

        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; max-width: 100%; }
        html { scroll-behavior: smooth; overflow-x: hidden; }
        body { background: var(--dark-bg); color: var(--text-light); font-family: 'Cairo', sans-serif; transition: background 0.5s, color 0.5s; overflow-x: hidden; max-width: 100vw; position: relative; }

        /* ===== Scrollbar مخصص ===== */
        ::-webkit-scrollbar { width: 10px; }
        ::-webkit-scrollbar-track { background: var(--dark-bg-2); }
        ::-webkit-scrollbar-thumb { background: var(--primary-gold-dark); border-radius: 5px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--primary-gold); }

        /* ===== الخلفية المتحركة ===== */
        #particles-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none; }
        .gradient-orb { position: fixed; border-radius: 50%; filter: blur(100px); opacity: 0.15; z-index: -1; pointer-events: none; }
        .orb-1 { width: 500px; height: 500px; background: var(--primary-gold); top: -200px; right: -200px; animation: orbFloat1 20s ease-in-out infinite; }
        .orb-2 { width: 400px; height: 400px; background: var(--primary-gold-dark); bottom: -150px; left: -150px; animation: orbFloat2 25s ease-in-out infinite; }
        @keyframes orbFloat1 { 0%,100% { transform: translate(0,0); } 50% { transform: translate(-100px, 100px); } }
        @keyframes orbFloat2 { 0%,100% { transform: translate(0,0); } 50% { transform: translate(100px, -100px); } }

        .scroll-progress { position: fixed; top: 0; left: 0; width: 0%; height: 3px; background: linear-gradient(90deg, var(--primary-gold-dark), var(--primary-gold-light)); z-index: 1002; transition: width 0.1s; box-shadow: 0 0 10px var(--primary-gold); }

        /* ===== شاشة التحميل ===== */
        .dev-loader { position: fixed; inset: 0; background: #050505; z-index: 10000; display: flex; justify-content: center; align-items: center; flex-direction: column; transition: opacity 0.8s ease, visibility 0.8s ease; overflow: hidden; padding: 20px; }
        .dev-loader.hidden { opacity: 0; visibility: hidden; }
        .dev-loader::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(transparent 90%, rgba(201, 169, 97, 0.05) 80%); background-size: 100% 4px; animation: scanlines 8s linear infinite; pointer-events: none; }
        @keyframes scanlines { 0% { background-position: 0 0; } 100% { background-position: 0 100%; } }

        .dev-loader-box { width: 100%; max-width: 500px; background: rgba(10, 10, 10, 0.9); border: 1px solid var(--primary-gold-dark); border-radius: 12px; box-shadow: 0 0 40px rgba(201, 169, 97, 0.15); overflow: hidden; backdrop-filter: blur(10px); }
        .dev-loader-header { background: rgba(201, 169, 97, 0.1); padding: 8px 15px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--border-color); }
        .dev-dots { display: flex; gap: 6px; }
        .dev-dots span { width: 10px; height: 10px; border-radius: 50%; background: var(--primary-gold-dark); opacity: 0.7; }
        .dev-loader-title { font-family: 'Share Tech Mono', monospace; color: var(--primary-gold); font-size: 12px; margin-right: auto; letter-spacing: 1px; }

        .dev-loader-content { padding: 25px; font-family: 'Share Tech Mono', monospace; }
        .dev-log { color: var(--primary-gold-light); font-size: 13px; margin-bottom: 6px; display: flex; align-items: center; gap: 10px; opacity: 0; transform: translateY(10px); animation: logAppear 0.4s forwards; }
        .dev-log::before { content: '>'; color: var(--primary-gold); }
        .dev-log.success::before { content: '\\2713'; color: #2ecc71; }
        .dev-log.error::before { content: '\\2717'; color: #e74c3c; }
        @keyframes logAppear { to { opacity: 1; transform: translateY(0); } }

        .dev-progress-wrap { margin-top: 20px; border-top: 1px dashed var(--border-color); padding-top: 15px; }
        .dev-progress-bar { width: 100%; height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; }
        .dev-progress-fill { height: 100%; width: 0%; background: linear-gradient(90deg, transparent, var(--primary-gold), var(--primary-gold-light)); box-shadow: 0 0 15px var(--primary-gold); transition: width 0.2s ease-out; }
        .dev-percent { text-align: right; color: #fff; font-size: 12px; margin-top: 5px; display: block; }

        /* ===== شريط الإعلان ===== */
        .top-bar { position: fixed; top: 0; left: 0; width: 100%; z-index: 1001; background: linear-gradient(90deg, #0a0a0a, #141414, #0a0a0a); border-bottom: 1px solid var(--border-color); box-shadow: 0 2px 15px rgba(0,0,0,0.5); overflow: hidden; height: 35px; display: flex; align-items: center; }
        .top-bar::before, .top-bar::after { content: ''; position: absolute; top: 0; width: 80px; height: 100%; z-index: 2; pointer-events: none; }
        .top-bar::before { left: 0; background: linear-gradient(to right, #0a0a0a, transparent); }
        .top-bar::after { right: 0; background: linear-gradient(to left, #0a0a0a, transparent); }
        [data-theme="light"] .top-bar { background: linear-gradient(90deg, #F5F5F5, #FFFFFF, #F5F5F5); }
        [data-theme="light"] .top-bar::before { background: linear-gradient(to right, #F5F5F5, transparent); }
        [data-theme="light"] .top-bar::after { background: linear-gradient(to left, #F5F5F5, transparent); }

        .marquee-wrapper { display: flex; width: max-content; animation: modern-marquee 30s linear infinite; }
        .marquee-content { display: flex; align-items: center; gap: 40px; padding: 0 20px; }
        .marquee-item { color: var(--primary-gold-light); font-size: clamp(11px, 3vw, 13px); font-weight: 600; font-family: 'Cairo', sans-serif; text-shadow: 0 0 8px rgba(201, 169, 97, 0.6); display: flex; align-items: center; gap: 40px; white-space: nowrap; }
        .marquee-item .icon { color: var(--primary-gold); font-size: 8px; animation: pulse-icon 1.5s infinite; }
        @keyframes modern-marquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        @keyframes pulse-icon { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

        /* ===== شريط التنقل ===== */
        .navbar { position: fixed; top: 35px; left: 0; width: 100%; z-index: 1000; background: var(--glass-bg); backdrop-filter: blur(20px); border-bottom: 1px solid var(--border-color); transition: top 0.4s; }
        .navbar.hide-nav { top: -65px; }
        .nav-container { max-width: var(--max-width); margin: 0 auto; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; }
        .nav-logo { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .nav-logo img { width: 42px; height: 42px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); transition: transform 0.3s; }
        .nav-logo:hover img { transform: scale(1.1) rotate(5deg); }
        .logo-text h1 { font-family: 'Amiri', serif; font-size: clamp(16px, 4vw, 22px); color: var(--primary-gold); line-height: 1.2; }
        .logo-text p { font-size: 9px; color: var(--text-muted); letter-spacing: 1px; }
        .nav-actions { display: flex; gap: 10px; align-items: center; }

        .search-box { position: relative; display: flex; align-items: center; }
        .search-box input { background: rgba(255,255,255,0.05); border: 1px solid var(--border-color); border-radius: 20px; padding: 6px 15px; color: var(--text-light); font-family: 'Cairo'; font-size: 12px; outline: none; width: 120px; transition: width 0.3s, border-color 0.3s; }
        .search-box input:focus { width: 180px; border-color: var(--primary-gold); box-shadow: 0 0 15px rgba(201,169,97,0.2); }
        .search-box i { position: absolute; right: 10px; color: var(--text-muted); font-size: 12px; pointer-events: none; }

        .nav-btn { background: none; border: 1px solid var(--border-color); color: var(--text-light); width: 38px; height: 38px; border-radius: 50%; font-size: 15px; transition: 0.3s; display: flex; justify-content: center; align-items: center; cursor: pointer; position: relative; }
        .nav-btn:hover { background: var(--primary-gold); color: #000; transform: scale(1.1); }
        .nav-btn .badge { position: absolute; top: -2px; right: -2px; background: #e74c3c; color: #fff; font-size: 10px; min-width: 18px; height: 18px; border-radius: 9px; display: flex; justify-content: center; align-items: center; font-weight: 700; padding: 0 4px; animation: badgePulse 2s infinite; }
        .nav-btn .badge.hidden { display: none; }
        @keyframes badgePulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.15); } }

        .theme-toggle:hover { transform: rotate(180deg); }
        .mobile-btn { display: flex; flex-direction: column; gap: 4px; border: none; }
        .mobile-btn span { display: block; width: 20px; height: 2px; background: var(--text-light); transition: all 0.3s; }
        .mobile-btn.active span:nth-child(1) { transform: rotate(45deg) translate(5px, 5px); }
        .mobile-btn.active span:nth-child(2) { opacity: 0; }
        .mobile-btn.active span:nth-child(3) { transform: rotate(-45deg) translate(5px, -5px); }

        /* ===== قائمة الإشعارات المنبثقة ===== */
        .notif-dropdown { position: fixed; top: 80px; left: 20px; width: 350px; max-height: 500px; background: var(--glass-bg); backdrop-filter: blur(20px); border: 1px solid var(--border-color); border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.5); z-index: 1001; overflow: hidden; opacity: 0; transform: translateY(-20px) scale(0.95); pointer-events: none; transition: all 0.3s; }
        .notif-dropdown.active { opacity: 1; transform: translateY(0) scale(1); pointer-events: auto; }
        .notif-dropdown-header { padding: 15px 20px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; background: rgba(201,169,97,0.05); }
        .notif-dropdown-header h3 { color: var(--primary-gold); font-size: 16px; font-family: 'Amiri', serif; }
        .notif-dropdown-close { background: none; border: none; color: var(--text-muted); font-size: 18px; cursor: pointer; transition: color 0.3s; }
        .notif-dropdown-close:hover { color: var(--notif-error); }
        .notif-list { max-height: 380px; overflow-y: auto; padding: 10px; }
        .notif-list::-webkit-scrollbar { width: 5px; }
        .notif-list::-webkit-scrollbar-thumb { background: var(--primary-gold-dark); border-radius: 3px; }
        .notif-item { padding: 12px 15px; border-radius: 10px; margin-bottom: 8px; background: var(--dark-bg-3); border-left: 3px solid var(--primary-gold); transition: all 0.3s; cursor: pointer; }
        .notif-item:hover { transform: translateX(-5px); box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        .notif-item.success { border-left-color: var(--notif-success); }
        .notif-item.info { border-left-color: var(--notif-info); }
        .notif-item.warning { border-left-color: var(--notif-warning); }
        .notif-item.error { border-left-color: var(--notif-error); }
        .notif-item-title { font-weight: 700; font-size: 14px; color: var(--text-light); margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }
        .notif-item-message { font-size: 12px; color: var(--text-muted); line-height: 1.5; }
        .notif-item-time { font-size: 10px; color: var(--text-muted); margin-top: 6px; text-align: left; }
        .notif-empty { text-align: center; padding: 40px 20px; color: var(--text-muted); font-size: 14px; }
        .notif-empty i { font-size: 40px; color: var(--border-color); margin-bottom: 15px; display: block; }

        /* ===== القائمة الكاملة ===== */
        .fullscreen-menu { position: fixed; top: 0; right: -100%; width: 100%; height: 100vh; background: rgba(10,10,10,0.98); backdrop-filter: blur(20px); z-index: 999; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 30px; transition: right 0.5s cubic-bezier(0.77, 0, 0.175, 1); }
        .fullscreen-menu.active { right: 0; }
        .fullscreen-menu a { color: var(--text-light); text-decoration: none; font-family: 'Amiri', serif; font-size: clamp(28px, 8vw, 40px); opacity: 0; transform: translateX(50px); transition: all 0.5s; cursor: pointer; }
        .fullscreen-menu.active a { opacity: 1; transform: translateX(0); }
        .fullscreen-menu.active a:nth-child(1) { transition-delay: 0.2s; }
        .fullscreen-menu.active a:nth-child(2) { transition-delay: 0.3s; }
        .fullscreen-menu.active a:nth-child(3) { transition-delay: 0.4s; }
        .fullscreen-menu.active a:nth-child(4) { transition-delay: 0.5s; }
        .fullscreen-menu a:hover { color: var(--primary-gold); text-shadow: 0 0 20px var(--primary-gold); }

        /* ===== المحتوى الرئيسي ===== */
        .main-content { margin-top: 120px; padding: 0 20px 50px; max-width: var(--max-width); margin-left: auto; margin-right: auto; }
        .reveal { opacity: 0; transform: translateY(50px); transition: all 1s cubic-bezier(0.5, 0, 0, 1); }
        .reveal.active { opacity: 1; transform: translateY(0); }

        .wave-divider { width: 100%; height: 80px; overflow: hidden; line-height: 0; margin: 40px 0; }
        .wave-divider svg { position: relative; display: block; width: calc(100% + 1.3px); height: 100%; }
        .wave-divider .shape-fill { fill: var(--dark-bg-2); }

        /* ===== السلايدر الرئيسي ===== */
        .main-slider { height: clamp(300px, 55vh, 550px); border-radius: 20px; overflow: hidden; margin-bottom: 40px; box-shadow: var(--shadow-gold); border: 1px solid var(--border-color); }
        .main-slider .swiper-slide { position: relative; }
        .main-slider .swiper-slide img { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.5); }
        .ad-slider-overlay { position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #fff; text-align: center; padding: 20px; background: linear-gradient(to top, rgba(0,0,0,0.9), transparent); }
        .ad-slider-overlay h2 { font-family: 'Amiri', serif; font-size: clamp(24px, 6vw, 42px); color: var(--primary-gold); margin-bottom: 15px; text-shadow: 0 0 20px rgba(201,169,97,0.5); }
        .typing-text { border-right: 2px solid var(--primary-gold); white-space: nowrap; overflow: hidden; font-size: clamp(14px, 4vw, 22px); max-width: 90%; animation: typing 4s steps(40, end), blink-caret .75s step-end infinite; background: linear-gradient(90deg, #E5C77C, #C9A961); -webkit-background-clip: text; background-clip: text; color: transparent; font-weight: 700; }
        @keyframes typing { from { width: 0 } to { width: 100% } }
        @keyframes blink-caret { from, to { border-color: transparent } 50% { border-color: var(--primary-gold) } }

        /* ===== شريط المعلومات ===== */
        .info-bar { display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; margin-bottom: 50px; padding: 20px; background: var(--glass-bg); border-radius: 16px; border: 1px solid var(--border-color); backdrop-filter: blur(10px); }
        .info-item { display: flex; align-items: center; gap: 10px; padding: 8px 16px; background: var(--dark-bg-3); border-radius: 10px; border: 1px solid var(--border-color); transition: all 0.3s; flex: 1; min-width: 200px; justify-content: center; }
        .info-item:hover { border-color: var(--primary-gold); transform: translateY(-3px); box-shadow: 0 5px 20px rgba(201,169,97,0.1); }
        .info-item i { color: var(--primary-gold); font-size: 18px; }
        .info-item span { color: var(--text-light); font-size: 13px; font-weight: 600; }

        /* ===== عناوين الأقسام ===== */
        .section { margin-bottom: 80px; }
        .section-header { text-align: center; margin-bottom: 40px; }
        .section-header h2 { font-family: 'Amiri', serif; font-size: clamp(28px, 6vw, 42px); color: var(--text-light); margin-bottom: 15px; position: relative; display: inline-block; }
        .section-header h2 span { color: var(--primary-gold); }
        .section-header h2::after { content: ''; position: absolute; bottom: -10px; left: 50%; transform: translateX(-50%); width: 60px; height: 3px; background: var(--primary-gold); box-shadow: 0 0 10px var(--primary-gold); }

        /* ===== شبكة الأقسام (عمودين بجانب بعض) ===== */
        .categories-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 25px; }
        .category-card { background: var(--glass-bg); border: 1px solid var(--border-color); border-radius: 16px; overflow: hidden; transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1); position: relative; cursor: pointer; will-change: transform; }
        .category-card::before { content: ''; position: absolute; inset: 0; border-radius: 16px; padding: 1px; background: radial-gradient(300px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(201, 169, 97, 0.8), transparent 40%); -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); -webkit-mask-composite: xor; mask-composite: exclude; opacity: 0; transition: opacity 0.3s; z-index: 2; pointer-events: none; }
        .category-card:hover::before { opacity: 1; }
        .category-card:hover { border-color: var(--primary-gold); transform: translateY(-8px); box-shadow: 0 20px 50px rgba(201,169,97,0.15); }
        .category-img { height: 220px; overflow: hidden; position: relative; }
        .category-img img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.8s; }
        .category-card:hover .category-img img { transform: scale(1.1); }
        .category-img::after { content: ''; position: absolute; inset: 0; background: linear-gradient(to top, rgba(0,0,0,0.7), transparent 60%); }
        .category-info { padding: 20px; text-align: center; z-index: 3; position: relative; }
        .category-info h3 { color: var(--text-light); font-size: clamp(16px, 4vw, 20px); font-weight: 700; margin-bottom: 8px; }
        .category-info p { color: var(--primary-gold); font-size: 12px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 5px; }
        .category-info p i { font-size: 10px; transition: transform 0.3s; }
        .category-card:hover .category-info p i { transform: translateX(-5px); }
        .category-badge { position: absolute; top: 15px; right: 15px; background: var(--primary-gold); color: #000; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; z-index: 4; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }

        /* ===== صفحة منتجات القسم ===== */
        .products-view { display: none; }
        .products-view.active { display: block; animation: fadeInUp 0.6s ease; }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        .products-view-header { display: flex; align-items: center; gap: 15px; margin-bottom: 30px; }
        .back-btn { background: var(--glass-bg); border: 1px solid var(--border-color); color: var(--text-light); padding: 10px 20px; border-radius: 12px; font-family: 'Cairo'; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; display: flex; align-items: center; gap: 8px; }
        .back-btn:hover { background: var(--primary-gold); color: #000; border-color: var(--primary-gold); transform: translateX(5px); }
        .products-view-title { font-family: 'Amiri', serif; font-size: clamp(24px, 5vw, 36px); color: var(--primary-gold); }
        .products-view-banner { width: 100%; height: 200px; border-radius: 16px; overflow: hidden; margin-bottom: 30px; position: relative; box-shadow: var(--shadow-gold); }
        .products-view-banner img { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.6); }
        .products-view-banner h3 { position: absolute; inset: 0; display: flex; justify-content: center; align-items: center; color: var(--primary-gold); font-family: 'Amiri', serif; font-size: clamp(24px, 6vw, 40px); text-shadow: 0 0 30px rgba(0,0,0,0.8); }

        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
        .product-card { background: var(--glass-bg); border: 1px solid var(--border-color); border-radius: 16px; overflow: hidden; transition: all 0.4s; position: relative; will-change: transform; cursor: pointer; }
        .product-card:hover { border-color: var(--primary-gold); transform: translateY(-8px); box-shadow: 0 15px 40px rgba(201,169,97,0.1); }
        .product-img { height: 180px; overflow: hidden; }
        .product-img img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.6s; }
        .product-card:hover .product-img img { transform: scale(1.15); }
        .product-info { padding: 15px; text-align: center; }
        .product-info h4 { color: var(--text-light); margin-bottom: 8px; font-size: clamp(14px, 3vw, 16px); }
        .product-price { color: var(--primary-gold); font-weight: 700; font-size: clamp(16px, 4vw, 18px); }
        .product-buy-btn { margin-top: 10px; width: 100%; padding: 8px; background: var(--primary-gold-dark); color: #fff; border: none; border-radius: 8px; font-family: 'Cairo'; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
        .product-buy-btn:hover { background: var(--primary-gold); color: #000; }
        .no-products { text-align: center; padding: 60px 20px; color: var(--text-muted); }
        .no-products i { font-size: 60px; color: var(--border-color); margin-bottom: 20px; display: block; }
        .no-products p { font-size: 18px; }

        /* ===== العروض ===== */
        .offers-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 30px; }
        .offer-card { background: var(--glass-bg); border: 1px solid var(--border-color); border-radius: 16px; overflow: hidden; transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1); position: relative; will-change: transform; cursor: pointer; }
        .offer-card::before { content: ''; position: absolute; inset: 0; border-radius: 16px; padding: 1px; background: radial-gradient(300px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(201, 169, 97, 0.8), transparent 40%); -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); -webkit-mask-composite: xor; mask-composite: exclude; opacity: 0; transition: opacity 0.3s; z-index: 2; pointer-events: none; }
        .offer-card:hover::before { opacity: 1; }
        .offer-card:hover { border-color: var(--primary-gold); transform: translateY(-8px); box-shadow: 0 20px 50px rgba(201,169,97,0.15); }
        .offer-img { height: 250px; overflow: hidden; position: relative; }
        .offer-img img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.8s; }
        .offer-card:hover .offer-img img { transform: scale(1.1); }
        .offer-badge { position: absolute; top: 15px; right: 15px; background: var(--primary-gold); color: #000; padding: 5px 14px; border-radius: 15px; font-size: 11px; z-index: 4; font-weight: bold; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .offer-info { padding: 25px; z-index: 3; position: relative; }
        .offer-info h3 { color: var(--primary-gold); font-size: clamp(18px, 4vw, 22px); margin-bottom: 15px; }
        .offer-info p { color: var(--text-muted); font-size: 14px; line-height: 1.6; margin-bottom: 15px; }
        .offer-price { font-family: 'Amiri', serif; font-size: clamp(22px, 5vw, 26px); color: var(--primary-gold-light); font-weight: 700; }

        /* ===== الفيديو ===== */
        .video-section { margin: 80px 0; border-radius: 20px; overflow: hidden; box-shadow: var(--shadow-gold); border: 1px solid var(--border-color); position: relative; height: clamp(300px, 50vh, 500px); }
        .video-section video { width: 100%; height: 100%; object-fit: cover; }
        .video-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; pointer-events: none; }
        .video-overlay h2 { font-family: 'Amiri', serif; font-size: clamp(28px, 6vw, 40px); color: #fff; text-shadow: 0 4px 15px rgba(0,0,0,0.8); }

        /* ===== قسم نبذة عنا ===== */
        .about-section { text-align: center; padding: 40px 20px; background: var(--glass-bg); border-radius: 20px; border: 1px solid var(--border-color); }
        .about-section h3 { font-family: 'Amiri', serif; font-size: clamp(24px, 5vw, 36px); color: var(--primary-gold); margin-bottom: 20px; }
        .about-section p { color: var(--text-muted); font-size: 16px; line-height: 1.8; max-width: 800px; margin: 0 auto; }

        /* ===== الأزرار العائمة (FAB) ===== */
        .fab-container { position: fixed; bottom: 20px; left: 20px; z-index: 9999; display: flex; flex-direction: column; align-items: center; gap: 12px; }
        .fab-robot { width: 55px; height: 55px; border-radius: 50%; background: linear-gradient(145deg, var(--primary-gold-dark), var(--primary-gold-light)); border: none; color: #0f0f0f; font-size: 24px; cursor: pointer; box-shadow: 0 5px 20px rgba(201, 169, 97, 0.6); transition: all 0.3s ease; display: flex; justify-content: center; align-items: center; animation: float 3s ease-in-out infinite; position: relative; z-index: 10; }
        .fab-robot:hover { transform: scale(1.1) rotate(10deg); box-shadow: 0 8px 25px rgba(201, 169, 97, 0.9); }
        .fab-robot.active { animation: none; transform: rotate(135deg); background: #e74c3c; color: #fff; }
        @keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-8px); } }

        .fab-menu-items { display: flex; flex-direction: column; gap: 10px; margin-bottom: 5px; opacity: 0; transform: translateY(20px) scale(0.8); pointer-events: none; transition: all 0.3s ease; }
        .fab-menu-items.active { opacity: 1; transform: translateY(0) scale(1); pointer-events: auto; }
        .fab-menu-item { width: 45px; height: 45px; border-radius: 50%; background: var(--dark-bg-2); border: 1px solid var(--primary-gold); color: var(--primary-gold); display: flex; justify-content: center; align-items: center; text-decoration: none; font-size: 18px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); transition: all 0.3s; position: relative; }
        .fab-menu-item:hover { background: var(--primary-gold); color: #000; transform: scale(1.1); }
        .fab-menu-item::after { content: attr(data-tooltip); position: absolute; left: 60px; background: #000; color: #fff; padding: 4px 10px; border-radius: 4px; font-size: 12px; white-space: nowrap; opacity: 0; pointer-events: none; transition: opacity 0.3s; font-family: 'Cairo'; }
        .fab-menu-item:hover::after { opacity: 1; }

        .back-to-top { position: fixed; bottom: 20px; right: 20px; width: 45px; height: 45px; background: var(--primary-gold); color: #000; border: none; border-radius: 50%; font-size: 18px; opacity: 0; transition: all 0.4s; transform: scale(0.5); cursor: pointer; z-index: 999; display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 15px rgba(201, 169, 97, 0.4); }
        .back-to-top.visible { opacity: 1; transform: scale(1); }
        .back-to-top:hover { background: var(--primary-gold-light); transform: translateY(-3px); }

        /* ===== الإشعارات المنبثقة (Toast) ===== */
        .toast-container { position: fixed; top: 80px; right: 20px; z-index: 10001; display: flex; flex-direction: column; gap: 10px; max-width: 400px; }
        .toast { background: var(--glass-bg); backdrop-filter: blur(20px); border: 1px solid var(--border-color); border-radius: 12px; padding: 15px 20px; display: flex; align-items: flex-start; gap: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.4); transition: all 0.4s ease; position: relative; overflow: hidden; }
        .toast.success { border-left: 4px solid var(--notif-success); }
        .toast.info { border-left: 4px solid var(--notif-info); }
        .toast.warning { border-left: 4px solid var(--notif-warning); }
        .toast.error { border-left: 4px solid var(--notif-error); }
        .toast-icon { font-size: 20px; margin-top: 2px; }
        .toast.success .toast-icon { color: var(--notif-success); }
        .toast.info .toast-icon { color: var(--notif-info); }
        .toast.warning .toast-icon { color: var(--notif-warning); }
        .toast.error .toast-icon { color: var(--notif-error); }
        .toast-content { flex: 1; }
        .toast-content h4 { color: var(--text-light); font-size: 14px; font-weight: 700; margin-bottom: 4px; }
        .toast-content p { color: var(--text-muted); font-size: 12px; line-height: 1.5; }
        .toast-close { background: none; border: none; color: var(--text-muted); font-size: 14px; cursor: pointer; padding: 0; margin-top: 2px; }
        .toast-close:hover { color: var(--notif-error); }
        .toast-progress { position: absolute; bottom: 0; left: 0; height: 3px; background: var(--primary-gold); width: 100%; transform-origin: right; }

        /* ===== Responsive ===== */
        @media (min-width: 992px) {
            .fab-robot { width: 60px; height: 60px; font-size: 26px; }
            .back-to-top { width: 50px; height: 50px; font-size: 20px; }
        }

        @media (max-width: 768px) {
            .main-content { margin-top: 100px; padding: 0 15px 30px; }
            .categories-grid { grid-template-columns: 1fr; gap: 15px; }
            .products-grid { grid-template-columns: repeat(2, 1fr); gap: 12px; }
            .offers-grid { grid-template-columns: 1fr; gap: 20px; }
            .product-img { height: 130px; }
            .search-box { display: none; }
            .logo-text p { display: none; }
            .nav-container { padding: 8px 15px; }
            .info-bar { flex-direction: column; }
            .info-item { min-width: 100%; }
            .notif-dropdown { width: calc(100vw - 40px); left: 10px; right: 10px; }
            .toast-container { right: 10px; left: 10px; max-width: none; }
        }

        @media (max-width: 480px) {
            .products-grid { grid-template-columns: 1fr; }
            .fab-menu-item::after { display: none; }
            .category-img { height: 180px; }
        }
    </style>
</head>
<body>
    <canvas id="particles-bg"></canvas>
    <div class="gradient-orb orb-1"></div>
    <div class="gradient-orb orb-2"></div>
    <div class="scroll-progress" id="scrollProgress"></div>

    <!-- شاشة التحميل -->
    <div class="dev-loader" id="devLoader">
        <div class="dev-loader-box">
            <div class="dev-loader-header">
                <div class="dev-dots"><span></span><span></span><span></span></div>
                <p class="dev-loader-title">SYSTEM_INIT.exe</p>
            </div>
            <div class="dev-loader-content">
                <div class="dev-log" style="animation-delay: 0.1s">Initializing Core Modules...</div>
                <div class="dev-log success" style="animation-delay: 0.4s">Core Modules Loaded</div>
                <div class="dev-log" style="animation-delay: 0.7s">Fetching Assets from Database...</div>
                <div class="dev-log success" style="animation-delay: 1.0s">Assets Synced</div>
                <div class="dev-log" style="animation-delay: 1.3s">Rendering UI Components...</div>
                <div class="dev-progress-wrap">
                    <div class="dev-progress-bar"><div class="dev-progress-fill" id="devBarFill"></div></div>
                    <span class="dev-percent" id="devPercent">0%</span>
                </div>
            </div>
        </div>
    </div>

    <!-- شريط الإعلان -->
    <div class="top-bar">
        <div class="marquee-wrapper" id="marqueeWrapper">
            <div class="marquee-content">
                <span class="marquee-item">%ANNOUNCEMENT_ITEM_1% <i class="fas fa-star icon"></i> %ANNOUNCEMENT_ITEM_2% <i class="fas fa-star icon"></i> %ANNOUNCEMENT_ITEM_3%</span>
            </div>
            <div class="marquee-content" aria-hidden="true">
                <span class="marquee-item">%ANNOUNCEMENT_ITEM_1% <i class="fas fa-star icon"></i> %ANNOUNCEMENT_ITEM_2% <i class="fas fa-star icon"></i> %ANNOUNCEMENT_ITEM_3%</span>
            </div>
        </div>
    </div>

    <!-- شريط التنقل -->
    <nav class="navbar" id="navbar">
        <div class="nav-container">
            <div class="nav-logo" onclick="goHome()">
                <img src="%LOGO_URL%" alt="Logo">
                <div class="logo-text">
                    <h1>مكتبة الشاغور</h1>
                    <p>AL-SHAGHOUR MODERN LIBRARY</p>
                </div>
            </div>
            <div class="nav-actions">
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="ابحث عن منتج..." oninput="searchProducts()">
                    <i class="fas fa-search"></i>
                </div>
                <button class="nav-btn" id="notifBtn" title="الإشعارات">
                    <i class="fas fa-bell"></i>
                    <span class="badge hidden" id="notifBadge">0</span>
                </button>
                <button class="nav-btn theme-toggle" id="themeToggle" title="الوضع الليلي/النهاري">
                    <i class="fas fa-moon"></i>
                </button>
                <button class="nav-btn mobile-btn" id="mobileBtn">
                    <span></span><span></span><span></span>
                </button>
            </div>
        </div>
    </nav>

    <!-- قائمة الإشعارات المنبثقة -->
    <div class="notif-dropdown" id="notifDropdown">
        <div class="notif-dropdown-header">
            <h3>الإشعارات</h3>
            <button class="notif-dropdown-close" onclick="toggleNotifDropdown()">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="notif-list" id="notifList">
            <div class="notif-empty">
                <i class="fas fa-bell-slash"></i>
                <p>لا توجد إشعارات حالياً</p>
            </div>
        </div>
    </div>

    <!-- القائمة الكاملة -->
    <div class="fullscreen-menu" id="fullscreenMenu">
        <a onclick="goHome()">الرئيسية</a>
        <a onclick="scrollToSection('categories')">الأقسام</a>
        <a onclick="scrollToSection('offers')">العروض</a>
        <a onclick="scrollToSection('about')">نبذة عنا</a>
    </div>

    <!-- المحتوى الرئيسي -->
    <div class="main-content" id="mainContent">
        <!-- السلايدر -->
        <div class="swiper main-slider" id="home">
            <div class="swiper-wrapper">%SLIDER_HTML%</div>
            <div class="swiper-pagination"></div>
        </div>

        <!-- شريط المعلومات -->
        <div class="info-bar reveal">
            <div class="info-item">
                <i class="fas fa-map-marker-alt"></i>
                <span>%LIBRARY_ADDRESS%</span>
            </div>
            <div class="info-item">
                <i class="fas fa-clock"></i>
                <span>%WORKING_HOURS%</span>
            </div>
            <div class="info-item">
                <i class="fas fa-phone-alt"></i>
                <span>%PHONE_NUMBER%</span>
            </div>
        </div>

        <div class="wave-divider">
            <svg data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 120" preserveAspectRatio="none">
                <path d="M321.39,56.44c58-10.79,114.16-30.13,172-41.86,82.39-16.72,168.19-17.73,250.45-.39C823.78,31,906.67,72,985.66,92.83c70.05,18.48,146.53,26.09,214.34,3V0H0V27.35A600.21,600.21,0,0,0,321.39,56.44Z" class="shape-fill"></path>
            </svg>
        </div>

        <!-- قسم الأقسام -->
        <section class="section reveal" id="categories">
            <div class="section-header"><h2>تصفح <span>الأقسام</span></h2></div>
            <div class="categories-grid" id="categoriesGrid">%CATEGORIES_HTML%</div>
        </section>

        <!-- صفحة عرض منتجات القسم -->
        <section class="section products-view" id="productsView">
            <div class="products-view-header">
                <button class="back-btn" onclick="goBackToCategories()">
                    <i class="fas fa-arrow-right"></i> رجوع للأقسام
                </button>
                <h2 class="products-view-title" id="productsViewTitle"></h2>
            </div>
            <div class="products-view-banner" id="productsViewBanner">
                <img src="" alt="Category Banner" id="productsViewBannerImg">
                <h3 id="productsViewBannerTitle"></h3>
            </div>
            <div class="products-grid" id="productsGrid"></div>
        </section>

        <!-- العروض -->
        <section class="section reveal" id="offers">
            <div class="section-header"><h2>أحدث <span>العروض</span></h2></div>
            <div class="offers-grid">%OFFERS_HTML%</div>
        </section>

        <!-- الفيديو -->
        <section class="section reveal" id="video">
            <div class="section-header"><h2>شاهد <span>الفيديو</span></h2></div>
            <div class="video-section">
                <video src="%VIDEO_URL%" muted loop playsinline id="autoplayVideo"></video>
                <div class="video-overlay"><h2>إبداعات القرطاسية</h2></div>
            </div>
        </section>

        <!-- نبذة عنا -->
        <section class="section reveal" id="about">
            <div class="about-section">
                <h3>نبذة <span style="color:var(--primary-gold)">عنا</span></h3>
                <p>%ABOUT_TEXT%</p>
            </div>
        </section>
    </div>

    <!-- الأزرار العائمة -->
    <div class="fab-container">
        <div class="fab-menu-items" id="fabMenu">
            <a href="https://wa.me/%WHATSAPP%" target="_blank" class="fab-menu-item" data-tooltip="واتساب"><i class="fab fa-whatsapp"></i></a>
            <a href="https://instagram.com/%INSTAGRAM%" target="_blank" class="fab-menu-item" data-tooltip="إنستغرام"><i class="fab fa-instagram"></i></a>
            <a href="mailto:%GMAIL%" class="fab-menu-item" data-tooltip="جيميل"><i class="fas fa-envelope"></i></a>
            <a href="tel:%PHONE_NUMBER%" class="fab-menu-item" data-tooltip="اتصل بنا"><i class="fas fa-phone"></i></a>
        </div>
        <button class="fab-robot" id="fabRobot" title="قائمة التواصل">
            <i class="fas fa-plus" id="fabIcon"></i>
        </button>
    </div>

    <button class="back-to-top" id="backToTop" title="للأعلى"><i class="fas fa-arrow-up"></i></button>

    <!-- حاوية الإشعارات المنبثقة -->
    <div class="toast-container" id="toastContainer"></div>

    <!-- بيانات JSON للجافاسكربت -->
    <script id="categories-data" type="application/json">%CATEGORIES_JSON%</script>
    <script id="notifications-data" type="application/json">%NOTIFICATIONS_JSON%</script>

    <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
    <script>
        // ===== متغيرات عامة =====
        let categoriesData = [];
        let notificationsData = [];
        let lastNotifTimestamp = 0;
        let unreadNotifCount = 0;

        // ===== شاشة التحميل =====
        let devProgress = 0;
        const devLoader = document.getElementById('devLoader');
        const devPercentText = document.getElementById('devPercent');
        const devBarFill = document.getElementById('devBarFill');
        const devInterval = setInterval(() => {
            devProgress += Math.random() * 15 + 5;
            if (devProgress >= 100) {
                devProgress = 100;
                clearInterval(devInterval);
                devPercentText.innerText = '100%';
                devBarFill.style.width = '100%';
                setTimeout(() => { devLoader.classList.add('hidden'); }, 800);
            } else {
                devPercentText.innerText = Math.floor(devProgress) + '%';
                devBarFill.style.width = devProgress + '%';
            }
        }, 200);
        setTimeout(() => { devLoader.classList.add('hidden'); }, 5000);

        // ===== تحميل البيانات =====
        try {
            categoriesData = JSON.parse(document.getElementById('categories-data').textContent);
        } catch(e) { console.error('Error parsing categories data:', e); }
        try {
            notificationsData = JSON.parse(document.getElementById('notifications-data').textContent);
            notificationsData.forEach(n => { if (n.timestamp > lastNotifTimestamp) lastNotifTimestamp = n.timestamp; });
        } catch(e) { console.error('Error parsing notifications data:', e); }

        // ===== الجزيئات الخلفية =====
        const canvas = document.getElementById('particles-bg');
        const ctx = canvas.getContext('2d');
        let particles = [];
        function resizeCanvas() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        class Particle {
            constructor() { this.reset(); }
            reset() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2 + 1;
                this.speedX = Math.random() * 0.5 - 0.25;
                this.speedY = Math.random() * 0.5 - 0.25;
            }
            update() {
                this.x += this.speedX; this.y += this.speedY;
                if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
                if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
            }
            draw() {
                ctx.fillStyle = 'rgba(201,169,97,0.5)';
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        function initParticles() { particles = []; for (let i = 0; i < 40; i++) particles.push(new Particle()); }
        function connectParticles() {
            for (let a = 0; a < particles.length; a++) {
                for (let b = a; b < particles.length; b++) {
                    let dist = Math.hypot(particles[a].x - particles[b].x, particles[a].y - particles[b].y);
                    if (dist < 120) {
                        ctx.strokeStyle = 'rgba(201,169,97,' + (0.2 - dist / 600) + ')';
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(particles[a].x, particles[a].y);
                        ctx.lineTo(particles[b].x, particles[b].y);
                        ctx.stroke();
                    }
                }
            }
        }
        function animateParticles() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => { p.update(); p.draw(); });
            connectParticles();
            requestAnimationFrame(animateParticles);
        }
        initParticles();
        animateParticles();

        // ===== شريط التنقل والقائمة =====
        const navbar = document.getElementById('navbar');
        const menu = document.getElementById('fullscreenMenu');
        const btn = document.getElementById('mobileBtn');
        let lastScroll = 0;
        window.addEventListener('scroll', () => {
            let st = window.scrollY;
            document.getElementById('scrollProgress').style.width = ((st / (document.body.offsetHeight - window.innerHeight)) * 100) + '%';
            if (st > 300) document.getElementById('backToTop').classList.add('visible');
            else document.getElementById('backToTop').classList.remove('visible');
            if (st > lastScroll && st > 100) navbar.classList.add('hide-nav');
            else navbar.classList.remove('hide-nav');
            lastScroll = st;
        });
        document.getElementById('backToTop').addEventListener('click', () => window.scrollTo({top: 0, behavior: 'smooth'}));
        btn.addEventListener('click', () => { btn.classList.toggle('active'); menu.classList.toggle('active'); });
        function closeMenu() { btn.classList.remove('active'); menu.classList.remove('active'); }

        function scrollToSection(id) {
            closeMenu();
            goHome();
            setTimeout(() => {
                document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
            }, 100);
        }

        // ===== GSAP Animations =====
        gsap.registerPlugin(ScrollTrigger);
        const obs = new IntersectionObserver((entries) => {
            entries.forEach(el => {
                if (el.isIntersecting) {
                    el.target.classList.add('active');
                    gsap.from(el.target.children, { opacity: 0, y: 30, duration: 0.8, stagger: 0.2 });
                }
            });
        }, { threshold: 0.1 });
        document.querySelectorAll('.reveal').forEach(el => obs.observe(el));

        // ===== السلايدر =====
        new Swiper('.main-slider', {
            loop: true, autoplay: { delay: 4000 }, effect: 'fade', fadeEffect: { crossFade: true },
            pagination: { el: '.swiper-pagination' }
        });

        // ===== زر الوضع الليلي والنهاري =====
        const themeToggle = document.getElementById('themeToggle');
        const htmlEl = document.documentElement;
        const savedTheme = localStorage.getItem('theme') || 'dark';
        htmlEl.setAttribute('data-theme', savedTheme);
        themeToggle.innerHTML = savedTheme === 'dark' ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
        themeToggle.addEventListener('click', () => {
            let currentTheme = htmlEl.getAttribute('data-theme');
            let newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            htmlEl.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            themeToggle.innerHTML = newTheme === 'dark' ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
        });

        // ===== الفيديو التلقائي =====
        const video = document.getElementById('autoplayVideo');
        new IntersectionObserver((entries) => {
            entries.forEach(en => { if (en.isIntersecting) video.play().catch(() => {}); else video.pause(); });
        }, { threshold: 0.5 }).observe(video);

        // ===== تأثيرات البطاقات (3D Tilt & Mouse Glow) =====
        function attachCardEffects() {
            document.querySelectorAll('.category-card, .offer-card, .product-card').forEach(card => {
                card.addEventListener('mousemove', e => {
                    let r = card.getBoundingClientRect();
                    card.style.setProperty('--mouse-x', (e.clientX - r.left) + 'px');
                    card.style.setProperty('--mouse-y', (e.clientY - r.top) + 'px');
                    if (window.innerWidth > 992) {
                        let rx = (e.clientY - r.top - r.height / 2) / 20;
                        let ry = (r.width / 2 - (e.clientX - r.left)) / 20;
                        card.style.transform = `perspective(1000px) rotateX(${-rx}deg) rotateY(${-ry}deg) scale(1.03)`;
                    }
                });
                card.addEventListener('mouseleave', () => { card.style.transform = 'none'; });
            });
        }
        attachCardEffects();

        // ===== زر الروبوت العائم =====
        const fabRobot = document.getElementById('fabRobot');
        const fabMenu = document.getElementById('fabMenu');
        fabRobot.addEventListener('click', () => {
            fabRobot.classList.toggle('active');
            fabMenu.classList.toggle('active');
        });

        // ===== نظام الأقسام والمنتجات (SPA) =====
        function showCategoryProducts(catId) {
            const cat = categoriesData.find(c => c.id === catId);
            if (!cat) return;

            // إخفاء الأقسام الرئيسية
            document.getElementById('categories').style.display = 'none';
            document.getElementById('offers').style.display = 'none';
            document.getElementById('video').style.display = 'none';
            document.getElementById('about').style.display = 'none';
            document.querySelector('.info-bar').style.display = 'none';
            document.querySelector('.main-slider').style.display = 'none';
            document.querySelector('.wave-divider').style.display = 'none';

            // إظهار صفحة المنتجات
            const productsView = document.getElementById('productsView');
            productsView.classList.add('active');

            // تعيين العنوان والصورة
            document.getElementById('productsViewTitle').innerText = cat.name;
            document.getElementById('productsViewBannerImg').src = cat.img;
            document.getElementById('productsViewBannerTitle').innerText = cat.name;

            // عرض المنتجات
            const grid = document.getElementById('productsGrid');
            if (cat.products && cat.products.length > 0) {
                grid.innerHTML = cat.products.map(p => `
                    <div class="product-card" onclick="window.open('https://wa.me/%WHATSAPP%?text=اريد شراء: ${encodeURIComponent(p.name)}', '_blank')">
                        <div class="product-img"><img src="${p.img}" alt="${p.name}"></div>
                        <div class="product-info">
                            <h4>${p.name}</h4>
                            <p class="product-price">${p.price} ل.س</p>
                            <button class="product-buy-btn" onclick="event.stopPropagation(); window.open('https://wa.me/%WHATSAPP%?text=اريد شراء: ${encodeURIComponent(p.name)} - ${encodeURIComponent(p.price)} ل.س', '_blank')">
                                <i class="fab fa-whatsapp"></i> اطلب الآن
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                grid.innerHTML = `
                    <div class="no-products" style="grid-column: 1 / -1;">
                        <i class="fas fa-box-open"></i>
                        <p>لا توجد منتجات في هذا القسم حالياً</p>
                    </div>
                `;
            }

            // إعادة ربط تأثيرات البطاقات
            attachCardEffects();

            // التمرير للأعلى
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function goBackToCategories() {
            document.getElementById('productsView').classList.remove('active');
            document.getElementById('categories').style.display = '';
            document.getElementById('offers').style.display = '';
            document.getElementById('video').style.display = '';
            document.getElementById('about').style.display = '';
            document.querySelector('.info-bar').style.display = '';
            document.querySelector('.main-slider').style.display = '';
            document.querySelector('.wave-divider').style.display = '';
            if (window.location.hash) {
                history.replaceState(null, '', window.location.pathname);
            }
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function goHome() {
            closeMenu();
            if (document.getElementById('productsView').classList.contains('active')) {
                goBackToCategories();
            } else {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        }

        // ===== نظام الإشعارات =====
        const notifBtn = document.getElementById('notifBtn');
        const notifDropdown = document.getElementById('notifDropdown');
        const notifList = document.getElementById('notifList');
        const notifBadge = document.getElementById('notifBadge');

        notifBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleNotifDropdown();
        });

        document.addEventListener('click', (e) => {
            if (!notifDropdown.contains(e.target) && !notifBtn.contains(e.target)) {
                notifDropdown.classList.remove('active');
            }
        });

        function toggleNotifDropdown() {
            notifDropdown.classList.toggle('active');
            if (notifDropdown.classList.contains('active')) {
                unreadNotifCount = 0;
                updateNotifBadge();
            }
        }

        function updateNotifBadge() {
            if (unreadNotifCount > 0) {
                notifBadge.textContent = unreadNotifCount;
                notifBadge.classList.remove('hidden');
            } else {
                notifBadge.classList.add('hidden');
            }
        }

        function renderNotifications() {
            if (notificationsData.length === 0) {
                notifList.innerHTML = `
                    <div class="notif-empty">
                        <i class="fas fa-bell-slash"></i>
                        <p>لا توجد إشعارات حالياً</p>
                    </div>
                `;
                return;
            }
            notifList.innerHTML = notificationsData.slice().reverse().map(n => {
                let iconClass = 'fa-info-circle';
                if (n.type === 'success') iconClass = 'fa-check-circle';
                else if (n.type === 'warning') iconClass = 'fa-exclamation-triangle';
                else if (n.type === 'error') iconClass = 'fa-times-circle';
                let timeStr = '';
                try {
                    let d = new Date(n.timestamp * 1000);
                    timeStr = d.toLocaleDateString('ar') + ' ' + d.toLocaleTimeString('ar', {hour:'2-digit',minute:'2-digit'});
                } catch(e) { timeStr = ''; }
                return `
                    <div class="notif-item ${n.type || 'info'}">
                        <div class="notif-item-title">
                            <i class="fas ${iconClass}"></i> ${escapeHtml(n.title || 'إشعار')}
                        </div>
                        <div class="notif-item-message">${escapeHtml(n.message || '')}</div>
                        <div class="notif-item-time">${timeStr}</div>
                    </div>
                `;
            }).join('');
        }

        function escapeHtml(text) {
            let div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function showToast(title, message, type = 'info') {
            let iconClass = 'fa-info-circle';
            if (type === 'success') iconClass = 'fa-check-circle';
            else if (type === 'warning') iconClass = 'fa-exclamation-triangle';
            else if (type === 'error') iconClass = 'fa-times-circle';

            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `
                <div class="toast-icon"><i class="fas ${iconClass}"></i></div>
                <div class="toast-content">
                    <h4>${escapeHtml(title)}</h4>
                    <p>${escapeHtml(message)}</p>
                </div>
                <button class="toast-close" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
                <div class="toast-progress" style="animation: shrinkBar 5s linear forwards;"></div>
            `;
            document.getElementById('toastContainer').appendChild(toast);

            gsap.fromTo(toast, { x: 400, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: 'power3.out' });

            setTimeout(() => {
                gsap.to(toast, {
                    x: 400, opacity: 0, duration: 0.5, ease: 'power3.in',
                    onComplete: () => toast.remove()
                });
            }, 5000);
        }

        // إضافة CSS للأنميشن
        const styleEl = document.createElement('style');
        styleEl.textContent = `@keyframes shrinkBar { from { transform: scaleX(1); } to { transform: scaleX(0); } }`;
        document.head.appendChild(styleEl);

        // عرض الإشعارات الأولية
        renderNotifications();

        // جلب الإشعارات الجديدة كل 30 ثانية
        async function fetchNewNotifications() {
            try {
                const response = await fetch(`/api/notifications?since=${lastNotifTimestamp}`);
                const data = await response.json();
                if (data.notifications && data.notifications.length > 0) {
                    data.notifications.forEach(n => {
                        notificationsData.push(n);
                        if (n.timestamp > lastNotifTimestamp) lastNotifTimestamp = n.timestamp;
                        showToast(n.title || 'إشعار', n.message || '', n.type || 'info');
                        unreadNotifCount++;
                    });
                    updateNotifBadge();
                    renderNotifications();
                }
            } catch (e) {
                console.error('Failed to fetch notifications:', e);
            }
        }
        setInterval(fetchNewNotifications, 30000);

        // ===== البحث =====
        function searchProducts() {
            let input = document.getElementById('searchInput').value.toLowerCase().trim();
            if (input === '') return;

            // البحث في جميع المنتجات
            let results = [];
            categoriesData.forEach(cat => {
                (cat.products || []).forEach(p => {
                    if (p.name.toLowerCase().includes(input)) {
                        results.push({ ...p, categoryName: cat.name, categoryId: cat.id });
                    }
                });
            });

            if (results.length > 0) {
                // عرض النتائج في صفحة المنتجات
                document.getElementById('categories').style.display = 'none';
                document.getElementById('offers').style.display = 'none';
                document.getElementById('video').style.display = 'none';
                document.getElementById('about').style.display = 'none';
                document.querySelector('.info-bar').style.display = 'none';
                document.querySelector('.main-slider').style.display = 'none';
                document.querySelector('.wave-divider').style.display = 'none';

                const productsView = document.getElementById('productsView');
                productsView.classList.add('active');
                document.getElementById('productsViewTitle').innerText = `نتائج البحث: ${input}`;
                document.getElementById('productsViewBanner').style.display = 'none';

                const grid = document.getElementById('productsGrid');
                grid.innerHTML = results.map(p => `
                    <div class="product-card" onclick="window.open('https://wa.me/%WHATSAPP%?text=اريد شراء: ${encodeURIComponent(p.name)}', '_blank')">
                        <div class="product-img"><img src="${p.img}" alt="${p.name}"></div>
                        <div class="product-info">
                            <h4>${p.name}</h4>
                            <p style="font-size:11px;color:var(--text-muted);margin-bottom:5px;">${p.categoryName}</p>
                            <p class="product-price">${p.price} ل.س</p>
                            <button class="product-buy-btn" onclick="event.stopPropagation(); window.open('https://wa.me/%WHATSAPP%?text=اريد شراء: ${encodeURIComponent(p.name)} - ${encodeURIComponent(p.price)} ل.س', '_blank')">
                                <i class="fab fa-whatsapp"></i> اطلب الآن
                            </button>
                        </div>
                    </div>
                `).join('');
                attachCardEffects();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        }

        // إعادة تعيين البحث عند المسح
        document.getElementById('searchInput').addEventListener('input', function() {
            if (this.value === '' && document.getElementById('productsView').classList.contains('active')) {
                goBackToCategories();
                document.getElementById('productsViewBanner').style.display = '';
            }
        });

        // ===== التوجيه (Routing) عبر Hash =====
        function handleRoute() {
            const hash = window.location.hash;
            if (hash.startsWith('#category/')) {
                const catId = hash.split('/')[1];
                showCategoryProducts(catId);
            } else if (hash === '' || hash === '#home') {
                if (document.getElementById('productsView').classList.contains('active')) {
                    goBackToCategories();
                }
            }
        }
        window.addEventListener('hashchange', handleRoute);
        window.addEventListener('load', handleRoute);
    </script>
</body>
</html>
"""

    def generate_html(self):
        data = self.db.load()
        if data.get("maintenance_mode", False):
            return self.maintenance_template.replace("%MAINTENANCE_MSG%", html.escape(str(data.get("maintenance_message", "نحن نقوم بأعمال صيانة وتطوير. سنعود قريباً!"))))

        slider_text = html.escape(str(data.get("slider_text", "وجهتك الأولى للقرطاسية والمستلزمات الفنية في سوريا")))
        slider_html = "".join([
            f'<div class="swiper-slide"><img src="{img}"><div class="ad-slider-overlay"><h2>مكتبة الشاغور الحديثة</h2><div class="typing-text">{slider_text}</div></div></div>'
            for img in data.get("slider_images", [])
        ])

        cats_html_parts = []
        for c in data.get("categories", []):
            prod_count = len(c.get("products", []))
            badge_html = f'<span class="category-badge">{prod_count} منتج</span>' if prod_count > 0 else ''
            cats_html_parts.append(
                f'<div class="category-card" onclick="window.location.hash=\'category/{c["id"]}\'">'
                f'{badge_html}'
                f'<div class="category-img"><img src="{c["img"]}" alt="{html.escape(c["name"])}"></div>'
                f'<div class="category-info">'
                f'<h3>{html.escape(c["name"])}</h3>'
                f'<p>تصفح المنتجات <i class="fas fa-arrow-left"></i></p>'
                f'</div></div>'
            )
        cats_html = "".join(cats_html_parts)

        categories_json = json.dumps(data.get("categories", []), ensure_ascii=False)

        offers_html = "".join([
            f'<div class="offer-card" onclick="window.open(\'https://wa.me/{data.get("contacts",{}).get("whatsapp","")}?text=اريد الاستفسار عن: {html.escape(o["title"]}\', \'_blank\')">'
            f'<div class="offer-img"><span class="offer-badge">عرض خاص</span><img src="{o["img"]}" alt="{html.escape(o["title"])}"></div>'
            f'<div class="offer-info"><h3>{html.escape(o["title"])}</h3>'
            f'<p>{html.escape(o["desc"])}</p>'
            f'<p class="offer-price">{html.escape(o["price"])}</p></div></div>'
            for o in data.get("offers", [])
        ])

        notifications_json = json.dumps(data.get("notifications", []), ensure_ascii=False)

        c = data.get("contacts", {})

        ann_text = data.get("announcements", "مرحباً بكم | توصيل سريع | عروض حصرية")
        ann_parts = [part.strip() for part in ann_text.split("|")]
        while len(ann_parts) < 3:
            ann_parts.append("مرحباً بكم في مكتبة الشاغور")

        final_html = self.html_template
        final_html = final_html.replace("%LOGO_URL%", str(data.get("logo_url", DEFAULT_LOGO)))
        final_html = final_html.replace("%ICON_URL%", str(data.get("icon_url", DEFAULT_LOGO)))
        final_html = final_html.replace("%ANNOUNCEMENT_ITEM_1%", html.escape(ann_parts[0]))
        final_html = final_html.replace("%ANNOUNCEMENT_ITEM_2%", html.escape(ann_parts[1]))
        final_html = final_html.replace("%ANNOUNCEMENT_ITEM_3%", html.escape(ann_parts[2]))
        final_html = final_html.replace("%SLIDER_HTML%", slider_html)
        final_html = final_html.replace("%CATEGORIES_HTML%", cats_html)
        final_html = final_html.replace("%CATEGORIES_JSON%", categories_json)
        final_html = final_html.replace("%OFFERS_HTML%", offers_html)
        final_html = final_html.replace("%VIDEO_URL%", str(data.get("video_url", "")))
        final_html = final_html.replace("%WHATSAPP%", str(c.get("whatsapp", "")))
        final_html = final_html.replace("%INSTAGRAM%", str(c.get("instagram", "")))
        final_html = final_html.replace("%GMAIL%", str(c.get("gmail", "")))
        final_html = final_html.replace("%LIBRARY_ADDRESS%", html.escape(str(data.get("library_address", ""))))
        final_html = final_html.replace("%WORKING_HOURS%", html.escape(str(data.get("working_hours", ""))))
        final_html = final_html.replace("%PHONE_NUMBER%", html.escape(str(data.get("phone_number", ""))))
        final_html = final_html.replace("%NOTIFICATIONS_JSON%", notifications_json)
        final_html = final_html.replace("%ABOUT_TEXT%", html.escape(str(data.get("about_text", ""))))
        return final_html

    async def handle_index(self, request):
        try:
            html_content = await asyncio.to_thread(self.generate_html)
            return web.Response(text=html_content, content_type='text/html')
        except Exception as e:
            logging.error(f"خطأ في توليد الصفحة: {traceback.format_exc()}")
            return web.Response(text="Internal Server Error", status=500)

    async def handle_api_notifications(self, request):
        try:
            data = self.db.load()
            since = float(request.query.get("since", 0))
            notifications = [n for n in data.get("notifications", []) if float(n.get("timestamp", 0)) > since]
            return web.json_response({"notifications": notifications})
        except Exception as e:
            logging.error(f"خطأ في API الإشعارات: {e}")
            return web.json_response({"notifications": [], "error": str(e)}, status=500)

    async def handle_uploads(self, request):
        file_path = request.match_info.get('file_path', '')
        if '..' in file_path or file_path.startswith('/'):
            return web.Response(status=400)
        full_path = os.path.abspath(os.path.join(UPLOADS_DIR, file_path))
        if not full_path.startswith(os.path.abspath(UPLOADS_DIR)):
            return web.Response(status=403)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            return web.FileResponse(full_path)
        return web.Response(status=404)

    async def handle_favicon(self, request):
        return web.Response(status=204)

# ==========================================
# 3. وحدة البوت (Telegram Bot Control Panel)
# ==========================================
class TelegramBot:
    def __init__(self, db_instance):
        self.db = db_instance
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.router = Router()
        self.dp.include_router(self.router)
        self._register_handlers()

    class AdminStates(StatesGroup):
        waiting_for_maintenance_msg = State()
        waiting_for_announcement = State()
        waiting_for_about_text = State()
        waiting_for_slider_text = State()
        waiting_for_video_url = State()
        waiting_for_logo_upload = State()
        waiting_for_icon_upload = State()
        waiting_for_slider_upload = State()
        waiting_for_category_name = State()
        waiting_for_category_img = State()
        waiting_for_product_name = State()
        waiting_for_product_price = State()
        waiting_for_product_img = State()
        waiting_for_offer_title = State()
        waiting_for_offer_price = State()
        waiting_for_offer_desc = State()
        waiting_for_offer_img = State()
        waiting_for_whatsapp = State()
        waiting_for_instagram = State()
        waiting_for_gmail = State()
        waiting_for_library_address = State()
        waiting_for_working_hours = State()
        waiting_for_phone_number = State()
        waiting_for_notification_title = State()
        waiting_for_notification_message = State()

    def main_kb(self):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖼 الشعار والأيقونة", callback_data="manage_branding")],
            [InlineKeyboardButton(text="📢 الإعلان", callback_data="edit_announcement"), InlineKeyboardButton(text="ℹ️ النص التعريفي", callback_data="edit_about")],
            [InlineKeyboardButton(text="✍️ نص السلايدر", callback_data="edit_slider_text"), InlineKeyboardButton(text="🖼 السلايدر", callback_data="manage_slider")],
            [InlineKeyboardButton(text="🎬 الفيديو", callback_data="edit_video"), InlineKeyboardButton(text="📂 الأقسام", callback_data="manage_cats")],
            [InlineKeyboardButton(text="📦 المنتجات", callback_data="manage_prods"), InlineKeyboardButton(text="🏷 العروض", callback_data="manage_offers")],
            [InlineKeyboardButton(text="🏢 معلومات المكتبة", callback_data="manage_library_info")],
            [InlineKeyboardButton(text="🔔 إرسال إشعار", callback_data="send_notification"), InlineKeyboardButton(text="📋 الإشعارات", callback_data="view_notifications")],
            [InlineKeyboardButton(text="📞 التواصل", callback_data="edit_contacts")],
            [InlineKeyboardButton(text="🛠 وضع الصيانة", callback_data="manage_maint")]
        ])

    def _register_handlers(self):
        @self.router.message(CommandStart())
        async def start_cmd(message: Message, state: FSMContext):
            if message.from_user.id != ADMIN_ID:
                return await message.answer("عذراً، هذه اللوحة مخصصة للمسؤولين فقط.")
            await state.clear()
            await message.answer("مرحباً بك في لوحة التحكم الشاملة لمكتبة الشاغور الحديثة.\nاختر ما تريد تعديله:", reply_markup=self.main_kb())

        @self.router.callback_query(F.data == "back")
        async def back_cb(cb: CallbackQuery, state: FSMContext):
            await state.clear()
            await cb.message.edit_text("القائمة الرئيسية:", reply_markup=self.main_kb())

        # --- الصيانة ---
        @self.router.callback_query(F.data == "manage_maint")
        async def maint_cb(cb: CallbackQuery):
            data = self.db.load()
            status = "مفعّلة 🟢" if data.get("maintenance_mode") else "معطّلة 🔴"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="تبديل وضع الصيانة", callback_data="toggle_maint")],
                [InlineKeyboardButton(text="تعديل رسالة الصيانة", callback_data="edit_maint_msg")],
                [InlineKeyboardButton(text="🔙 رجوع", callback_data="back")]
            ])
            await cb.message.edit_text(f"إدارة الصيانة:\nالحالة الحالية: {status}", reply_markup=kb)

        @self.router.callback_query(F.data == "toggle_maint")
        async def toggle_maint_cb(cb: CallbackQuery):
            data = self.db.load()
            data["maintenance_mode"] = not data.get("maintenance_mode", False)
            self.db.save(data)
            status = "مفعّلة 🟢" if data["maintenance_mode"] else "معطّلة 🔴"
            await cb.answer(f"تم تغيير الحالة إلى: {status}", show_alert=True)

        @self.router.callback_query(F.data == "edit_maint_msg")
        async def edit_maint_msg_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل رسالة الصيانة الجديدة:")
            await state.set_state(self.AdminStates.waiting_for_maintenance_msg)

        @self.router.message(self.AdminStates.waiting_for_maintenance_msg)
        async def process_maint_msg(message: Message, state: FSMContext):
            data = self.db.load()
            data["maintenance_message"] = message.text
            self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث رسالة الصيانة!", reply_markup=self.main_kb())

        # --- الشعار والأيقونة ---
        @self.router.callback_query(F.data == "manage_branding")
        async def manage_branding_cb(cb: CallbackQuery):
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="رفع الشعار", callback_data="upload_logo")],
                [InlineKeyboardButton(text="رفع الأيقونة", callback_data="upload_icon")],
                [InlineKeyboardButton(text="🔙 رجوع", callback_data="back")]
            ])
            await cb.message.edit_text("إدارة هوية الموقع:", reply_markup=kb)

        async def upload_photo_handler(message: Message, state: FSMContext, key):
            if not message.photo:
                await message.answer("الرجاء إرسال صورة حقيقية.")
                return
            file_id = message.photo[-1].file_id
            try:
                file = await self.bot.get_file(file_id)
                ext = file.file_path.split('.')[-1]
                file_name = f"{key}_{uuid.uuid4().hex}.{ext}"
                file_path = os.path.join(UPLOADS_DIR, file_name)
                os.makedirs(UPLOADS_DIR, exist_ok=True)
                await self.bot.download_file(file.file_path, file_path)
                data = self.db.load()
                data[key] = f"/uploads/{file_name}"
                self.db.save(data)
                await state.clear()
                await message.answer(f"تم تحديث {key} بنجاح!", reply_markup=self.main_kb())
            except Exception as e:
                await state.clear()
                await message.answer(f"حدث خطأ أثناء رفع الصورة: {e}", reply_markup=self.main_kb())

        @self.router.callback_query(F.data == "upload_logo")
        async def upload_logo_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل صورة الشعار الجديد:")
            await state.set_state(self.AdminStates.waiting_for_logo_upload)

        @self.router.message(self.AdminStates.waiting_for_logo_upload, F.photo)
        async def proc_logo(message: Message, state: FSMContext):
            await upload_photo_handler(message, state, "logo_url")

        @self.router.callback_query(F.data == "upload_icon")
        async def upload_icon_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل صورة الأيقونة الجديدة:")
            await state.set_state(self.AdminStates.waiting_for_icon_upload)

        @self.router.message(self.AdminStates.waiting_for_icon_upload, F.photo)
        async def proc_icon(message: Message, state: FSMContext):
            await upload_photo_handler(message, state, "icon_url")

        # --- الإعلان ---
        @self.router.callback_query(F.data == "edit_announcement")
        async def edit_ann_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل نص الإعلان العلوي الجديد (يمكنك استخدام | كفاصل بين الجمل):")
            await state.set_state(self.AdminStates.waiting_for_announcement)

        @self.router.message(self.AdminStates.waiting_for_announcement)
        async def proc_ann(message: Message, state: FSMContext):
            data = self.db.load()
            data["announcements"] = message.text
            self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث الإعلان! 📢", reply_markup=self.main_kb())

        # --- النص التعريفي ---
        @self.router.callback_query(F.data == "edit_about")
        async def edit_about_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل النص التعريفي الجديد (About):")
            await state.set_state(self.AdminStates.waiting_for_about_text)

        @self.router.message(self.AdminStates.waiting_for_about_text)
        async def proc_about(message: Message, state: FSMContext):
            data = self.db.load()
            data["about_text"] = message.text
            self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث النص التعريفي! ℹ️", reply_markup=self.main_kb())

        # --- نص السلايدر ---
        @self.router.callback_query(F.data == "edit_slider_text")
        async def edit_slider_text_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل النص الذي سيظهر في السلايدر (تأثير الكتابة):")
            await state.set_state(self.AdminStates.waiting_for_slider_text)

        @self.router.message(self.AdminStates.waiting_for_slider_text)
        async def proc_slider_text(message: Message, state: FSMContext):
            data = self.db.load()
            data["slider_text"] = message.text
            self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث نص السلايدر! ✍️", reply_markup=self.main_kb())

        # --- الفيديو ---
        @self.router.callback_query(F.data == "edit_video")
        async def edit_vid_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل رابط الفيديو الجديد (MP4):")
            await state.set_state(self.AdminStates.waiting_for_video_url)

        @self.router.message(self.AdminStates.waiting_for_video_url)
        async def proc_vid(message: Message, state: FSMContext):
            data = self.db.load()
            data["video_url"] = message.text
            self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث الفيديو! 🎬", reply_markup=self.main_kb())

        # --- السلايدر ---
        @self.router.callback_query(F.data == "manage_slider")
        async def man_slider_cb(cb: CallbackQuery):
            data = self.db.load()
            kb = [[InlineKeyboardButton(text="➕ إضافة صورة", callback_data="add_slider")]]
            for i, img in enumerate(data.get("slider_images", [])):
                kb.append([InlineKeyboardButton(text=f"🗑 حذف صورة {i+1}", callback_data=f"del_slider_{i}")])
            kb.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back")])
            await cb.message.edit_text("إدارة صور السلايدر:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

        @self.router.callback_query(F.data == "add_slider")
        async def add_slider_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل صورة السلايدر الجديدة:")
            await state.set_state(self.AdminStates.waiting_for_slider_upload)

        @self.router.message(self.AdminStates.waiting_for_slider_upload, F.photo)
        async def proc_slider_img(message: Message, state: FSMContext):
            try:
                file_id = message.photo[-1].file_id
                file = await self.bot.get_file(file_id)
                file_name = f"slider_{uuid.uuid4().hex}.jpg"
                file_path = os.path.join(UPLOADS_DIR, file_name)
                os.makedirs(UPLOADS_DIR, exist_ok=True)
                await self.bot.download_file(file.file_path, file_path)
                data = self.db.load()
                if "slider_images" not in data:
                    data["slider_images"] = []
                data["slider_images"].append(f"/uploads/{file_name}")
                self.db.save(data)
                await state.clear()
                await message.answer("تمت إضافة الصورة! 🖼", reply_markup=self.main_kb())
            except Exception as e:
                await state.clear()
                await message.answer(f"حدث خطأ أثناء حفظ الصورة: {e}", reply_markup=self.main_kb())

        @self.router.callback_query(F.data.startswith("del_slider_"))
        async def del_slider_cb(cb: CallbackQuery):
            index = int(cb.data.split("_")[2])
            data = self.db.load()
            if data.get("slider_images") and len(data["slider_images"]) > index:
                data["slider_images"].pop(index)
                self.db.save(data)
                await cb.answer("تم الحذف", show_alert=True)
                await man_slider_cb(cb)

        # --- الأقسام ---
        @self.router.callback_query(F.data == "manage_cats")
        async def man_cats_cb(cb: CallbackQuery):
            data = self.db.load()
            kb = [[InlineKeyboardButton(text="➕ إضافة قسم", callback_data="add_cat")]]
            for cat in data.get("categories", []):
                kb.append([InlineKeyboardButton(text=f"🗑 حذف: {cat['name']}", callback_data=f"del_cat_{cat['id']}")])
            kb.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back")])
            await cb.message.edit_text("إدارة الأقسام:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

        @self.router.callback_query(F.data == "add_cat")
        async def add_cat_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل اسم القسم الجديد:")
            await state.set_state(self.AdminStates.waiting_for_category_name)

        @self.router.message(self.AdminStates.waiting_for_category_name)
        async def proc_cat_name(message: Message, state: FSMContext):
            await state.update_data(name=message.text)
            await message.answer("أرسل صورة القسم:")
            await state.set_state(self.AdminStates.waiting_for_category_img)

        @self.router.message(self.AdminStates.waiting_for_category_img, F.photo)
        async def proc_cat_img(message: Message, state: FSMContext):
            try:
                file_id = message.photo[-1].file_id
                file = await self.bot.get_file(file_id)
                file_name = f"cat_{uuid.uuid4().hex}.jpg"
                file_path = os.path.join(UPLOADS_DIR, file_name)
                os.makedirs(UPLOADS_DIR, exist_ok=True)
                await self.bot.download_file(file.file_path, file_path)
                data = self.db.load()
                cat_data = await state.get_data()
                if "categories" not in data:
                    data["categories"] = []
                data["categories"].append({
                    "id": uuid.uuid4().hex,
                    "name": cat_data["name"],
                    "img": f"/uploads/{file_name}",
                    "products": []
                })
                self.db.save(data)
                await state.clear()
                await message.answer("تمت إضافة القسم! 📂", reply_markup=self.main_kb())
            except Exception as e:
                await state.clear()
                await message.answer(f"حدث خطأ أثناء حفظ صورة القسم: {e}", reply_markup=self.main_kb())

        @self.router.callback_query(F.data.startswith("del_cat_"))
        async def del_cat_cb(cb: CallbackQuery):
            cat_id = cb.data.split("_")[2]
            data = self.db.load()
            data["categories"] = [c for c in data.get("categories", []) if c["id"] != cat_id]
            self.db.save(data)
            await cb.answer("تم حذف القسم", show_alert=True)
            await man_cats_cb(cb)

        # --- المنتجات ---
        @self.router.callback_query(F.data == "manage_prods")
        async def man_prods_cb(cb: CallbackQuery):
            data = self.db.load()
            kb = []
            for cat in data.get("categories", []):
                kb.append([InlineKeyboardButton(text=f"منتجات: {cat['name']}", callback_data=f"list_prods_{cat['id']}")])
            kb.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back")])
            await cb.message.edit_text("اختر القسم لإدارة منتجاته:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

        @self.router.callback_query(F.data.startswith("list_prods_"))
        async def list_prods_cb(cb: CallbackQuery):
            cat_id = cb.data.split("_")[2]
            data = self.db.load()
            cat = next((c for c in data.get("categories", []) if c["id"] == cat_id), None)
            if not cat:
                return await cb.answer("القسم غير موجود")
            kb = [[InlineKeyboardButton(text="➕ إضافة منتج", callback_data=f"add_prod_{cat_id}")]]
            for prod in cat.get("products", []):
                kb.append([InlineKeyboardButton(text=f"🗑 حذف: {prod['name']}", callback_data=f"del_prod_{prod['id']}")])
            kb.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="manage_prods")])
            await cb.message.edit_text(f"منتجات قسم: {cat['name']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

        @self.router.callback_query(F.data.startswith("add_prod_"))
        async def add_prod_cb(cb: CallbackQuery, state: FSMContext):
            cat_id = cb.data.split("_")[2]
            await state.set_data({"cat_id": cat_id})
            await cb.message.answer("أرسل اسم المنتج:")
            await state.set_state(self.AdminStates.waiting_for_product_name)

        @self.router.message(self.AdminStates.waiting_for_product_name)
        async def proc_prod_name(message: Message, state: FSMContext):
            await state.update_data(name=message.text)
            await message.answer("أرسل سعر المنتج (مثال: 15000):")
            await state.set_state(self.AdminStates.waiting_for_product_price)

        @self.router.message(self.AdminStates.waiting_for_product_price)
        async def proc_prod_price(message: Message, state: FSMContext):
            await state.update_data(price=message.text)
            await message.answer("أرسل صورة المنتج:")
            await state.set_state(self.AdminStates.waiting_for_product_img)

        @self.router.message(self.AdminStates.waiting_for_product_img, F.photo)
        async def proc_prod_img(message: Message, state: FSMContext):
            try:
                file_id = message.photo[-1].file_id
                file = await self.bot.get_file(file_id)
                file_name = f"prod_{uuid.uuid4().hex}.jpg"
                file_path = os.path.join(UPLOADS_DIR, file_name)
                os.makedirs(UPLOADS_DIR, exist_ok=True)
                await self.bot.download_file(file.file_path, file_path)
                data = self.db.load()
                prod_data = await state.get_data()
                cat_id = prod_data["cat_id"]
                for cat in data.get("categories", []):
                    if cat["id"] == cat_id:
                        cat.setdefault("products", []).append({
                            "id": uuid.uuid4().hex,
                            "name": prod_data["name"],
                            "price": prod_data["price"],
                            "img": f"/uploads/{file_name}"
                        })
                        break
                self.db.save(data)
                await state.clear()
                await message.answer("تمت إضافة المنتج! 📦", reply_markup=self.main_kb())
            except Exception as e:
                await state.clear()
                await message.answer(f"حدث خطأ أثناء حفظ صورة المنتج: {e}", reply_markup=self.main_kb())

        @self.router.callback_query(F.data.startswith("del_prod_"))
        async def del_prod_cb(cb: CallbackQuery):
            prod_id = cb.data.split("_")[2]
            data = self.db.load()
            for cat in data.get("categories", []):
                cat["products"] = [p for p in cat.get("products", []) if p["id"] != prod_id]
            self.db.save(data)
            await cb.answer("تم حذف المنتج", show_alert=True)

        # --- العروض ---
        @self.router.callback_query(F.data == "manage_offers")
        async def man_offers_cb(cb: CallbackQuery):
            data = self.db.load()
            kb = [[InlineKeyboardButton(text="➕ إضافة عرض", callback_data="add_offer")]]
            for off in data.get("offers", []):
                kb.append([InlineKeyboardButton(text=f"🗑 حذف: {off['title']}", callback_data=f"del_offer_{off['id']}")])
            kb.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back")])
            await cb.message.edit_text("إدارة العروض:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

        @self.router.callback_query(F.data == "add_offer")
        async def add_offer_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل عنوان العرض:")
            await state.set_state(self.AdminStates.waiting_for_offer_title)

        @self.router.message(self.AdminStates.waiting_for_offer_title)
        async def proc_offer_title(message: Message, state: FSMContext):
            await state.update_data(title=message.text)
            await message.answer("أرسل سعر العرض (مثال: 10,000 ل.س):")
            await state.set_state(self.AdminStates.waiting_for_offer_price)

        @self.router.message(self.AdminStates.waiting_for_offer_price)
        async def proc_offer_price(message: Message, state: FSMContext):
            await state.update_data(price=message.text)
            await message.answer("أرسل وصف العرض:")
            await state.set_state(self.AdminStates.waiting_for_offer_desc)

        @self.router.message(self.AdminStates.waiting_for_offer_desc)
        async def proc_offer_desc(message: Message, state: FSMContext):
            await state.update_data(desc=message.text)
            await message.answer("أرسل صورة العرض:")
            await state.set_state(self.AdminStates.waiting_for_offer_img)

        @self.router.message(self.AdminStates.waiting_for_offer_img, F.photo)
        async def proc_offer_img(message: Message, state: FSMContext):
            try:
                file_id = message.photo[-1].file_id
                file = await self.bot.get_file(file_id)
                file_name = f"offer_{uuid.uuid4().hex}.jpg"
                file_path = os.path.join(UPLOADS_DIR, file_name)
                os.makedirs(UPLOADS_DIR, exist_ok=True)
                await self.bot.download_file(file.file_path, file_path)
                data = self.db.load()
                off_data = await state.get_data()
                if "offers" not in data:
                    data["offers"] = []
                data["offers"].append({
                    "id": uuid.uuid4().hex,
                    "title": off_data["title"],
                    "price": off_data["price"],
                    "desc": off_data["desc"],
                    "img": f"/uploads/{file_name}"
                })
                self.db.save(data)
                await state.clear()
                await message.answer("تمت إضافة العرض! 🏷", reply_markup=self.main_kb())
            except Exception as e:
                await state.clear()
                await message.answer(f"حدث خطأ أثناء حفظ صورة العرض: {e}", reply_markup=self.main_kb())

        @self.router.callback_query(F.data.startswith("del_offer_"))
        async def del_offer_cb(cb: CallbackQuery):
            off_id = cb.data.split("_")[2]
            data = self.db.load()
            data["offers"] = [o for o in data.get("offers", []) if o["id"] != off_id]
            self.db.save(data)
            await cb.answer("تم حذف العرض", show_alert=True)
            await man_offers_cb(cb)

        # --- معلومات المكتبة (عنوان، ساعات، هاتف) ---
        @self.router.callback_query(F.data == "manage_library_info")
        async def manage_library_info_cb(cb: CallbackQuery):
            data = self.db.load()
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📍 العنوان", callback_data="edit_address")],
                [InlineKeyboardButton(text="🕐 ساعات الدوام", callback_data="edit_hours")],
                [InlineKeyboardButton(text="📞 رقم الهاتف", callback_data="edit_phone")],
                [InlineKeyboardButton(text="🔙 رجوع", callback_data="back")]
            ])
            await cb.message.edit_text(
                f"إدارة معلومات المكتبة:\n\n"
                f"📍 العنوان: {data.get('library_address', 'غير محدد')}\n"
                f"🕐 الدوام: {data.get('working_hours', 'غير محدد')}\n"
                f"📞 الهاتف: {data.get('phone_number', 'غير محدد')}",
                reply_markup=kb
            )

        @self.router.callback_query(F.data == "edit_address")
        async def edit_address_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل عنوان المكتبة الجديد:")
            await state.set_state(self.AdminStates.waiting_for_library_address)

        @self.router.message(self.AdminStates.waiting_for_library_address)
        async def proc_address(message: Message, state: FSMContext):
            data = self.db.load()
            data["library_address"] = message.text
            self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث العنوان! 📍", reply_markup=self.main_kb())

        @self.router.callback_query(F.data == "edit_hours")
        async def edit_hours_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل ساعات الدوام الجديدة:")
            await state.set_state(self.AdminStates.waiting_for_working_hours)

        @self.router.message(self.AdminStates.waiting_for_working_hours)
        async def proc_hours(message: Message, state: FSMContext):
            data = self.db.load()
            data["working_hours"] = message.text
            self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث ساعات الدوام! 🕐", reply_markup=self.main_kb())

        @self.router.callback_query(F.data == "edit_phone")
        async def edit_phone_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل رقم الهاتف الجديد:")
            await state.set_state(self.AdminStates.waiting_for_phone_number)

        @self.router.message(self.AdminStates.waiting_for_phone_number)
        async def proc_phone(message: Message, state: FSMContext):
            data = self.db.load()
            data["phone_number"] = message.text
            self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث رقم الهاتف! 📞", reply_markup=self.main_kb())

        # --- الإشعارات ---
        @self.router.callback_query(F.data == "send_notification")
        async def send_notif_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل عنوان الإشعار:")
            await state.set_state(self.AdminStates.waiting_for_notification_title)

        @self.router.message(self.AdminStates.waiting_for_notification_title)
        async def proc_notif_title(message: Message, state: FSMContext):
            await state.update_data(title=message.text)
            await message.answer("أرسل نص الإشعار:")
            await state.set_state(self.AdminStates.waiting_for_notification_message)

        @self.router.message(self.AdminStates.waiting_for_notification_message)
        async def proc_notif_message(message: Message, state: FSMContext):
            try:
                data = self.db.load()
                notif_data = await state.get_data()
                if "notifications" not in data:
                    data["notifications"] = []
                data["notifications"].append({
                    "id": uuid.uuid4().hex,
                    "title": notif_data["title"],
                    "message": message.text,
                    "type": "info",
                    "timestamp": time.time()
                })
                # الاحتفاظ بآخر 50 إشعار فقط
                if len(data["notifications"]) > 50:
                    data["notifications"] = data["notifications"][-50:]
                self.db.save(data)
                await state.clear()
                await message.answer("تم إرسال الإشعار بنجاح! سيظهر للمستخدمين على الموقع. 🔔", reply_markup=self.main_kb())
            except Exception as e:
                await state.clear()
                await message.answer(f"حدث خطأ: {e}", reply_markup=self.main_kb())

        @self.router.callback_query(F.data == "view_notifications")
        async def view_notifs_cb(cb: CallbackQuery):
            data = self.db.load()
            notifs = data.get("notifications", [])
            kb = [[InlineKeyboardButton(text="🔔 إرسال إشعار جديد", callback_data="send_notification")]]
            if notifs:
                kb.append([InlineKeyboardButton(text="🗑 حذف جميع الإشعارات", callback_data="del_all_notifs")])
                for n in reversed(notifs[-10:]):
                    title_short = n.get("title", "إشعار")[:30]
                    kb.append([InlineKeyboardButton(text=f"🗑 {title_short}", callback_data=f"del_notif_{n['id']}")])
            kb.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back")])
            await cb.message.edit_text(
                f"الإشعارات ({len(notifs)} إشعار):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
            )

        @self.router.callback_query(F.data.startswith("del_notif_"))
        async def del_notif_cb(cb: CallbackQuery):
            notif_id = cb.data.split("_")[2]
            data = self.db.load()
            data["notifications"] = [n for n in data.get("notifications", []) if n["id"] != notif_id]
            self.db.save(data)
            await cb.answer("تم الحذف", show_alert=True)
            await view_notifs_cb(cb)

        @self.router.callback_query(F.data == "del_all_notifs")
        async def del_all_notifs_cb(cb: CallbackQuery):
            data = self.db.load()
            data["notifications"] = []
            self.db.save(data)
            await cb.answer("تم حذف جميع الإشعارات", show_alert=True)
            await view_notifs_cb(cb)

        # --- التواصل ---
        @self.router.callback_query(F.data == "edit_contacts")
        async def edit_contacts_cb(cb: CallbackQuery):
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="واتساب", callback_data="con_wa")],
                [InlineKeyboardButton(text="إنستغرام", callback_data="con_ig"), InlineKeyboardButton(text="جيميل", callback_data="con_gm")],
                [InlineKeyboardButton(text="🔙 رجوع", callback_data="back")]
            ])
            await cb.message.edit_text("اختر منصة لتعديلها:", reply_markup=kb)

        @self.router.callback_query(F.data.in_(["con_wa", "con_ig", "con_gm"]))
        async def edit_con_cb(cb: CallbackQuery, state: FSMContext):
            state_map = {
                "con_wa": (self.AdminStates.waiting_for_whatsapp, "واتساب"),
                "con_ig": (self.AdminStates.waiting_for_instagram, "إنستغرام"),
                "con_gm": (self.AdminStates.waiting_for_gmail, "جيميل")
            }
            new_state, name = state_map[cb.data]
            await state.set_state(new_state)
            await cb.message.answer(f"أرسل {name} الجديد:")

        async def process_contact(message: Message, state: FSMContext, key):
            data = self.db.load()
            if "contacts" not in data:
                data["contacts"] = {}
            data["contacts"][key] = message.text
            self.db.save(data)
            await state.clear()
            await message.answer("تم التحديث! 📞", reply_markup=self.main_kb())

        @self.router.message(self.AdminStates.waiting_for_whatsapp)
        async def proc_wa(message: Message, state: FSMContext):
            await process_contact(message, state, "whatsapp")

        @self.router.message(self.AdminStates.waiting_for_instagram)
        async def proc_ig(message: Message, state: FSMContext):
            await process_contact(message, state, "instagram")

        @self.router.message(self.AdminStates.waiting_for_gmail)
        async def proc_gm(message: Message, state: FSMContext):
            await process_contact(message, state, "gmail")

    async def run_background(self):
        while True:
            try:
                await self.bot.delete_webhook(drop_pending_updates=True)
                logging.info("🤖 البوت يعمل بشكل سليم ويراقب الرسائل...")
                await self.dp.start_polling(self.bot, handle_signals=False)
                logging.info("Polling stopped normally. Restarting in 15 seconds...")
                await asyncio.sleep(15)
            except Exception as e:
                logging.error(f"❌ خطأ في تشغيل البوت: {e}")
                logging.info("سيتم إعادة محاولة تشغيل البوت بعد 60 ثانية...")
                await asyncio.sleep(60)

# ==========================================
# 4. المنفذ الرئيسي (Main Executor)
# ==========================================
async def main():
    logging.info("🚀 بدء تشغيل التطبيق...")
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    web_app_instance = WebServer(db)
    bot_instance = TelegramBot(db)

    app = web.Application()
    app.router.add_get('/', web_app_instance.handle_index)
    app.router.add_get('/favicon.ico', web_app_instance.handle_favicon)
    app.router.add_get('/api/notifications', web_app_instance.handle_api_notifications)
    app.router.add_get('/uploads/{file_path}', web_app_instance.handle_uploads)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)

    try:
        await site.start()
        logging.info(f"✅ خادم الويب يستمع فعلياً على 0.0.0.0:{port}")
    except Exception as e:
        logging.critical(f"❌ فشل تشغيل خادم الويب: {e}")
        return

    asyncio.create_task(bot_instance.run_background())

    try:
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logging.critical(f"❌ خطأ قاتل في حلقة الأحداث: {e}")
    finally:
        await runner.cleanup()
        await bot_instance.bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("⛔ تم إيقاف التطبيق")
    except Exception:
        logging.critical(traceback.format_exc())
