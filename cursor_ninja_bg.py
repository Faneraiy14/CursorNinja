# -*- coding: utf-8 -*-
"""
Cursor Ninja (версія з фоном) — Fruit Ninja у власному вікні.

Красивий фон: нічне небо ніндзя-стилю (зорі, місяць, гори). Фрукти
вилітають знизу вгору по дузі — розрізай їх, швидко проводячи мишкою.
Бомби 💣 не чіпай. Три життя.

Це віконна версія (не оверлей), тому її зручно скомпілювати в .exe
і надіслати другу — запуститься без установки Python.

Керування:
    Води мишкою крізь фрукти — ріж їх.
    R / ENTER — почати заново (після програшу)
    ESC       — вийти

Потрібен лише вбудований tkinter (для .exe нічого не треба).
"""

import tkinter as tk
import random
import math
import time

WIN_W, WIN_H = 1000, 680
TICK_MS = 20
GRAVITY = 0.34
MIN_BLADE_SPEED = 12
START_LIVES = 3

FRUITS = [
    ("#E8412F", "#F98A80"),   # яблуко
    ("#FB8C00", "#FFC078"),   # апельсин
    ("#FDD835", "#FFF176"),   # лимон
    ("#7CB342", "#AED581"),   # лайм
    ("#8E24AA", "#CE93D8"),   # виноград
    ("#EC407A", "#F8BBD0"),   # кавун
]


