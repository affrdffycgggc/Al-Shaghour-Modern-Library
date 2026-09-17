import os
import sys
import json
import asyncio
import uuid
import logging
import traceback
import threading
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
BOT_TOKEN = "8395651089:AAEfbnpVCy0AJL2pI1X57Zlv5cP7CySOo5s"  # ضع توكن البوت هنا
ADMIN_ID = 8410208108  # ضع معرفك الرقمي هنا
DB_FILE = "data.json"
UPLOADS_DIR = "uploads"

# قفل لمنع التداخل أثناء القراءة والكتابة
_data_lock = threading.Lock()

try:
    if not os.path.exists(UPLOADS_DIR):
        os.makedirs(UPLOADS_DIR)
except Exception as e:
    logging.warning(f"تعذر إنشاء مجلد الرفعات: {e} - main.py:37")

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
                        return self._memory_db
                except Exception:
                    logging.warning("ملف البيانات تالف. سيتم إنشاء بيانات افتراضية. - main.py:59")
            
            self._memory_db = self._default_data()
            self.save(self._memory_db)
            return self._memory_db

    def save(self, data):
        with _data_lock:
            self._memory_db = data
            try:
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception:
                logging.warning("تعذر الكتابة على القرص. سيتم استخدام الذاكرة المؤقتة. - main.py:72")

    def _default_data(self):
        return {
            "maintenance_mode": False,
            "maintenance_message": "نحن حالياً نقوم بأعمال تطوير وصيانة لتحسين تجربتكم. سنعود قريباً بأفضل مما كنا!",
            "announcements": "مرحباً بكم في مكتبة الشاغور الحديثة 📚 | توصيل سريع لجميع المحافظات 🚚 | عروض حصرية على القرطاسية 🎨",
            "about_text": "مكتبة الشاغور الحديثة، وجهتك الأولى للقرطاسية والمستلزمات الفنية والمكتبية في سوريا. نقدم منتجات بجودة عالية وأسعار منافسة.",
            "slider_text": "وجهتك الأولى للقرطاسية والمستلزمات الفنية في سوريا",
            "logo_url": DEFAULT_LOGO,
            "icon_url": DEFAULT_LOGO,
            "slider_images": [
                "https://images.unsplash.com/photo-1507842217343-583bb7270b0f?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80",
                "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80"
            ],
            "video_url": "https://cdn.coverr.co/videos/cover2-coverr-co-writing-on-a-notebook-1080p.mp4",
            "categories": [
                {"id": "cat1", "name": "قرطاسية مدرسية", "img": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80", "products": [{"id": "p1", "name": "دفتر سلك", "price": "15,000", "img": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80"}]},
                {"id": "cat2", "name": "أدوات مكتبية", "img": "https://images.unsplash.com/photo-1497032628192-86f99bcd76bc?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80", "products": []},
                {"id": "cat3", "name": "أدوات فنية", "img": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80", "products": []},
                {"id": "cat4", "name": "كتب ودفاتر", "img": "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80", "products": []},
                {"id": "cat5", "name": "اكسسوارات هواتف", "img": "https://images.unsplash.com/photo-1572569511254-d8f925fe2cbb?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80", "products": []}
            ],
            "offers": [
                {"id": "off1", "title": "خصم 20% على الأقلام", "price": "10,000 ل.س", "desc": "عرض لفترة محدودة على جميع أنواع الأقلام", "img": "https://images.unsplash.com/photo-1583485088034-697b5bc36b92?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80"}
            ],
            "contacts": {"whatsapp": "963935123456", "instagram": "shaghour_library", "gmail": "info@shaghour.sy"}
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
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>صيانة | مكتبة الشاغور الحديثة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@200;400;600;800&family=Amiri:wght@400;700&display=swap" rel="stylesheet">
    <style>body{margin:0;background:#0F0F0F;color:#C9A961;font-family:'Cairo',sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;text-align:center;overflow:hidden}.container{z-index:2;padding:20px}.gear{width:100px;height:100px;margin:0 auto 30px;border:3px solid #C9A961;border-radius:50%;border-top-color:transparent;animation:spin 2s linear infinite;display:flex;justify-content:center;align-items:center;box-shadow:0 0 30px rgba(201,169,97,0.3)}.gear svg{width:50px;height:50px;fill:#C9A961;animation:spin-rev 4s linear infinite}@keyframes spin{100%{transform:rotate(360deg)}}@keyframes spin-rev{100%{transform:rotate(-360deg)}}h1{font-family:'Amiri',serif;font-size:48px;margin-bottom:20px;text-shadow:0 0 20px rgba(201,169,97,0.5)}p{font-size:18px;max-width:600px;margin:0 auto;line-height:1.6;color:#8B8B8B}.bg-particles{position:absolute;top:0;left:0;width:100%;height:100%;z-index:1;pointer-events:none}</style>
</head>
<body>
    <canvas class="bg-particles" id="bg"></canvas>
    <div class="container"><div class="gear"><svg viewBox="0 0 24 24"><path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.91,5.35C9.32,5.59,8.79,5.92,8.29,6.29L5.9,5.33c-0.22-0.08-0.47,0-0.59,0.22L3.4,8.87 c-0.12,0.21-0.08,0.47,0.12,0.61l2.03,1.58C5.5,11.36,5.48,11.68,5.48,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.04,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/></svg></div><h1>الموقع قيد الصيانة</h1><p>%MAINTENANCE_MSG%</p></div>
    <script>const c=document.getElementById('bg');const ctx=c.getContext('2d');c.width=innerWidth;c.height=innerHeight;let p=[];class P{constructor(){this.x=Math.random()*c.width;this.y=Math.random()*c.height;this.s=Math.random()*2+1;this.sx=Math.random()*0.5-0.25;this.sy=Math.random()*0.5-0.25;}u(){this.x+=this.sx;this.y+=this.sy;if(this.x<0||this.x>c.width)this.sx*=-1;if(this.y<0||this.y>c.height)this.sy*=-1;}d(){ctx.fillStyle='rgba(201,169,97,0.5)';ctx.beginPath();ctx.arc(this.x,this.y,this.s,0,Math.PI*2);ctx.fill();}}for(let i=0;i<30;i++)p.push(new P());function anim(){ctx.clearRect(0,0,c.width,c.height);p.forEach(e=>{e.u();e.d();});requestAnimationFrame(anim);}anim();</script>
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
    <title>مكتبة الشاغور الحديثة | Al-Shaghour Modern Library</title>
    <link rel="icon" href="%ICON_URL%" type="image/x-icon">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@200;400;600;800&family=Amiri:wght@400;700&family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@10/swiper-bundle.min.css">
    <style>
        :root {
            --primary-gold: #C9A961; --primary-gold-light: #E5C77C; --primary-gold-dark: #9B7D3F;
            --dark-bg: #0F0F0F; --dark-bg-2: #1A1A1A;
            --text-light: #F5F1E8; --text-muted: #8B8B8B; --border-color: rgba(201, 169, 97, 0.2);
            --shadow-gold: 0 10px 40px rgba(201, 169, 97, 0.15); --glass-bg: rgba(26, 26, 26, 0.7);
            --transition-smooth: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }
        [data-theme="light"] { 
            --dark-bg: #F8F9FA; --dark-bg-2: #FFFFFF; --text-light: #1A1A1A; --text-muted: #555555; 
            --border-color: rgba(0,0,0,0.1); --glass-bg: rgba(255,255,255,0.85); --shadow-gold: 0 10px 40px rgba(0,0,0,0.1);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        body { background: var(--dark-bg); color: var(--text-light); font-family: 'Cairo', sans-serif; transition: background 0.5s, color 0.5s; overflow-x: hidden; }
        body.no-cursor { cursor: none; }
        
        .cursor-dot { position: fixed; width: 6px; height: 6px; background: var(--primary-gold); border-radius: 50%; pointer-events: none; z-index: 9999; transition: transform 0.1s; mix-blend-mode: difference; opacity: 0; }
        .cursor-outline { position: fixed; width: 30px; height: 30px; border: 1px solid var(--primary-gold); border-radius: 50%; pointer-events: none; z-index: 9998; transition: all 0.2s; opacity: 0; }
        
        #particles-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none; }
        .scroll-progress { position: fixed; top: 0; left: 0; width: 0%; height: 3px; background: linear-gradient(90deg, var(--primary-gold-dark), var(--primary-gold-light)); z-index: 1002; transition: width 0.1s; }
        
        /* ===== واجهة التحميل المتطورة (Developer / Cyberpunk Style) ===== */
        .dev-loader { position: fixed; inset: 0; background: #050505; z-index: 10000; display: flex; justify-content: center; align-items: center; flex-direction: column; transition: opacity 0.8s ease, visibility 0.8s ease; overflow: hidden; }
        .dev-loader.hidden { opacity: 0; visibility: hidden; }
        .dev-loader::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(transparent 90%, rgba(201, 169, 97, 0.05) 80%); background-size: 100% 4px; animation: scanlines 8s linear infinite; pointer-events: none; }
        @keyframes scanlines { 0% { background-position: 0 0; } 100% { background-position: 0 100%; } }
        
        .dev-loader-box { width: 90%; max-width: 500px; background: rgba(10, 10, 10, 0.9); border: 1px solid var(--primary-gold-dark); border-radius: 12px; box-shadow: 0 0 40px rgba(201, 169, 97, 0.15); overflow: hidden; backdrop-filter: blur(10px); position: relative; }
        .dev-loader-header { background: rgba(201, 169, 97, 0.1); padding: 8px 15px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--border-color); }
        .dev-dots { display: flex; gap: 6px; }
        .dev-dots span { width: 10px; height: 10px; border-radius: 50%; background: var(--primary-gold-dark); opacity: 0.7; }
        .dev-loader-title { font-family: 'Share Tech Mono', monospace; color: var(--primary-gold); font-size: 12px; margin-right: auto; letter-spacing: 1px; }
        
        .dev-loader-content { padding: 25px; font-family: 'Share Tech Mono', monospace; }
        .dev-log { color: var(--primary-gold-light); font-size: 13px; margin-bottom: 6px; display: flex; align-items: center; gap: 10px; opacity: 0; transform: translateY(10px); animation: logAppear 0.4s forwards; }
        .dev-log::before { content: '>'; color: var(--primary-gold); }
        .dev-log.success::before { content: '✓'; color: #2ecc71; }
        .dev-log.error::before { content: '✗'; color: #e74c3c; }
        @keyframes logAppear { to { opacity: 1; transform: translateY(0); } }
        
        .dev-progress-wrap { margin-top: 20px; border-top: 1px dashed var(--border-color); padding-top: 15px; }
        .dev-progress-bar { width: 100%; height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; position: relative; }
        .dev-progress-fill { height: 100%; width: 0%; background: linear-gradient(90deg, transparent, var(--primary-gold), var(--primary-gold-light)); box-shadow: 0 0 15px var(--primary-gold); transition: width 0.2s ease-out; }
        .dev-percent { text-align: right; color: #fff; font-size: 12px; margin-top: 5px; display: block; }
        
        /* ===== شريط الإعلان المتطور (Modern Neon Marquee) ===== */
        .top-bar { position: fixed; top: 0; left: 0; width: 100%; z-index: 1001; background: linear-gradient(90deg, #0f0f0f, #1a1a1a, #0f0f0f); border-bottom: 1px solid var(--border-color); box-shadow: 0 2px 15px rgba(0,0,0,0.5); overflow: hidden; height: 35px; display: flex; align-items: center; }
        .top-bar::before, .top-bar::after { content: ''; position: absolute; top: 0; width: 80px; height: 100%; z-index: 2; pointer-events: none; }
        .top-bar::before { left: 0; background: linear-gradient(to right, #0f0f0f, transparent); }
        .top-bar::after { right: 0; background: linear-gradient(to left, #0f0f0f, transparent); }
        [data-theme="light"] .top-bar { background: linear-gradient(90deg, #F8F9FA, #FFFFFF, #F8F9FA); }
        [data-theme="light"] .top-bar::before { background: linear-gradient(to right, #F8F9FA, transparent); }
        [data-theme="light"] .top-bar::after { background: linear-gradient(to left, #F8F9FA, transparent); }
        
        .marquee-wrapper { display: flex; width: max-content; animation: modern-marquee 30s linear infinite; }
        .marquee-content { display: flex; align-items: center; gap: 40px; padding: 0 20px; }
        .marquee-item { color: var(--primary-gold-light); font-size: clamp(11px, 2vw, 13px); font-weight: 600; font-family: 'Cairo', sans-serif; text-shadow: 0 0 8px rgba(201, 169, 97, 0.6); display: flex; align-items: center; gap: 40px; white-space: nowrap; }
        .marquee-item .icon { color: var(--primary-gold); font-size: 8px; animation: pulse-icon 1.5s infinite; }
        @keyframes modern-marquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        @keyframes pulse-icon { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        
        /* ===== شريط التنقل والأزرار ===== */
        .navbar { position: fixed; top: 35px; left: 0; width: 100%; z-index: 1000; background: var(--glass-bg); backdrop-filter: blur(15px); border-bottom: 1px solid var(--border-color); transition: top 0.4s; }
        .navbar.hide-nav { top: -65px; }
        .nav-container { max-width: 1400px; margin: 0 auto; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; }
        .nav-logo { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .nav-logo img { width: 40px; height: 40px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); transition: transform 0.3s; }
        .nav-logo:hover img { transform: scale(1.1) rotate(5deg); }
        .logo-text h1 { font-family: 'Amiri', serif; font-size: clamp(16px, 3vw, 22px); color: var(--primary-gold); line-height: 1.2; }
        .logo-text p { font-size: 9px; color: var(--text-muted); letter-spacing: 1px; }
        .nav-actions { display: flex; gap: 10px; align-items: center; }
        .theme-toggle, .mobile-btn { background: none; border: 1px solid var(--border-color); color: var(--text-light); width: 35px; height: 35px; border-radius: 50%; font-size: 14px; transition: 0.3s; display: flex; justify-content: center; align-items: center; z-index: 1001; cursor: pointer; }
        .theme-toggle:hover { background: var(--primary-gold); color: #fff; transform: rotate(180deg); }
        .mobile-btn { display: flex; flex-direction: column; gap: 4px; border: none; cursor: pointer; }
        .mobile-btn span { display: block; width: 20px; height: 2px; background: var(--text-light); transition: all 0.3s; }
        .mobile-btn.active span:nth-child(1) { transform: rotate(45deg) translate(5px, 5px); }
        .mobile-btn.active span:nth-child(2) { opacity: 0; }
        .mobile-btn.active span:nth-child(3) { transform: rotate(-45deg) translate(5px, -5px); }
        
        .fullscreen-menu { position: fixed; top: 0; right: -100%; width: 100%; height: 100vh; background: rgba(15,15,15,0.98); backdrop-filter: blur(20px); z-index: 999; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 30px; transition: right 0.5s cubic-bezier(0.77, 0, 0.175, 1); }
        .fullscreen-menu.active { right: 0; }
        .fullscreen-menu a { color: var(--text-light); text-decoration: none; font-family: 'Amiri', serif; font-size: clamp(28px, 6vw, 40px); opacity: 0; transform: translateX(50px); transition: all 0.5s; cursor: pointer; }
        .fullscreen-menu.active a { opacity: 1; transform: translateX(0); }
        .fullscreen-menu.active a:nth-child(1) { transition-delay: 0.2s; }
        .fullscreen-menu.active a:nth-child(2) { transition-delay: 0.3s; }
        .fullscreen-menu.active a:nth-child(3) { transition-delay: 0.4s; }
        .fullscreen-menu.active a:nth-child(4) { transition-delay: 0.5s; }
        .fullscreen-menu a:hover { color: var(--primary-gold); text-shadow: 0 0 20px var(--primary-gold); }
        
        .main-content { margin-top: 120px; padding: 0 20px 50px; max-width: 1400px; margin-left: auto; margin-right: auto; }
        .reveal { opacity: 0; transform: translateY(50px); transition: all 1s cubic-bezier(0.5, 0, 0, 1); }
        .reveal.active { opacity: 1; transform: translateY(0); }
        
        .wave-divider { width: 100%; height: 80px; overflow: hidden; line-height: 0; margin: 40px 0; }
        .wave-divider svg { position: relative; display: block; width: calc(100% + 1.3px); height: 100%; }
        .wave-divider .shape-fill { fill: var(--dark-bg-2); }
        
        .main-slider { height: clamp(300px, 50vh, 500px); border-radius: 20px; overflow: hidden; margin-bottom: 60px; box-shadow: var(--shadow-gold); border: 1px solid var(--border-color); }
        .main-slider .swiper-slide img { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.6); }
        .ad-slider-overlay { position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #fff; text-align: center; padding: 20px; background: linear-gradient(to top, rgba(0,0,0,0.9), transparent); }
        .ad-slider-overlay h2 { font-family: 'Amiri', serif; font-size: clamp(24px, 5vw, 42px); color: var(--primary-gold); margin-bottom: 15px; text-shadow: 0 0 20px rgba(201,169,97,0.5); }
        
        .typing-text { 
            border-right: 2px solid var(--primary-gold); 
            white-space: nowrap; 
            overflow: hidden; 
            font-size: clamp(16px, 3vw, 22px); 
            max-width: 90%; 
            animation: typing 4s steps(40, end), blink-caret .75s step-end infinite;
            background: linear-gradient(90deg, #E5C77C, #C9A961);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            font-family: 'Cairo', sans-serif;
            font-weight: 700;
        }
        @keyframes typing { from { width: 0 } to { width: 100% } }
        @keyframes blink-caret { from, to { border-color: transparent } 50% { border-color: var(--primary-gold) } }
        
        .section { margin-bottom: 80px; }
        .section-header { text-align: center; margin-bottom: 40px; }
        .section-header h2 { font-family: 'Amiri', serif; font-size: clamp(28px, 5vw, 42px); color: var(--text-light); margin-bottom: 15px; position: relative; display: inline-block; }
        .section-header h2 span { color: var(--primary-gold); }
        .section-header h2::after { content: ''; position: absolute; bottom: -10px; left: 50%; transform: translateX(-50%); width: 60px; height: 3px; background: var(--primary-gold); box-shadow: 0 0 10px var(--primary-gold); }
        
        .cat-swiper { overflow: visible; padding: 20px 10px 40px; }
        .glow-card { background: var(--glass-bg); border: 1px solid var(--border-color); border-radius: 16px; overflow: hidden; transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1); position: relative; cursor: pointer; height: 100%; }
        .glow-card::before { content: ''; position: absolute; inset: 0; border-radius: 16px; padding: 1px; background: radial-gradient(300px circle at var(--mouse-x) var(--mouse-y), rgba(201, 169, 97, 0.8), transparent 40%); -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); -webkit-mask-composite: xor; mask-composite: exclude; opacity: 0; transition: opacity 0.3s; z-index: 2; pointer-events: none; }
        .glow-card:hover::before { opacity: 1; }
        .category-img { height: 200px; overflow: hidden; }
        .category-img img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.8s; }
        .glow-card:hover .category-img img { transform: scale(1.1); }
        .category-info { padding: 20px; text-align: center; z-index: 3; position: relative; }
        .category-info h3 { color: var(--text-light); font-size: clamp(16px, 3vw, 18px); font-weight: 700; }
        
        .category-block { margin-bottom: 60px; }
        .category-title-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
        .category-title-row h3 { font-family: 'Amiri', serif; font-size: clamp(22px, 4vw, 28px); color: var(--primary-gold); }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }
        .product-card { background: var(--glass-bg); border: 1px solid var(--border-color); border-radius: 16px; overflow: hidden; transition: all 0.3s; position: relative; }
        .product-card:hover { border-color: var(--primary-gold); transform: translateY(-5px); }
        .product-img { height: 150px; overflow: hidden; }
        .product-img img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s; }
        .product-card:hover .product-img img { transform: scale(1.1); }
        .product-info { padding: 15px; text-align: center; }
        .product-info h4 { color: var(--text-light); margin-bottom: 8px; font-size: clamp(14px, 2.5vw, 16px); }
        .product-price { color: var(--primary-gold); font-weight: 700; font-size: clamp(16px, 3vw, 18px); }
        
        .offers-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 30px; }
        .offer-img { height: 250px; overflow: hidden; position: relative; }
        .offer-img img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.8s; }
        .glow-card:hover .offer-img img { transform: scale(1.1); }
        .offer-badge { position: absolute; top: 15px; right: 15px; background: var(--primary-gold); color: #000; padding: 5px 12px; border-radius: 15px; font-size: 11px; z-index: 4; font-weight: bold; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .offer-info { padding: 25px; z-index: 3; position: relative; }
        .offer-info h3 { color: var(--primary-gold); font-size: clamp(18px, 3vw, 22px); margin-bottom: 15px; }
        .offer-info p { color: var(--text-muted); font-size: 14px; line-height: 1.6; margin-bottom: 15px; }
        .offer-price { font-family: 'Amiri', serif; font-size: clamp(22px, 4vw, 26px); color: var(--primary-gold-light); font-weight: 700; }
        
        .video-section { margin: 80px 0; border-radius: 20px; overflow: hidden; box-shadow: var(--shadow-gold); border: 1px solid var(--border-color); position: relative; height: clamp(300px, 50vh, 500px); }
        .video-section video { width: 100%; height: 100%; object-fit: cover; }
        .video-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; pointer-events: none; }
        .video-overlay h2 { font-family: 'Amiri', serif; font-size: clamp(28px, 5vw, 40px); color: #fff; text-shadow: 0 4px 15px rgba(0,0,0,0.8); }
        
        /* ===== زر الروبوت العائم (بدون طرق التواصل - فقط العودة للأعلى أو القائمة) ===== */
        .fab-container { position: fixed; bottom: 20px; left: 20px; z-index: 9999; display: flex; flex-direction: column; align-items: center; gap: 10px; }
        .fab-robot { width: 50px; height: 50px; border-radius: 50%; background: linear-gradient(145deg, var(--primary-gold-dark), var(--primary-gold-light)); border: none; color: #0f0f0f; font-size: 22px; cursor: pointer; box-shadow: 0 5px 20px rgba(201, 169, 97, 0.6); transition: all 0.3s ease; display: flex; justify-content: center; align-items: center; animation: float 3s ease-in-out infinite; position: relative; z-index: 10; }
        .fab-robot:hover { transform: scale(1.1) rotate(10deg); box-shadow: 0 8px 25px rgba(201, 169, 97, 0.9); }
        .fab-robot.active { animation: none; transform: scale(0.9); }
        @keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-8px); } }
        
        .back-to-top { position: fixed; bottom: 20px; right: 20px; width: 40px; height: 40px; background: var(--primary-gold); color: #000; border: none; border-radius: 50%; font-size: 16px; opacity: 0; transition: all 0.4s; transform: scale(0.5); cursor: pointer; z-index: 999; display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 15px rgba(201, 169, 97, 0.4); }
        .back-to-top.visible { opacity: 1; transform: scale(1); }
        .back-to-top:hover { background: var(--primary-gold-light); transform: translateY(-3px); }
        
        @media (min-width: 992px) {
            .fab-robot { width: 60px; height: 60px; font-size: 26px; bottom: 30px; left: 30px; }
            .back-to-top { width: 50px; height: 50px; font-size: 20px; bottom: 30px; right: 30px; }
        }
        
        @media (max-width: 768px) {
            .main-content { margin-top: 100px; padding: 0 15px 30px; }
            .products-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
            .product-img { height: 100px; }
            .glow-card { border-radius: 12px; }
        }
    </style>
</head>
<body class="no-cursor">
    <div class="cursor-dot" id="cursorDot"></div>
    <div class="cursor-outline" id="cursorOutline"></div>
    <canvas id="particles-bg"></canvas>
    <div class="scroll-progress" id="scrollProgress"></div>
    
    <!-- واجهة التحميل المتطورة Developer Loader -->
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

    <!-- شريط الإعلان المتطور Modern Marquee -->
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

    <nav class="navbar" id="navbar">
        <div class="nav-container">
            <div class="nav-logo" onclick="scrollTo({top:0,behavior:'smooth'})">
                <img src="%LOGO_URL%" alt="Logo">
                <div class="logo-text">
                    <h1>مكتبة الشاغور الحديثة</h1>
                    <p>AL-SHAGHOUR MODERN LIBRARY</p>
                </div>
            </div>
            <div class="nav-actions">
                <button class="theme-toggle" id="themeToggle"><i class="fas fa-moon"></i></button>
                <button class="mobile-btn" id="mobileBtn"><span></span><span></span><span></span></button>
            </div>
        </div>
    </nav>
    
    <div class="fullscreen-menu" id="fullscreenMenu">
        <a href="#home" onclick="closeMenu()">الرئيسية</a>
        <a href="#categories" onclick="closeMenu()">الأقسام</a>
        <a href="#offers" onclick="closeMenu()">العروض</a>
        <a href="#contact" onclick="closeMenu()">تواصل معنا</a>
    </div>

    <div class="main-content">
        <div class="swiper main-slider" id="home">
            <div class="swiper-wrapper">%SLIDER_HTML%</div>
            <div class="swiper-pagination"></div>
        </div>

        <div class="wave-divider">
            <svg data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 120" preserveAspectRatio="none">
                <path d="M321.39,56.44c58-10.79,114.16-30.13,172-41.86,82.39-16.72,168.19-17.73,250.45-.39C823.78,31,906.67,72,985.66,92.83c70.05,18.48,146.53,26.09,214.34,3V0H0V27.35A600.21,600.21,0,0,0,321.39,56.44Z" class="shape-fill"></path>
            </svg>
        </div>

        <section class="section reveal" id="categories">
            <div class="section-header"><h2>تصفح <span>الأقسام</span></h2></div>
            <div class="swiper cat-swiper">
                <div class="swiper-wrapper">%CATEGORIES_HTML%</div>
                <div class="swiper-button-next"></div>
                <div class="swiper-button-prev"></div>
            </div>
        </section>

        <section class="section reveal" id="products_section">
            <div class="section-header"><h2>منتجاتنا <span>المميزة</span></h2></div>
            %PRODUCTS_HTML%
        </section>

        <section class="section reveal" id="offers">
            <div class="section-header"><h2>أحدث <span>العروض</span></h2></div>
            <div class="offers-grid">%OFFERS_HTML%</div>
        </section>

        <section class="section reveal" id="video">
            <div class="section-header"><h2>شاهد <span>الفيديو</span></h2></div>
            <div class="video-section">
                <video src="%VIDEO_URL%" muted loop playsinline id="autoplayVideo"></video>
                <div class="video-overlay"><h2>إبداعات القرطاسية</h2></div>
            </div>
        </section>

        <section class="section reveal" id="contact">
            <div class="section-header"><h2>تواصل <span>معنا</span></h2></div>
            <div class="contact-grid" style="display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:20px; text-align:center;">
                <div class="contact-card" style="background:var(--glass-bg); padding:30px 15px; border-radius:16px; border:1px solid var(--border-color);">
                    <i class="fas fa-map-marker-alt" style="font-size:24px; color:var(--primary-gold); margin-bottom:15px;"></i>
                    <h4 style="color:var(--text-light); margin-bottom:10px;">العنوان</h4>
                    <p style="color:var(--text-muted); font-size:14px;">سوريا - دمشق - الشاغور</p>
                </div>
                <div class="contact-card" style="background:var(--glass-bg); padding:30px 15px; border-radius:16px; border:1px solid var(--border-color);">
                    <i class="fas fa-clock" style="font-size:24px; color:var(--primary-gold); margin-bottom:15px;"></i>
                    <h4 style="color:var(--text-light); margin-bottom:10px;">أوقات العمل</h4>
                    <p style="color:var(--text-muted); font-size:14px;">السبت - الخميس: 9 ص - 9 م</p>
                </div>
                <div class="contact-card" style="background:var(--glass-bg); padding:30px 15px; border-radius:16px; border:1px solid var(--border-color);">
                    <i class="fas fa-phone-alt" style="font-size:24px; color:var(--primary-gold); margin-bottom:15px;"></i>
                    <h4 style="color:var(--text-light); margin-bottom:10px;">الهاتف</h4>
                    <p style="color:var(--text-muted); font-size:14px;">+963 11 123 4567</p>
                </div>
            </div>
        </section>
    </div>
    
    <!-- زر الروبوت العائم (بدون قائمة التواصل) -->
    <div class="fab-container">
        <button class="fab-robot" id="fabRobot" title="العودة للأعلى">
            <i class="fas fa-robot" id="fabIcon"></i>
        </button>
    </div>

    <button class="back-to-top" id="backToTop" title="للأعلى"><i class="fas fa-arrow-up"></i></button>

    <script src="https://cdn.jsdelivr.net/npm/swiper@10/swiper-bundle.min.js"></script>
    <script>
        // ===== منطق واجهة التحميل المتطورة =====
        let devProgress = 0; 
        const devLoader = document.getElementById('devLoader'); 
        const devPercentText = document.getElementById('devPercent');
        const devBarFill = document.getElementById('devBarFill');
        const devInterval = setInterval(() => { 
            devProgress += Math.random() * 15 + 5; 
            if(devProgress >= 100) { 
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
        // Fallback
        setTimeout(() => { devLoader.classList.add('hidden'); }, 5000);

        // ===== المؤشر المخصص =====
        const dot = document.getElementById('cursorDot'); 
        const outline = document.getElementById('cursorOutline');
        if (window.innerWidth > 768) {
            let mx=0, my=0, ox=0, oy=0;
            document.addEventListener('mousemove', e => { 
                mx=e.clientX; my=e.clientY; 
                dot.style.opacity = 1; outline.style.opacity = 1; 
                dot.style.left=mx+'px'; dot.style.top=my+'px'; 
            });
            function animCursor(){ 
                ox+=(mx-ox)*0.15; oy+=(my-oy)*0.15; 
                outline.style.left=ox+'px'; outline.style.top=oy+'px'; 
                requestAnimationFrame(animCursor); 
            } 
            animCursor();
        } else { 
            document.body.classList.remove('no-cursor'); 
            dot.style.display = 'none';
            outline.style.display = 'none';
        }

        // ===== الجزيئات =====
        const canvas=document.getElementById('particles-bg'); const ctx=canvas.getContext('2d'); let p=[];
        function res(){canvas.width=innerWidth;canvas.height=innerHeight;} res(); addEventListener('resize',res);
        class P{constructor(){this.x=Math.random()*canvas.width;this.y=Math.random()*canvas.height;this.s=Math.random()*2+1;this.sx=Math.random()*0.5-0.25;this.sy=Math.random()*0.5-0.25;}u(){this.x+=this.sx;this.y+=this.sy;if(this.x<0||this.x>canvas.width)this.sx*=-1;if(this.y<0||this.y>canvas.height)this.sy*=-1;}d(){ctx.fillStyle='rgba(201,169,97,0.5)';ctx.beginPath();ctx.arc(this.x,this.y,this.s,0,Math.PI*2);ctx.fill();}}
        function init(){p=[];for(let i=0;i<30;i++)p.push(new P());}
        function conn(){for(let a=0;a<p.length;a++)for(let b=a;b<p.length;b++){let d=Math.hypot(p[a].x-p[b].x,p[a].y-p[b].y);if(d<120){ctx.strokeStyle='rgba(201,169,97,'+(0.2-d/600)+')';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(p[a].x,p[a].y);ctx.lineTo(p[b].x,p[b].y);ctx.stroke();}}}
        function anim(){ctx.clearRect(0,0,canvas.width,canvas.height);p.forEach(e=>{e.u();e.d();});conn();requestAnimationFrame(anim);} init(); anim();

        // ===== شريط التنقل والقائمة =====
        const navbar = document.getElementById('navbar'); const menu = document.getElementById('fullscreenMenu'); const btn = document.getElementById('mobileBtn'); let lastScroll = 0;
        window.addEventListener('scroll', () => {
            let st = window.scrollY; document.getElementById('scrollProgress').style.width = ((st / (document.body.offsetHeight - innerHeight)) * 100) + '%';
            if(st > 300) document.getElementById('backToTop').classList.add('visible'); else document.getElementById('backToTop').classList.remove('visible');
            if (st > lastScroll && st > 100) navbar.classList.add('hide-nav'); else navbar.classList.remove('hide-nav'); lastScroll = st;
        });
        document.getElementById('backToTop').addEventListener('click', () => scrollTo({top:0,behavior:'smooth'}));
        btn.addEventListener('click', () => { btn.classList.toggle('active'); menu.classList.toggle('active'); });
        function closeMenu() { btn.classList.remove('active'); menu.classList.remove('active'); }

        const obs = new IntersectionObserver((e)=>{e.forEach(el=>{if(el.isIntersecting)el.target.classList.add('active');})},{threshold:0.1});
        document.querySelectorAll('.reveal').forEach(el=>obs.observe(el));

        new Swiper('.main-slider', {loop:true, autoplay:{delay:4000}, effect:'slide', pagination:{el:'.swiper-pagination'}});
        new Swiper('.cat-swiper', {slidesPerView:1, spaceBetween:20, loop:true, autoplay:{delay:3000}, breakpoints:{640:{slidesPerView:2},992:{slidesPerView:3},1200:{slidesPerView:4}}, navigation:{nextEl:'.swiper-button-next',prevEl:'.swiper-button-prev'}});

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

        const video = document.getElementById('autoplayVideo');
        new IntersectionObserver((e)=>{e.forEach(en=>{if(en.isIntersecting)video.play().catch(()=>{});else video.pause();})},{threshold:0.5}).observe(video);

        // ===== تأثيرات البطاقات =====
        document.querySelectorAll('.glow-card, .contact-card, .product-card').forEach(card => {
            card.addEventListener('mousemove', e => { let r = card.getBoundingClientRect(); card.style.setProperty('--mouse-x', (e.clientX-r.left)+'px'); card.style.setProperty('--mouse-y', (e.clientY-r.top)+'px'); let rx = (e.clientY - r.top - r.height/2) / 20; let ry = (r.width/2 - (e.clientX - r.left)) / 20; card.style.transform = `perspective(1000px) rotateX(${-rx}deg) rotateY(${-ry}deg) scale(1.03)`; });
            card.addEventListener('mouseleave', () => card.style.transform = 'none');
        });

        // ===== زر الروبوت العائم (تحديث ليعمل كزر للعودة للأعلى بحركة سلسة) =====
        const fabRobot = document.getElementById('fabRobot');
        fabRobot.addEventListener('click', () => {
            fabRobot.classList.toggle('active');
            window.scrollTo({ top: 0, behavior: 'smooth' });
            setTimeout(() => fabRobot.classList.remove('active'), 1000);
        });
    </script>
</body>
</html>
"""

    def generate_html(self):
        data = self.db.load()
        if data.get("maintenance_mode", False):
            return self.maintenance_template.replace("%MAINTENANCE_MSG%", str(data.get("maintenance_message", "نحن نقوم بأعمال صيانة وتطوير. سنعود قريباً!")))

        slider_text = data.get("slider_text", "وجهتك الأولى للقرطاسية والمستلزمات الفنية في سوريا")
        slider_html = "".join([f'<div class="swiper-slide"><img src="{img}"><div class="ad-slider-overlay"><h2>مكتبة الشاغور الحديثة</h2><div class="typing-text">{slider_text}</div></div></div>' for img in data.get("slider_images", [])])
        
        cats_html = "".join([f'<div class="swiper-slide"><div class="glow-card"><div class="category-img"><img src="{c["img"]}"></div><div class="category-info"><h3>{c["name"]}</h3></div></div></div>' for c in data.get("categories", [])])
        
        prods_html_parts = []
        for cat in data.get("categories", []):
            if not cat.get("products"): continue
            prods_html_parts.append(f'<div class="category-block reveal"><div class="category-title-row"><h3>{cat["name"]}</h3></div><div class="products-grid">')
            for prod in cat.get("products", []):
                prods_html_parts.append(f'<div class="product-card"><div class="product-img"><img src="{prod["img"]}"></div><div class="product-info"><h4>{prod["name"]}</h4><p class="product-price">{prod["price"]} ل.س</p></div></div>')
            prods_html_parts.append('</div></div>')
        prods_html = "".join(prods_html_parts)
            
        offers_html = "".join([f'<div class="glow-card"><div class="offer-img"><span class="offer-badge">عرض خاص</span><img src="{o["img"]}"></div><div class="offer-info"><h3>{o["title"]}</h3><p>{o["desc"]}</p><p class="offer-price">{o["price"]}</p></div></div>' for o in data.get("offers", [])])
        
        c = data.get("contacts", {})
        
        # معالجة الإعلانات بطريقة عصرية مقسمة
        ann_text = data.get("announcements", "مرحباً بكم | توصيل سريع | عروض حصرية")
        ann_parts = [part.strip() for part in ann_text.split("|")]
        while len(ann_parts) < 3: ann_parts.append("مرحباً بكم في مكتبة الشاغور")
            
        final_html = self.html_template
        final_html = final_html.replace("%LOGO_URL%", str(data.get("logo_url", DEFAULT_LOGO)))
        final_html = final_html.replace("%ICON_URL%", str(data.get("icon_url", DEFAULT_LOGO)))
        final_html = final_html.replace("%ANNOUNCEMENT_ITEM_1%", ann_parts[0])
        final_html = final_html.replace("%ANNOUNCEMENT_ITEM_2%", ann_parts[1])
        final_html = final_html.replace("%ANNOUNCEMENT_ITEM_3%", ann_parts[2])
        final_html = final_html.replace("%SLIDER_HTML%", slider_html)
        final_html = final_html.replace("%CATEGORIES_HTML%", cats_html)
        final_html = final_html.replace("%PRODUCTS_HTML%", prods_html)
        final_html = final_html.replace("%OFFERS_HTML%", offers_html)
        final_html = final_html.replace("%VIDEO_URL%", str(data.get("video_url", "")))
        # تم إبقاء المتغيرات في حال الحاجة لها مستقبلاً
        final_html = final_html.replace("%WHATSAPP%", str(c.get("whatsapp", "")))
        final_html = final_html.replace("%INSTAGRAM%", str(c.get("instagram", "")))
        final_html = final_html.replace("%GMAIL%", str(c.get("gmail", "")))
        return final_html

    async def handle_index(self, request):
        try:
            return web.Response(text=self.generate_html(), content_type='text/html')
        except Exception as e:
            logging.error(f"خطأ في توليد الصفحة: {e} - main.py:621")
            return web.Response(text="Internal Server Error", status=500)

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

    def main_kb(self):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖼 الشعار والأيقونة", callback_data="manage_branding")],
            [InlineKeyboardButton(text="📢 الإعلان", callback_data="edit_announcement"), InlineKeyboardButton(text="ℹ️ النص التعريفي", callback_data="edit_about")],
            [InlineKeyboardButton(text="✍️ نص السلايدر", callback_data="edit_slider_text"), InlineKeyboardButton(text="🖼 السلايدر", callback_data="manage_slider")],
            [InlineKeyboardButton(text="🎬 الفيديو", callback_data="edit_video"), InlineKeyboardButton(text="📂 الأقسام", callback_data="manage_cats")],
            [InlineKeyboardButton(text="📦 المنتجات", callback_data="manage_prods"), InlineKeyboardButton(text="🏷 العروض", callback_data="manage_offers")],
            [InlineKeyboardButton(text="📞 التواصل", callback_data="edit_contacts")],
            [InlineKeyboardButton(text="🛠 وضع الصيانة", callback_data="manage_maint")]
        ])

    def _register_handlers(self):
        @self.router.message(CommandStart())
        async def start_cmd(message: Message, state: FSMContext):
            if message.from_user.id != ADMIN_ID: return await message.answer("عذراً، هذه اللوحة مخصصة للمسؤولين فقط.")
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
            data = self.db.load(); data["maintenance_message"] = message.text; self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث رسالة الصيانة!", reply_markup=self.main_kb())

        # --- الشعار والأيقونة ---
        @self.router.callback_query(F.data == "manage_branding")
        async def manage_branding_cb(cb: CallbackQuery):
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="رفع الشعار (Logo)", callback_data="upload_logo")],
                [InlineKeyboardButton(text="رفع الأيقونة (Favicon)", callback_data="upload_icon")],
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
                if not os.path.exists(UPLOADS_DIR): os.makedirs(UPLOADS_DIR)
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
            data = self.db.load(); data["announcements"] = message.text; self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث الإعلان! 📢", reply_markup=self.main_kb())

        # --- النص التعريفي ---
        @self.router.callback_query(F.data == "edit_about")
        async def edit_about_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل النص التعريفي الجديد (About):")
            await state.set_state(self.AdminStates.waiting_for_about_text)

        @self.router.message(self.AdminStates.waiting_for_about_text)
        async def proc_about(message: Message, state: FSMContext):
            data = self.db.load(); data["about_text"] = message.text; self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث النص التعريفي! ℹ️", reply_markup=self.main_kb())

        # --- نص السلايدر ---
        @self.router.callback_query(F.data == "edit_slider_text")
        async def edit_slider_text_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل النص الذي سيظهر في السلايدر (تأثير الكتابة):")
            await state.set_state(self.AdminStates.waiting_for_slider_text)

        @self.router.message(self.AdminStates.waiting_for_slider_text)
        async def proc_slider_text(message: Message, state: FSMContext):
            data = self.db.load(); data["slider_text"] = message.text; self.db.save(data)
            await state.clear()
            await message.answer("تم تحديث نص السلايدر! ✍️", reply_markup=self.main_kb())

        # --- الفيديو ---
        @self.router.callback_query(F.data == "edit_video")
        async def edit_vid_cb(cb: CallbackQuery, state: FSMContext):
            await cb.message.answer("أرسل رابط الفيديو الجديد (MP4):")
            await state.set_state(self.AdminStates.waiting_for_video_url)

        @self.router.message(self.AdminStates.waiting_for_video_url)
        async def proc_vid(message: Message, state: FSMContext):
            data = self.db.load(); data["video_url"] = message.text; self.db.save(data)
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
                if not os.path.exists(UPLOADS_DIR): os.makedirs(UPLOADS_DIR)
                await self.bot.download_file(file.file_path, file_path)
                data = self.db.load()
                if "slider_images" not in data: data["slider_images"] = []
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
                if not os.path.exists(UPLOADS_DIR): os.makedirs(UPLOADS_DIR)
                await self.bot.download_file(file.file_path, file_path)
                data = self.db.load()
                cat_data = await state.get_data()
                if "categories" not in data: data["categories"] = []
                data["categories"].append({"id": uuid.uuid4().hex, "name": cat_data["name"], "img": f"/uploads/{file_name}", "products": []})
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
            if not cat: return await cb.answer("القسم غير موجود")
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
                if not os.path.exists(UPLOADS_DIR): os.makedirs(UPLOADS_DIR)
                await self.bot.download_file(file.file_path, file_path)
                data = self.db.load()
                prod_data = await state.get_data()
                cat_id = prod_data["cat_id"]
                for cat in data.get("categories", []):
                    if cat["id"] == cat_id:
                        cat.setdefault("products", []).append({"id": uuid.uuid4().hex, "name": prod_data["name"], "price": prod_data["price"], "img": f"/uploads/{file_name}"})
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
                if not os.path.exists(UPLOADS_DIR): os.makedirs(UPLOADS_DIR)
                await self.bot.download_file(file.file_path, file_path)
                data = self.db.load()
                off_data = await state.get_data()
                if "offers" not in data: data["offers"] = []
                data["offers"].append({"id": uuid.uuid4().hex, "title": off_data["title"], "price": off_data["price"], "desc": off_data["desc"], "img": f"/uploads/{file_name}"})
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
            state_map = {"con_wa": (self.AdminStates.waiting_for_whatsapp, "واتساب"), "con_ig": (self.AdminStates.waiting_for_instagram, "إنستغرام"), "con_gm": (self.AdminStates.waiting_for_gmail, "جيميل")}
            new_state, name = state_map[cb.data]
            await state.set_state(new_state)
            await cb.message.answer(f"أرسل {name} الجديد:")

        async def process_contact(message: Message, state: FSMContext, key):
            data = self.db.load()
            if "contacts" not in data: data["contacts"] = {}
            data["contacts"][key] = message.text; self.db.save(data)
            await state.clear()
            await message.answer("تم التحديث! 📞", reply_markup=self.main_kb())

        @self.router.message(self.AdminStates.waiting_for_whatsapp)
        async def proc_wa(message: Message, state: FSMContext): await process_contact(message, state, "whatsapp")
        @self.router.message(self.AdminStates.waiting_for_instagram)
        async def proc_ig(message: Message, state: FSMContext): await process_contact(message, state, "instagram")
        @self.router.message(self.AdminStates.waiting_for_gmail)
        async def proc_gm(message: Message, state: FSMContext): await process_contact(message, state, "gmail")

    async def run_background(self):
        while True:
            try:
                await self.bot.delete_webhook(drop_pending_updates=True)
                logging.info("🤖 البوت يعمل بشكل سليم ويراقب الرسائل... - main.py:1087")
                await self.dp.start_polling(self.bot, handle_signals=False)
                logging.info("Polling stopped normally. Restarting in 15 seconds... - main.py:1089")
                await asyncio.sleep(15)
            except Exception as e:
                logging.error(f"❌ خطأ في تشغيل البوت (ربما شبكة الاستضافة تمنع تيليجرام): {e} - main.py:1092")
                logging.info("سيتم إعادة محاولة تشغيل البوت بعد 60 ثانية لمنع استهلاك المعالج (Code 137)... - main.py:1093")
                await asyncio.sleep(60) 

# ==========================================
# 4. المنفذ الرئيسي (Main Executor)
# ==========================================
async def main():
    logging.info("🚀 بدء تشغيل التطبيق... - main.py:1100")
    if not os.path.exists(UPLOADS_DIR):
        try:
            os.makedirs(UPLOADS_DIR)
        except Exception as e:
            logging.warning(f"تعذر إنشاء مجلد الرفعات عند الإقلاع: {e} - main.py:1105")

    web_app_instance = WebServer(db)
    bot_instance = TelegramBot(db)

    app = web.Application()
    app.router.add_get('/', web_app_instance.handle_index)
    app.router.add_get('/favicon.ico', web_app_instance.handle_favicon)
    app.router.add_get('/uploads/{file_path}', web_app_instance.handle_uploads)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    try:
        await site.start()
        logging.info(f"✅ خادم الويب يعمل بنجاح على المنفذ {port} - main.py:1123")
    except Exception as e:
        logging.error(f"❌ فشل تشغيل خادم الويب: {e} - main.py:1125")
        return

    asyncio.create_task(bot_instance.run_background())
    
    try:
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logging.error(f"❌ خطأ قاتل في حلقة الأحداث: {e} - main.py:1134")
    finally:
        await runner.cleanup()
        await bot_instance.bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nتم إيقاف البرنامج يدوياً. - main.py:1143")
    except Exception as e:
        logging.error(f"❌ خطأ قاتل خارجي: {e} - main.py:1145")
        traceback.print_exc()