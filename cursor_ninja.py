# -*- coding: utf-8 -*-
"""
Cursor Ninja — Fruit Ninja прямо на твоєму робочому столі.

Фрукти вилітають знизу вгору по дузі. Ти РОЗРІЗАЄШ їх, швидко проводячи
МИШКОЮ крізь них (курсор = лезо). За кожен фрукт — очки.
Пропустив фрукт (впав униз) — мінус життя. Розрізав БОМБУ 💣 — мінус життя.
Три життя. Коли закінчаться — екран кінця гри.

Працює як прозорий оверлей поверх усіх вікон. Позиція мишки читається
глобально (через Windows API), тому різати можна будь-де на екрані.

Керування:
    Просто ВОДИ МИШКОЮ швидко крізь фрукти.
    R або ENTER — почати заново (після програшу)
    ESC         — вийти

Потрібен лише вбудований tkinter + ctypes. Windows.
"""

import tkinter as tk
import ctypes
import random
import math
import time

TICK_MS = 22
TRANSPARENT = "gray1"
GRAVITY = 0.38
MIN_BLADE_SPEED = 14      # мін. швидкість руху мишки, щоб різати (px/тік)
START_LIVES = 3

VK_ESC, VK_R, VK_ENTER = 0x1B, 0x52, 0x0D

FRUITS = [
    ("#E8412F", "#F98A80"),   # яблуко
    ("#FB8C00", "#FFC078"),   # апельсин
    ("#FDD835", "#FFF176"),   # лимон
    ("#7CB342", "#AED581"),   # лайм
    ("#8E24AA", "#CE93D8"),   # виноград
    ("#EC407A", "#F8BBD0"),   # кавун-рожевий
]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def cursor_pos():
    p = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def is_down(vk):
    return (ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000) != 0


def seg_dist(px, py, ax, ay, bx, by):
    """Відстань від точки (px,py) до відрізка (a)-(b)."""
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