def lerp_color(c1, c2, t):
    a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
    r = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return f"#{r[0]:02x}{r[1]:02x}{r[2]:02x}"


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class CursorNinja:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cursor Ninja 🥷🍉")
        self.root.resizable(False, False)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - WIN_W) // 2
        y = (sh - WIN_H) // 2
        self.root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

        self.canvas = tk.Canvas(self.root, width=WIN_W, height=WIN_H,
                                highlightthickness=0, cursor="none")
        self.canvas.pack()

        self.draw_background()   # статичний фон (малюється один раз)

        # мишка
        self.mx, self.my = WIN_W // 2, WIN_H // 2
        self.pmx, self.pmy = self.mx, self.my
        self.canvas.bind("<Motion>", self.on_motion)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Key>", self.on_key)
        self.root.focus_force()

        self.trail = []
        self.reset()
        self.loop()

    # ---------- фон (малюється один раз) ----------
    def draw_background(self):
        c = self.canvas
        # градієнт неба
        top, bottom = "#0b1026", "#2a1330"
        step = 3
        for yy in range(0, WIN_H, step):
            col = lerp_color(top, bottom, yy / WIN_H)
            c.create_rectangle(0, yy, WIN_W, yy + step, fill=col, outline="")

        # зорі
        random.seed(7)
        for _ in range(90):
            sx = random.randint(0, WIN_W)
            sy = random.randint(0, int(WIN_H * 0.72))
            r = random.choice([1, 1, 1, 2])
            bright = random.choice(["#ffffff", "#e0e6ff", "#cfd8ff"])
            c.create_oval(sx - r, sy - r, sx + r, sy + r, fill=bright, outline="")
        random.seed()

        # місяць з сяйвом
        mx, my = WIN_W - 150, 120
        for i, gr in enumerate([70, 56, 44]):
            glow = ["#3a3550", "#4a4468", "#5a5480"][i]
            c.create_oval(mx - gr, my - gr, mx + gr, my + gr, fill=glow, outline="")
        c.create_oval(mx - 40, my - 40, mx + 40, my + 40, fill="#f4f0d0", outline="")
        c.create_oval(mx - 18, my - 30, mx + 30, my + 26, fill="#e8e2be", outline="")

        # гори (силуети)
        c.create_polygon(0, WIN_H, 0, WIN_H - 170, 190, WIN_H - 40,
                        360, WIN_H - 210, 560, WIN_H - 30, WIN_H, WIN_H,
                        fill="#0a0a16", outline="")
        c.create_polygon(WIN_W, WIN_H, WIN_W, WIN_H - 150, WIN_W - 260, WIN_H - 30,
                        WIN_W - 480, WIN_H - 190, WIN_W - 700, WIN_H - 20,
                        fill="#12071c", outline="")

    # ---------- ввід ----------
    def on_motion(self, e):
        self.mx, self.my = e.x, e.y

    def on_key(self, e):
        if not self.alive and e.keysym in ("r", "R", "Return"):
            self.reset()

    # ---------- логіка ----------
    def reset(self):
        self.objects = []
        self.particles = []
        self.popups = []
        self.score = 0
        self.lives = START_LIVES
        self.combo = 0
        self.combo_time = 0
        self.best_combo = 0
        self.spawn_timer = 0
        self.alive = True

    def spawn_wave(self):
        for _ in range(random.randint(1, 3)):
            is_bomb = random.random() < 0.16
            x = random.randint(int(WIN_W * 0.1), int(WIN_W * 0.9))
            colors = ("#222831", "#4b4f57") if is_bomb else random.choice(FRUITS)
            self.objects.append({
                "x": float(x), "y": float(WIN_H + 40),
                "vx": random.uniform(-4, 4), "vy": -random.uniform(16, 20),
                "r": random.randint(26, 38), "bomb": is_bomb,
                "col": colors[0], "col2": colors[1], "sliced": False,
            })

    def spawn_particles(self, x, y, color, n=12):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            sp = random.uniform(2, 7)
            self.particles.append({"x": x, "y": y, "vx": math.cos(a) * sp,
                                   "vy": math.sin(a) * sp, "life": 1.0, "col": color})

    def update(self):
        px, py = self.pmx, self.pmy
        blade = math.hypot(self.mx - px, self.my - py)
        self.trail.append((self.mx, self.my))
        if len(self.trail) > 10:
            self.trail.pop(0)

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_wave()
            self.spawn_timer = random.randint(26, 50)

        for o in self.objects:
            o["vy"] += GRAVITY
            o["x"] += o["vx"]
            o["y"] += o["vy"]
            if not o["sliced"] and blade >= MIN_BLADE_SPEED:
                if seg_dist(o["x"], o["y"], px, py, self.mx, self.my) <= o["r"] + 6:
                    self.slice_object(o)

        still = []
        for o in self.objects:
            if o["sliced"]:
                continue
            if o["y"] > WIN_H + 60 and o["vy"] > 0:
                if not o["bomb"]:
                    self.lives -= 1
                    self.combo = 0
                    if self.lives <= 0:
                        self.alive = False
                continue
            still.append(o)
        self.objects = still

        for p in self.particles:
            p["vy"] += 0.25
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 0.03
        self.particles = [p for p in self.particles if p["life"] > 0]

        for u in self.popups:
            u["y"] -= 1.2
            u["life"] -= 0.02
        self.popups = [u for u in self.popups if u["life"] > 0]

        if self.combo and time.time() - self.combo_time > 1.1:
            self.combo = 0

        self.pmx, self.pmy = self.mx, self.my

    def slice_object(self, o):
        o["sliced"] = True
        if o["bomb"]:
            self.lives -= 1
            self.combo = 0
            self.spawn_particles(o["x"], o["y"], "#FF5252", 22)
            self.spawn_particles(o["x"], o["y"], "#FFCA28", 14)
            if self.lives <= 0:
                self.alive = False
            return
        self.combo += 1
        self.combo_time = time.time()
        self.best_combo = max(self.best_combo, self.combo)
        gain = 1 + (self.combo - 1)
        self.score += gain
        self.spawn_particles(o["x"], o["y"], o["col"], 14)
        self.spawn_particles(o["x"], o["y"], o["col2"], 8)
        self.popups.append({"x": o["x"], "y": o["y"],
                            "txt": f"+{gain}" + (f"  x{self.combo}" if self.combo > 1 else ""),
                            "life": 1.0})

    # ---------- малювання (динаміка) ----------
    def draw(self):
        c = self.canvas
        c.delete("dyn")

        for o in self.objects:
            x, y, r = o["x"], o["y"], o["r"]
            if o["bomb"]:
                c.create_oval(x - r, y - r, x + r, y + r, fill=o["col"],
                              outline="#111", width=2, tags="dyn")
                c.create_line(x, y - r, x + 10, y - r - 16, width=3,
                              fill="#8d6e63", tags="dyn")
                c.create_text(x + 12, y - r - 20, text="✦", fill="#FFB300",
                              font=("Segoe UI Emoji", 16, "bold"), tags="dyn")
                c.create_text(x, y, text="💣", font=("Segoe UI Emoji", int(r)),
                              tags="dyn")
            else:
                c.create_oval(x - r, y - r, x + r, y + r, fill=o["col"],
                              outline="", tags="dyn")
                c.create_oval(x - r + 5, y - r + 5, x + r - 5, y + r - 5,
                              outline=o["col2"], width=3, tags="dyn")
                c.create_oval(x - r * 0.5, y - r * 0.55, x - r * 0.15, y - r * 0.2,
                              fill="#ffffff", outline="", tags="dyn")

        for p in self.particles:
            s = 4 * p["life"] + 1
            c.create_oval(p["x"] - s, p["y"] - s, p["x"] + s, p["y"] + s,
                          fill=p["col"], outline="", tags="dyn")

        for u in self.popups:
            c.create_text(u["x"], u["y"], text=u["txt"], fill="#FFFFFF",
                          font=("Consolas", 20, "bold"), tags="dyn")

        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                x1, y1 = self.trail[i - 1]
                x2, y2 = self.trail[i]
                c.create_line(x1, y1, x2, y2, width=max(1, int(i * 0.9)),
                              fill="#8EF6FF", capstyle="round", tags="dyn")
        # вістря леза
        c.create_oval(self.mx - 5, self.my - 5, self.mx + 5, self.my + 5,
                      fill="#CFFAFF", outline="", tags="dyn")

        self.draw_hud()
        if not self.alive:
            self.draw_gameover()

    def draw_hud(self):
        c = self.canvas
        c.create_text(24, 22, text="🍉 CURSOR NINJA", anchor="w", fill="#8EF6FF",
                      font=("Consolas", 20, "bold"), tags="dyn")
        c.create_text(24, 54, text=f"Очки: {self.score}", anchor="w", fill="#FFFFFF",
                      font=("Consolas", 18, "bold"), tags="dyn")
        if self.combo > 1:
            c.create_text(24, 84, text=f"Комбо x{self.combo}!", anchor="w",
                          fill="#FFD54F", font=("Consolas", 16, "bold"), tags="dyn")
        hearts = "❤ " * self.lives + "· " * (START_LIVES - self.lives)
        c.create_text(WIN_W - 24, 26, text=hearts.strip(), anchor="e", fill="#FF5C7A",
                      font=("Segoe UI Emoji", 20, "bold"), tags="dyn")

    def draw_gameover(self):
        c = self.canvas
        cx, cy = WIN_W // 2, WIN_H // 2
        c.create_rectangle(cx - 250, cy - 120, cx + 250, cy + 120,
                           fill="#0d1117", outline="#8EF6FF", width=3, tags="dyn")
        c.create_text(cx, cy - 70, text="ГРА ЗАКІНЧЕНА", fill="#FF5C7A",
                      font=("Consolas", 28, "bold"), tags="dyn")
        c.create_text(cx, cy - 20, text=f"Очки: {self.score}", fill="#FFFFFF",
                      font=("Consolas", 22, "bold"), tags="dyn")
        c.create_text(cx, cy + 18, text=f"Найкраще комбо: x{self.best_combo}",
                      fill="#FFD54F", font=("Consolas", 16, "bold"), tags="dyn")
        c.create_text(cx, cy + 68, text="R / ENTER — заново    ESC — вихід",
                      fill="#9aa0a6", font=("Consolas", 14), tags="dyn")

    def loop(self):
        try:
            if not self.root.winfo_exists():
                return
        except tk.TclError:
            return
        if self.alive:
            self.update()
        else:
            self.pmx, self.pmy = self.mx, self.my
        self.draw()
        self.root.after(TICK_MS, self.loop)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    CursorNinja().run()
