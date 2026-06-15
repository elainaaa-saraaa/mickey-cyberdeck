import tkinter as tk
from PIL import Image, ImageTk
import os
import sys
import random
import time
import threading
import sqlite3
from datetime import date
import psutil

# --- MAGIC FUNCTION FOR .EXE PACKAGING ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MickeyCyberdeck:
    def __init__(self, root):
        self.root = root
        self.root.title("Mickey")

        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)

        self.trans_color = "#123456"
        self.root.config(bg=self.trans_color)
        self.root.wm_attributes("-transparentcolor", self.trans_color)


        self.WIN_W = 360
        self.WIN_H = 500

        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        sx = sw - self.WIN_W - 20
        sy = sh - self.WIN_H - 48
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}+{sx}+{sy}")

    
        self.dog_states = {
            "idle":   ["dog_eyeopen.png",       "dog_eyeclose.png"],
            "happy":  ["dog_happy_eyeopen.png",  "dog_happy_eyeclose.png"],
            "sleepy": ["dog_sleepy.png"],
            "sad":    ["dog_sad.png"],
        }
        self.current_state = "idle"
        self.dog_frame_index = 0
        self.dog_canvas_image = None
        

        self.current_weather = "sunny"
        self.wind_speed = 0.4
        self.cloud_offset = 0.0
        self.sunrise_hour = 6.0
        self.sunset_hour = 18.0
        self.night_sleep_triggered = False
        self.morning_wake_triggered = False
        
        # Timers and Pomodorro
        self.session_start_time = time.time()
        self.last_break_time = time.time()
        self.max_focus_time = 900.0  # 15 mins till burnout, you can change this according to youu
        self.energy_boost = 0.0
        self.needs_break = False  
        
        self.pomodoro_active = False
        self.pomodoro_end_time = 0
        self.overheat_lock = False
        self.bone_float_y = 0.0
        self.bone_float_dir = 0.3
        
        self.last_pet_time = 0
        self.pet_timer = None
        self.msg_after = None

        self.init_database()

    
        self.canvas = tk.Canvas(root, width=self.WIN_W, height=self.WIN_H, bg=self.trans_color, bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.clock_label = tk.Label(root, text="", bg=self.trans_color, fg="#ff3333", font=("Courier", 14, "bold"), cursor="hand2")
        self.clock_label.place(x=self.WIN_W//2 - 50, y=10)

        self.grip = tk.Label(root, text="⇲", bg=self.trans_color, fg="#ffcc88", font=("Arial", 16), cursor="sizing")
        self.grip.place(relx=1.0, rely=1.0, anchor="se")
        self.grip.bind("<B1-Motion>", self.resize_drag)
        self.grip.bind("<ButtonRelease-1>", self.resize_release)

        self.close_btn = tk.Label(root, text="✖", bg=self.trans_color, fg="#ff5555", font=("Arial", 14, "bold"), cursor="hand2")
        self.close_btn.place(x=self.WIN_W - 25, y=5)
        
        self.close_btn.bind("<Button-1>", self.safe_exit)         
        self.root.bind("<Escape>", self.dismiss_message)          

        # Bindings
        self.canvas.bind("<Button-1>",  self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.drag_window)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.clock_label.bind("<Double-Button-1>", self.toggle_pomodoro)

        # Breakdone button
        self.break_btn = tk.Label(root, text="[ BREAK DONE ]", bg="#00ff00", fg="black", font=("Courier", 12, "bold"), cursor="hand2", bd=2, relief="solid")
        self.break_btn.bind("<Button-1>", self.action_break_done)

        self.drag_start_x = 0
        self.drag_start_y = 0

        self._image_cache = {}
        self._preload_images()

        self.update_dog_animation()
        self.environment_engine_loop()
        
        self.sync_db_loop()
        self.auto_sync_weather_loop()
        self.hardware_watchdog_loop() 

    def hardware_watchdog_loop(self):
        """Silently monitors CPU/RAM. Mickey panics if the computer is suffering!"""
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        if cpu > 85.0 or ram > 90.0:
            if not self.overheat_lock: 
                self.overheat_lock = True
                self.current_state = "sad"
                if cpu > 85.0:
                    self.show_bowl_message(f"⚠️ OVERLOAD! 🚨\nCPU at {int(cpu)}%!\nPlease close some tabs!", 6000)
                else:
                    self.show_bowl_message(f"⚠️ MEMORY FULL! 🚨\nRAM at {int(ram)}%!\nMy brain hurts!", 6000)
        else:
            if self.overheat_lock:
                self.overheat_lock = False 
                self.current_state = "happy"
                self.show_bowl_message("Phew! System cooled down.\nGood job! ❄️", 4000)

        self.root.after(5000, self.hardware_watchdog_loop)

    # SQLITE database 
    def init_database(self):
        self.db_path = resource_path("mickey_telemetry.db")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                log_date TEXT PRIMARY KEY, screen_minutes INTEGER,
                pet_count INTEGER, weather_logged TEXT
            )
        ''')
        self.conn.commit()
        today = date.today().isoformat()
        self.cursor.execute("INSERT OR IGNORE INTO daily_stats (log_date, screen_minutes, pet_count, weather_logged) VALUES (?, 0, 0, 'none')", (today,))
        self.conn.commit()

    def update_db_stat(self, stat_name, increment=1, string_val=None):
        today = date.today().isoformat()
        if string_val:
            self.cursor.execute(f"UPDATE daily_stats SET {stat_name} = ? WHERE log_date = ?", (string_val, today))
        else:
            self.cursor.execute(f"UPDATE daily_stats SET {stat_name} = {stat_name} + ? WHERE log_date = ?", (increment, today))
        self.conn.commit()

    def sync_db_loop(self):
        self.update_db_stat("screen_minutes", 1)
        self.root.after(60000, self.sync_db_loop)

    def safe_exit(self, event=None):
        self.conn.close()
        self.root.destroy()

    #Current weather
    def auto_sync_weather_loop(self):
        self.sync_weather(show_msg=False)
        self.root.after(900000, self.auto_sync_weather_loop) 

    def sync_weather(self, event=None, show_msg=True):
        if show_msg: self.show_bowl_message("📡 Checking satellite...")
        threading.Thread(target=self._fetch_weather_task, args=(show_msg,), daemon=True).start()

    def _fetch_weather_task(self, show_msg):
        try:
            import requests
            res = requests.get("https://wttr.in/?format=j1", timeout=5)
            data = res.json()
            
            # Weather mapping
            desc = data['current_condition'][0]['weatherDesc'][0]['value'].lower()
            wind_kmh = int(data['current_condition'][0]['windspeedKmph'])
            
            # Astronomical time mapping (Sunrise/Sunset)
            try:
                astro = data.get('weather', [{}])[0].get('astronomy', [{}])[0]
                sunrise_str = astro.get('sunrise', '06:00 AM')
                sunset_str = astro.get('sunset', '06:00 PM')
                
                def parse_ampm(s):
                    t, ampm = s.strip().split(" ")
                    h, m = map(int, t.split(":"))
                    if ampm.upper() == "PM" and h != 12: h += 12
                    if ampm.upper() == "AM" and h == 12: h = 0
                    return h + (m / 60.0)
                    
                sr = parse_ampm(sunrise_str) or 6.0
                ss = parse_ampm(sunset_str) or 18.0
            except:
                sr, ss = 6.0, 18.0
                
            self.root.after(0, self.apply_weather, desc, wind_kmh, show_msg, sr, ss)
        except Exception:
            if show_msg: self.root.after(0, self.show_bowl_message, "Radar offline! ☁️")

    def apply_weather(self, desc, wind_kmh, show_msg, sr=6.0, ss=18.0):
        self.sunrise_hour = sr
        self.sunset_hour = ss
        
        if any(w in desc for w in ["rain", "drizzle", "shower"]): self.current_weather = "rainy"
        elif any(w in desc for w in ["snow", "ice", "blizzard"]): self.current_weather = "snowy"
        elif any(w in desc for w in ["cloud", "overcast", "fog"]): self.current_weather = "cloudy"
        else: self.current_weather = "sunny"
        
        self.update_db_stat("weather_logged", string_val=self.current_weather)

        if wind_kmh > 25: self.wind_speed, wind_status = 2.0, " (Windy! 🌬️)"
        elif wind_kmh > 15: self.wind_speed, wind_status = 1.0, " (Breezy 🍃)"
        else: self.wind_speed, wind_status = 0.4, ""
            
        if show_msg: self.show_bowl_message(f"[{desc.upper()}{wind_status}]")

    def on_canvas_double_click(self, event):
        bx, by = self._bowl_origin()
        
        #Click the sun/moon for the current weather 
        if event.x <= 80 and event.y <= 80:
            self.sync_weather(show_msg=True)
            return

        # Click Mickey to put her to sleep
        if event.y < by:
            self.toggle_nap()

    def toggle_nap(self):
        if self.pomodoro_active:
            self.show_bowl_message("[ACCESS DENIED]\nFOCUS MODE ACTIVE")
            return
        if self.needs_break:
            self.show_bowl_message("You must take a break first!\nClick [BREAK DONE]")
            return
            
        if self.current_state == "sleepy":
            self.current_state = "happy"
            # NOTE: Timer reset explicitly removed. The 15 min focus timer continues.
            self.show_bowl_message("Yawn... I'm awake! ☀️")
            p = self.canvas.create_text(self.WIN_W//2, self.WIN_H//2 - 50, text="☀️", font=("Arial", 18), tags="particle")
            self.animate_float(p, 15, -3)
            if self.pet_timer: self.root.after_cancel(self.pet_timer)
            self.pet_timer = self.root.after(3000, self.revert_to_idle)
        else:
            self.current_state = "sleepy"
            self.show_bowl_message("Nap time...\nTimer paused. Zzz 😴")
            p = self.canvas.create_text(self.WIN_W//2 + 20, self.WIN_H//2 - 50, text="Zzz", fill="#88ccff", font=("Courier", 16, "bold"), tags="particle")
            self.animate_float(p, 20, -2)

    def toggle_pomodoro(self, event):
        """Double click the clock to toggle 25-minute deep focus mode."""
        if self.pomodoro_active:
            self.pomodoro_active = False
            self.current_state = "idle"
            self.show_bowl_message("[ FOCUS DEACTIVATED ]")
        else:
            self.pomodoro_active = True
            self.pomodoro_end_time = time.time() + (25 * 60) # 25 mins
            self.current_state = "idle"
            self.show_bowl_message("[ DEEP WORK: 25 MINS ]")

    def pet_dog(self, event):
        if self.current_state == "sleepy" or self.needs_break or self.pomodoro_active: return
        if time.time() - self.last_pet_time > 0.4:
            self.last_pet_time = time.time()
            self.current_state = "happy"
            self.update_db_stat("pet_count", 1)

            hx, hy = event.x + random.randint(-20, 20), event.y - 30
            heart = self.canvas.create_text(hx, hy, text="❤️", fill="red", font=("Arial", 16), tags="particle")
            self.animate_float(heart, 15, -4)
            if self.pet_timer: self.root.after_cancel(self.pet_timer)
            self.pet_timer = self.root.after(2000, self.revert_to_idle)

    def revert_to_idle(self):
        if self.current_state == "happy" and not self.needs_break and not self.overheat_lock: 
            self.current_state = "idle"

    def animate_float(self, item_id, ticks_left, y_movement):
        if ticks_left > 0:
            self.canvas.move(item_id, 0, y_movement)
            self.root.after(50, self.animate_float, item_id, ticks_left - 1, y_movement)
        else:
            self.canvas.delete(item_id)

    # Breakdone reset 
    def action_break_done(self, event=None):
        """Unlocks Mickey from sad mode after the user takes a break."""
        self.needs_break = False
        self.last_break_time = time.time() # Resets the timer!
        self.current_state = "happy"
        self.break_btn.place_forget() 
        self.show_bowl_message("Break complete!\nLet's get back to it!", 4000)

    # Window Resizing 
    def resize_drag(self, event):
        new_w = max(320, self.root.winfo_pointerx() - self.root.winfo_rootx())
        new_h = max(420, self.root.winfo_pointery() - self.root.winfo_rooty())
        self.root.geometry(f"{new_w}x{new_h}")
        self.clock_label.place(x=new_w//2 - 45, y=6)
        self.close_btn.place(x=new_w - 25, y=5)
        
        if self.needs_break:
            self.break_btn.place(x=new_w//2 - 75, y=new_h - 200)

    def resize_release(self, event):
        self.WIN_W, self.WIN_H = self.root.winfo_width(), self.root.winfo_height()
        self.canvas.config(width=self.WIN_W, height=self.WIN_H)
        self._preload_images()

    def _preload_images(self):
        all_frames = set(frame for frames in self.dog_states.values() for frame in frames)
        for fname in all_frames:
            abs_path = resource_path(fname)
            if os.path.exists(abs_path):
                img = Image.open(abs_path).convert("RGBA")
                dog_h = self.WIN_H - 40 - 150 
                self._image_cache[fname] = ImageTk.PhotoImage(img.resize((self.WIN_W, dog_h), Image.NEAREST))

    # Dashboard
    def show_stats(self):
        """Compiles system and DB stats into a clean readout."""
        today = date.today().isoformat()
        self.cursor.execute("SELECT screen_minutes, pet_count FROM daily_stats WHERE log_date = ?", (today,))
        result = self.cursor.fetchone()
        mins, pets = result[0] if result else 0, result[1] if result else 0
        hrs, leftover = mins // 60, mins % 60
        
        elapsed = time.time() - self.last_break_time
        energy_pct = max(0.0, min(1.0, 1.0 - (elapsed / self.max_focus_time)))
        
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        
        msg = f"[ SYSTEM DASHBOARD ]\nBat: {int(energy_pct*100)}%\nScreen: {hrs}h {leftover}m\nCPU: {int(cpu)}% RAM: {int(ram)}%\nPets: {pets}"
        self.show_bowl_message(msg, 6000)

    def on_canvas_click(self, event):
        bx, by = self._bowl_origin()
        
        bone_x = self.WIN_W // 2 - 28
        bone_y = self.WIN_H - 45 + int(self.bone_float_y)
        if bone_x <= event.x <= bone_x + 56 and bone_y <= event.y <= bone_y + 24:
            self.show_stats()
            return

        # The whimsical messagess (my fav part)
        if bx <= event.x <= bx + 144 and by <= event.y <= by + 64:
            self.show_bowl_message(random.choice([
                "Mickey says hiiii! 🐾", 
                "Double-click me to take a nap! 💤",
                "Double-click sun/moon for weather! ☀️",
                "You're doing great today! 🌟",
                "Remember to hydrate! 💧",
                "Believe that everything happens for a reason:>",
                "Don't stress yourself out, take a breath :)"
            ]))
            return
            
        self.drag_start_x, self.drag_start_y = event.x, event.y
        self.root.focus_set() 

    def drag_window(self, event):
        nx, ny = self.root.winfo_x() + (event.x - self.drag_start_x), self.root.winfo_y() + (event.y - self.drag_start_y)
        self.root.geometry(f"+{nx}+{ny}")

    # Message box
    def dismiss_message(self, event=None):
        """Called safely when the Escape key is pressed."""
        if self.msg_after:
            self.root.after_cancel(self.msg_after)
            self.msg_after = None
        self.canvas.delete("bowlmsg")

    def show_bowl_message(self, message, duration=4000):
        self.dismiss_message() # Clear any existing messages safely
        
        bx, by = self._bowl_origin()
        lines = message.count('\n') + 1
        bh = 30 + (lines * 15)  
        bw = self.WIN_W - 30
        
        mx = self.WIN_W // 2
        my = by + 64 + 10 + (bh // 2)
        rx, ry = mx - bw//2, my - bh//2
        
        # Retro Pixel Border (8-bit style)
        self.canvas.create_rectangle(rx+4, ry, rx+bw-4, ry+bh, fill="#111111", outline="", tags="bowlmsg")
        self.canvas.create_rectangle(rx, ry+4, rx+bw, ry+bh-4, fill="#111111", outline="", tags="bowlmsg")
        
        self.canvas.create_rectangle(rx+8, ry, rx+bw-8, ry+4, fill="white", outline="", tags="bowlmsg") 
        self.canvas.create_rectangle(rx+8, ry+bh-4, rx+bw-8, ry+bh, fill="white", outline="", tags="bowlmsg") 
        self.canvas.create_rectangle(rx, ry+8, rx+4, ry+bh-8, fill="white", outline="", tags="bowlmsg") 
        self.canvas.create_rectangle(rx+bw-4, ry+8, rx+bw, ry+bh-8, fill="white", outline="", tags="bowlmsg") 
        
        for cx, cy in [(rx+4, ry+4), (rx+bw-8, ry+4), (rx+4, ry+bh-8), (rx+bw-8, ry+bh-8)]:
            self.canvas.create_rectangle(cx, cy, cx+4, cy+4, fill="white", outline="", tags="bowlmsg")
            
        self.canvas.create_text(mx, my, text=message, font=("Courier", 9, "bold"), fill="white", tags="bowlmsg", justify="center")
        self.msg_after = self.root.after(duration, self.dismiss_message)

    #Pixel components
    def _px(self, ox, oy, col, size=5, tag="sky"):
        self.canvas.create_rectangle(ox, oy, ox+size, oy+size, fill=col, outline="", tags=tag)

    def _bowl_origin(self):
        return (self.WIN_W - 144) // 2, self.WIN_H - 180  

    def draw_pixel_bone(self, ox, oy):
        ps = 4
        bone_pattern = [
            "  oo      oo  ",
            " owwo    owwo ",
            " owmmmmmmmmso ",
            " omssssssssso ",
            " osso    osso ",
            "  oo      oo  "
        ]
        color_map = {'w': '#ffffff', 'm': '#e6e6e6', 's': '#a6a6a6', 'o': '#222222'}
        for r, row in enumerate(bone_pattern):
            for c, ch in enumerate(row):
                if ch in color_map:
                    self._px(ox+c*ps, oy+r*ps, color_map[ch], ps, tag="dashboard_bone")

    def draw_pixel_sun(self, cx, cy):
        ps, sun = 6, [" xxxxx ", "xxxxxxx", "xxxxxxx", "xxxxxxx", " xxxxx "]
        sx, sy = cx - (len(sun[0])*ps)//2, cy - (len(sun)*ps)//2
        for r, row in enumerate(sun):
            for c, ch in enumerate(row):
                if ch == "x": self._px(sx+c*ps, sy+r*ps, "#FFD700", ps)

    def draw_pixel_full_moon(self, cx, cy):
        ps, moon = 6, ["  xxxxxx  ", " xxxxxxxx ", "xxxxxxxxxx", "xxOxxxxxxx", "xxxxxxxOxx", "xxxxOxxxxx", "xxxxxxxxxx", " xxxxxxxx ", "  xxxxxx  "]
        sx, sy = cx - (len(moon[0])*ps)//2, cy - (len(moon)*ps)//2
        for r, row in enumerate(moon):
            for c, ch in enumerate(row):
                if ch == "x": self._px(sx+c*ps, sy+r*ps, "#fffde7", ps)
                elif ch == "O": self._px(sx+c*ps, sy+r*ps, "#d4d4b8", ps)

    def draw_pixel_cloud(self, ox, oy, tag="sky", is_dark=False):
        ps, cloud = 8, ["   xxxxxx   ", "  xxxxxxxx  ", " xxxxxxxxxx ", "xxxxxxxxxxxx", "xxxxxxxxxxxx", " xxxxxxxxxx "]
        for r, row in enumerate(cloud):
            for c, ch in enumerate(row):
                if ch == "x": self._px(ox+c*ps, oy+r*ps, ("#7788aa" if is_dark else "#ffffff") if r < 4 else ("#556677" if is_dark else "#dde8f0"), ps, tag=tag)

    def draw_pixel_bowl(self, ox, oy):
        ps = 8 
        bowl_rows = ["dddddddddddddddddd", "rdrrrrrrrrrrrrrrrr", "rrwwrrrrrrrrrrrrrr", "rrwwrrrrrrrrrrrrrr", "rrrrrrrrrrrrrrrrrr", " rrrrrrrrrrrrrrrr ", "  rrrrrrrrrrrrrr  ", "   dddddddddddd   "]
        for (kx, ky, col) in [(4, -1, "#b87333"), (7, -2, "#cd853f"), (10, -2, "#8b4513"), (13, -1, "#b87333"), (6, -1, "#cd853f"), (11, -1, "#8b4513")]:
            self.canvas.create_oval(ox+kx*ps, oy+ky*ps, ox+(kx+1)*ps+2, oy+(ky+1)*ps+2, fill=col, outline="#5c3a21", width=2, tags="bowl")

        for r, row in enumerate(bowl_rows):
            for c, ch in enumerate(row):
                if ch == 'r': col = "#ff2a2a" 
                elif ch == 'd': col = "#990000"
                elif ch == 'w': col = "#ffffff"
                else: continue
                self._px(ox+c*ps, oy+r*ps, col, ps, tag="bowl")
        
        self.canvas.create_text(ox + (9 * ps), oy + (4 * ps), text="mickey :>", font=("Courier", 10, "bold"), fill="white", tags="bowl")

    # Weather
    def environment_engine_loop(self):
        self.canvas.delete("sky_back", "sky_front", "weather_fx", "dashboard_bone")
        now = time.localtime()
        current_decimal_time = now.tm_hour + now.tm_min / 60.0
        
        if self.pomodoro_active:
            rem = int(self.pomodoro_end_time - time.time())
            if rem <= 0:
                self.pomodoro_active = False
                self.show_bowl_message("POMODORO COMPLETE!\nTake a 5 min break. 🔔")
            else:
                self.clock_label.config(text=f"WORK: {rem//60:02d}:{rem%60:02d}", fg="#cc00ff")
        else:
            self.clock_label.config(text=time.strftime("%I:%M %p", now), fg="#ff3333")

        # 15 min timer
        elapsed = time.time() - self.last_break_time
        if elapsed >= self.max_focus_time:
            if not self.needs_break:
                self.needs_break = True
                self.show_bowl_message("[ BURNOUT DETECTED ]\nTake a break, then click\n[BREAK DONE] below!", 8000)
                self.break_btn.place(x=self.WIN_W//2 - 75, y=self.WIN_H - 200)
                
            
            self.current_state = "sad"
            self.break_btn.lift()

        # Mickey's sleepy/wake up time
        is_night = current_decimal_time >= 23.0 or current_decimal_time < self.sunrise_hour
        
        if is_night and not self.night_sleep_triggered:
            self.night_sleep_triggered = True
            self.morning_wake_triggered = False 
            if self.current_state != "sleepy" and not self.pomodoro_active and not self.needs_break:
                self.current_state = "sleepy"
                self.show_bowl_message("It's late! I'm going to sleep.\nYou should rest too! Zzz 😴", 6000)
                p = self.canvas.create_text(self.WIN_W//2 + 20, self.WIN_H//2 - 50, text="Zzz", fill="#88ccff", font=("Courier", 16, "bold"), tags="particle")
                self.animate_float(p, 20, -2)

        elif not is_night and not self.morning_wake_triggered:
            self.morning_wake_triggered = True
            self.night_sleep_triggered = False 
            if self.current_state == "sleepy" and not self.needs_break:
                self.current_state = "happy"
                self.show_bowl_message("Good morning! The sun is up! ☀️", 5000)
                p = self.canvas.create_text(self.WIN_W//2, self.WIN_H//2 - 50, text="☀️", font=("Arial", 18), tags="particle")
                self.animate_float(p, 15, -3)
                if self.pet_timer: self.root.after_cancel(self.pet_timer)
                self.pet_timer = self.root.after(3000, self.revert_to_idle)

        # Environment Rendering
        is_daytime = self.sunrise_hour <= current_decimal_time < self.sunset_hour

        if self.pomodoro_active:
            self.canvas.config(bg="#2b0033")
            self.draw_pixel_sun(40, 35) 
        else:
            self.canvas.config(bg=self.trans_color)
            if self.current_weather in ["sunny", "windy"]:
                self.draw_pixel_sun(40, 35) if is_daytime else self.draw_pixel_full_moon(40, 35)

        self.cloud_offset += self.wind_speed
        canvas_w, cloud_w = self.WIN_W, 96 
        
        is_dark = self.current_weather in ["cloudy", "rainy", "snowy"]
        cloud_count = 6 if is_dark else 2

        for i in range(cloud_count):
            x = (self.cloud_offset * (0.45 + (i*0.1)) + (i * 120)) % (canvas_w + cloud_w) - cloud_w
            self.draw_pixel_cloud(int(x), 20 + (i*20), tag="sky_back", is_dark=is_dark)

        if self.current_weather == "rainy" and not self.pomodoro_active:
            for _ in range(18): 
                rx, ry = random.randint(0, self.WIN_W), random.randint(0, int(self.WIN_H * 0.6))
                self.canvas.create_line(rx, ry, rx-8, ry+20, fill="#66aaff", width=2, tags="weather_fx")
        elif self.current_weather == "snowy" and not self.pomodoro_active:
            for _ in range(25): 
                rx, ry = random.randint(0, self.WIN_W), random.randint(0, int(self.WIN_H * 0.6))
                self.canvas.create_oval(rx, ry, rx+5, ry+5, fill="white", outline="#dddddd", tags="weather_fx")

        self.canvas.delete("bowl")
        self.draw_pixel_bowl(*self._bowl_origin())
        
        self.bone_float_y += self.bone_float_dir
        if self.bone_float_y > 4 or self.bone_float_y < -4: self.bone_float_dir *= -1
        bone_x = self.WIN_W // 2 - 28
        bone_y = self.WIN_H - 45 + int(self.bone_float_y)
        self.draw_pixel_bone(bone_x, bone_y)
        
        if self.dog_canvas_image is not None: self.canvas.tag_raise("dog")

        self.canvas.delete("sky_front")
        for i in range(1 if not is_dark else 3):
            x = (self.cloud_offset * 0.65 + (i * 150) + 280) % (canvas_w + cloud_w) - cloud_w
            self.draw_pixel_cloud(int(x), 40 + (i*10), tag="sky_front", is_dark=is_dark)

        for tag in ["weather_fx", "bowl", "dashboard_bone", "bowlmsg", "particle"]: self.canvas.tag_raise(tag)
        self.root.after(60, self.environment_engine_loop)

    def update_dog_animation(self):
        frames = self.dog_states[self.current_state]
        fname  = frames[self.dog_frame_index % len(frames)]
        self.canvas.delete("dog")

        dog_top, dog_h = 40, self.WIN_H - 180
        if fname in self._image_cache:
            self.dog_canvas_image = self.canvas.create_image(0, dog_top, anchor="nw", image=self._image_cache[fname], tags="dog")
        else:
            self.dog_canvas_image = self.canvas.create_rectangle(0, dog_top, self.WIN_W, dog_top + dog_h, fill="#ffcc88", outline="#885500", width=2, tags="dog")
            self.canvas.create_text(self.WIN_W//2, dog_top + dog_h//2, text="🐕", font=("Arial", 60), tags="dog")

        self.canvas.tag_bind("dog", "<Motion>", self.pet_dog)
        self.dog_frame_index += 1
        self.root.after(500, self.update_dog_animation)

if __name__ == "__main__":
    root = tk.Tk()
    app = MickeyCyberdeck(root)
    root.mainloop()