class CursorNinja:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cursor Ninja")
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.sw}x{self.sh}+0+0")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", TRANSPARENT)

        self.canvas = tk.Canvas(self.root, width=self.sw, height=self.sh,
                                bg=TRANSPARENT, highlightthickness=0)
        self.canvas.pack()

        self.mx, self.my = cursor_pos()
        self.trail = []
        self.reset()
        self.loop()

    def reset(self):
        self.objects = []       # фрукти й бомби
        self.particles = []     # бризки
        self.popups = []        # спливаючі очки
        self.score = 0
        self.lives = START_LIVES
        self.best_combo = 0
        self.combo = 0
        self.combo_time = 0
        self.spawn_timer = 0
        self.alive = True

    # ---------- створення об'єктів ----------
    def spawn_wave(self):
        n = random.randint(1, 3)
        for _ in range(n):
            is_bomb = random.random() < 0.16
            x = random.randint(int(self.sw * 0.1), int(self.sw * 0.9))
            vx = random.uniform(-5, 5)
            vy = -random.uniform(19, 24)
            r = random.randint(30, 42)
            if is_bomb:
                colors = ("#222831", "#4b4f57")
            else:
                colors = random.choice(FRUITS)
            self.objects.append({
                "x": float(x), "y": float(self.sh + 40),
                "vx": vx, "vy": vy, "r": r,
                "bomb": is_bomb, "col": colors[0], "col2": colors[1],
                "spin": random.uniform(-6, 6), "ang": 0.0, "sliced": False,
            })

    def spawn_particles(self, x, y, color, n=12):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            sp = random.uniform(2, 7)
            self.particles.append({
                "x": x, "y": y, "vx": math.cos(a) * sp, "vy": math.sin(a) * sp,
                "life": 1.0, "col": color,
            })

    # ---------- оновлення ----------
    def update(self):
        # мишка + лезо
        px, py = self.mx, self.my
        self.mx, self.my = cursor_pos()
        blade_len = math.hypot(self.mx - px, self.my - py)
        self.trail.append((self.mx, self.my))
        if len(self.trail) > 10:
            self.trail.pop(0)

        # спавн хвиль
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_wave()
            self.spawn_timer = random.randint(28, 55)

        # об'єкти (фізика + різання)
        for o in self.objects:
            o["vy"] += GRAVITY
            o["x"] += o["vx"]
            o["y"] += o["vy"]
            o["ang"] += o["spin"]

            if not o["sliced"] and blade_len >= MIN_BLADE_SPEED:
                d = seg_dist(o["x"], o["y"], px, py, self.mx, self.my)
                if d <= o["r"] + 6:
                    self.slice_object(o)

        # прибирання + пропущені фрукти
        still = []
        for o in self.objects:
            if o["sliced"]:
                continue
            if o["y"] > self.sh + 60 and o["vy"] > 0:
                if not o["bomb"]:            # пропустив фрукт
                    self.lives -= 1
                    self.combo = 0
                    if self.lives <= 0:
                        self.alive = False
                continue
            still.append(o)
        self.objects = still

        # частинки
        for p in self.particles:
            p["vy"] += 0.25
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 0.03
        self.particles = [p for p in self.particles if p["life"] > 0]

        # спливаючі очки
        for u in self.popups:
            u["y"] -= 1.2
            u["life"] -= 0.02
        self.popups = [u for u in self.popups if u["life"] > 0]

        # комбо згасає
        if self.combo and time.time() - self.combo_time > 1.1:
            self.combo = 0

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
        gain = 1 + (self.combo - 1)          # комбо дає більше очок
        self.score += gain
        self.spawn_particles(o["x"], o["y"], o["col"], 14)
        self.spawn_particles(o["x"], o["y"], o["col2"], 8)
        self.popups.append({"x": o["x"], "y": o["y"],
                            "txt": f"+{gain}" + ("  x" + str(self.combo) if self.combo > 1 else ""),
                            "life": 1.0})

    # ---------- малювання ----------
    def draw(self):
        c = self.canvas
        c.delete("all")

        # фрукти / бомби
        for o in self.objects:
            x, y, r = o["x"], o["y"], o["r"]
            if o["bomb"]:
                c.create_oval(x - r, y - r, x + r, y + r, fill=o["col"], outline="#111", width=2)
                # ґніт + іскра
                c.create_line(x, y - r, x + 10, y - r - 16, width=3, fill="#8d6e63")
                c.create_text(x + 12, y - r - 20, text="✦", fill="#FFB300",
                              font=("Segoe UI Emoji", 16, "bold"))
                c.create_text(x, y, text="💣", font=("Segoe UI Emoji", int(r), "bold"))
            else:
                c.create_oval(x - r, y - r, x + r, y + r, fill=o["col"], outline="")
                c.create_oval(x - r + 5, y - r + 5, x + r - 5, y + r - 5,
                              outline=o["col2"], width=3)
                # блиск
                c.create_oval(x - r * 0.5, y - r * 0.55, x - r * 0.15, y - r * 0.2,
                              fill="#ffffff", outline="")

        # частинки (бризки соку)
        for p in self.particles:
            s = 4 * p["life"] + 1
            c.create_oval(p["x"] - s, p["y"] - s, p["x"] + s, p["y"] + s,
                          fill=p["col"], outline="")

        # спливаючі очки
        for u in self.popups:
            c.create_text(u["x"], u["y"], text=u["txt"], fill="#FFFFFF",
                          font=("Consolas", 20, "bold"))

        # лезо (слід мишки)
        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                x1, y1 = self.trail[i - 1]
                x2, y2 = self.trail[i]
                w = max(1, int(i * 0.9))
                c.create_line(x1, y1, x2, y2, width=w, fill="#8EF6FF",
                              capstyle="round")

        # HUD
        self.draw_hud()

        if not self.alive:
            self.draw_gameover()

    def draw_hud(self):
        c = self.canvas
        c.create_text(30, 24, text=f"🍉 CURSOR NINJA", anchor="w",
                      fill="#8EF6FF", font=("Consolas", 20, "bold"))
        c.create_text(30, 58, text=f"Очки: {self.score}", anchor="w",
                      fill="#FFFFFF", font=("Consolas", 18, "bold"))
        if self.combo > 1:
            c.create_text(30, 88, text=f"Комбо x{self.combo}!", anchor="w",
                          fill="#FFD54F", font=("Consolas", 16, "bold"))
        # життя
        hearts = "❤ " * self.lives + "· " * (START_LIVES - self.lives)
        c.create_text(self.sw - 30, 30, text=hearts.strip(), anchor="e",
                      fill="#FF5C7A", font=("Segoe UI Emoji", 22, "bold"))
        c.create_text(self.sw - 30, 62, text="ESC — вихід", anchor="e",
                      fill="#9aa0a6", font=("Consolas", 12))

    def draw_gameover(self):
        c = self.canvas
        cx, cy = self.sw // 2, self.sh // 2
        c.create_rectangle(cx - 260, cy - 130, cx + 260, cy + 130,
                           fill="#0d1117", outline="#8EF6FF", width=3)
        c.create_text(cx, cy - 80, text="ГРА ЗАКІНЧЕНА", fill="#FF5C7A",
                      font=("Consolas", 30, "bold"))
        c.create_text(cx, cy - 25, text=f"Очки: {self.score}", fill="#FFFFFF",
                      font=("Consolas", 22, "bold"))
        c.create_text(cx, cy + 15, text=f"Найкраще комбо: x{self.best_combo}",
                      fill="#FFD54F", font=("Consolas", 16, "bold"))
        c.create_text(cx, cy + 70, text="R або ENTER — заново    ESC — вихід",
                      fill="#9aa0a6", font=("Consolas", 14))

    # ---------- цикл ----------
    def loop(self):
        # Раніше тут була ще й VK_Q — оверлей читає клавіші ГЛОБАЛЬНО
        # (GetAsyncKeyState, не фокус вікна, бо гра має ловити мишку по
        # всьому екрану, навіть коли курсор над іншим вікном). Це означало,
        # що звичайне набирання літери "q" в БУДЬ-ЯКОМУ іншому застосунку —
        # чат, документ — миттєво й без попередження закривало гру. ESC —
        # набагато безпечніший вибір для глобальної гарячої клавіші: його
        # рідко тиснуть випадково під час звичайного набору тексту.
        if is_down(VK_ESC):
            self.root.destroy()
            return
        try:
            if not self.root.winfo_exists():
                return
        except tk.TclError:
            return

        if self.alive:
            self.update()
        else:
            # оновлюємо позицію мишки, щоб не було стрибка після рестарту
            self.mx, self.my = cursor_pos()
            if is_down(VK_R) or is_down(VK_ENTER):
                self.reset()

        self.draw()
        self.root.after(TICK_MS, self.loop)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    CursorNinja().run()
