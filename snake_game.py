import pygame
import random
import sys
import json
import os
import math
import array

# ── Init ──────────────────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

# ── Constants ─────────────────────────────────────────────────────────────────
CELL   = 20
COLS   = 30
ROWS   = 25
WIDTH  = COLS * CELL
HEIGHT = ROWS * CELL + 80

# Directions
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)

SCORE_FILE = "highscore.json"

# ── Difficulty levels ─────────────────────────────────────────────────────────
LEVELS = [
    (  0, "EASY",    8, (80,  220, 120)),
    ( 50, "MEDIUM", 12, (220, 200,  60)),
    (120, "HARD",   17, (255, 140,  40)),
    (220, "INSANE", 24, (255,  60,  60)),
    (350, "GODLIKE",32, (200,  80, 255)),
]

def get_level(score):
    lvl = LEVELS[0]
    for entry in LEVELS:
        if score >= entry[0]:
            lvl = entry
    return lvl

# ── Snake colour themes per level ─────────────────────────────────────────────
# Each theme: (head_colour, body_colour)
SNAKE_THEMES = [
    ((80,  255, 160), (40,  200, 100)),   # EASY    — green
    ((80,  200, 255), (40,  140, 220)),   # MEDIUM  — blue
    ((255, 220,  60), (200, 160,  20)),   # HARD    — yellow
    ((255, 100,  60), (200,  50,  20)),   # INSANE  — orange-red
    ((220,  80, 255), (160,  30, 220)),   # GODLIKE — purple
]

def get_snake_colors(score):
    idx = LEVELS.index(get_level(score))
    return SNAKE_THEMES[idx]

# ── Sound helpers ─────────────────────────────────────────────────────────────
def make_sound(freq=440, duration=0.08, volume=0.4, wave="square", decay=True):
    sample_rate = 44100
    n           = int(sample_rate * duration)
    buf         = []
    for i in range(n):
        t   = i / sample_rate
        if wave == "square":
            v = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        elif wave == "sine":
            v = math.sin(2 * math.pi * freq * t)
        elif wave == "noise":
            v = random.uniform(-1, 1)
        else:
            v = math.sin(2 * math.pi * freq * t)
        env = (1 - i / n) if decay else 1.0
        buf.append(int(v * env * volume * 32767))
    raw = array.array("h", buf).tobytes()
    return pygame.mixer.Sound(buffer=raw)

SND_EAT       = make_sound(660,  0.07, 0.5, "square")
SND_LEVELUP   = make_sound(880,  0.18, 0.4, "sine",  decay=False)
SND_DIE       = make_sound(120,  0.35, 0.5, "noise")
SND_HIGHSCORE = make_sound(1046, 0.25, 0.4, "sine",  decay=False)

# ── High score ────────────────────────────────────────────────────────────────
def load_highscore():
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE, "r") as f:
            return json.load(f).get("highscore", 0)
    return 0

def save_highscore(score):
    with open(SCORE_FILE, "w") as f:
        json.dump({"highscore": score}, f)

# ── Particle system ───────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color, vx, vy, life=30, size=4):
        self.x, self.y   = float(x), float(y)
        self.color       = color
        self.vx, self.vy = vx, vy
        self.life        = life
        self.max_life    = life
        self.size        = size

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.vy   += 0.15        # gravity
        self.vx   *= 0.95        # friction
        self.life -= 1

    def draw(self, surf):
        alpha  = max(0, int(255 * self.life / self.max_life))
        radius = max(1, int(self.size * self.life / self.max_life))
        r, g, b = self.color
        color  = (r, g, b)
        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), radius)

    @property
    def alive(self):
        return self.life > 0


def spawn_eat_particles(particles, food_pos, color):
    """Sparkle burst when food is eaten."""
    cx = food_pos[0] * CELL + CELL // 2
    cy = food_pos[1] * CELL + CELL // 2
    for _ in range(18):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.5, 4.5)
        vx    = math.cos(angle) * speed
        vy    = math.sin(angle) * speed
        col   = random.choice([color, (255, 255, 200), (255, 180, 80)])
        particles.append(Particle(cx, cy, col, vx, vy,
                                  life=random.randint(20, 35),
                                  size=random.randint(2, 5)))


def spawn_death_particles(particles, snake):
    """Explosion along the whole snake body."""
    for (c, r) in snake:
        cx = c * CELL + CELL // 2
        cy = r * CELL + CELL // 2
        for _ in range(6):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.0, 5.0)
            vx    = math.cos(angle) * speed
            vy    = math.sin(angle) * speed
            col   = random.choice([(255, 80, 80), (255, 160, 40),
                                   (255, 220, 60), (200, 200, 200)])
            particles.append(Particle(cx, cy, col, vx, vy,
                                      life=random.randint(25, 55),
                                      size=random.randint(2, 6)))


# ── Helpers ───────────────────────────────────────────────────────────────────
def draw_cell(surf, col, row, color, radius=4):
    rect = pygame.Rect(col * CELL + 1, row * CELL + 1, CELL - 2, CELL - 2)
    pygame.draw.rect(surf, color, rect, border_radius=radius)

def random_food(snake):
    while True:
        pos = (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
        if pos not in snake:
            return pos

# ── Game ──────────────────────────────────────────────────────────────────────
class SnakeGame:
    def __init__(self):
        self.screen    = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("🐍  Snake")
        self.clock     = pygame.time.Clock()
        self.font_lg   = pygame.font.SysFont("Consolas", 36, bold=True)
        self.font_md   = pygame.font.SysFont("Consolas", 22, bold=True)
        self.font_sm   = pygame.font.SysFont("Consolas", 18)
        self.font_xs   = pygame.font.SysFont("Consolas", 14)
        self.highscore = load_highscore()
        self.tick      = 0       # global frame counter for animations
        self.reset()

    def reset(self):
        mid              = (COLS // 2, ROWS // 2)
        self.snake       = [mid, (mid[0]-1, mid[1]), (mid[0]-2, mid[1])]
        self.dir         = RIGHT
        self.next        = RIGHT
        self.food        = random_food(self.snake)
        self.score       = 0
        self.alive       = True
        self.new_hs      = False
        self.cur_lvl_idx = 0
        self.particles   = []
        self.death_done  = False   # explosion spawned only once

    # ── Drawing ───────────────────────────────────────────────────────────────
    def draw_grid(self):
        for c in range(COLS):
            for r in range(ROWS):
                pygame.draw.rect(self.screen, (20, 24, 40),
                                 pygame.Rect(c*CELL, r*CELL, CELL, CELL), 1)

    def draw_snake(self):
        head_col, body_col = get_snake_colors(self.score)

        # Smooth colour transition: interpolate toward new theme
        for i, (c, r) in enumerate(self.snake):
            # Slightly darken body segments toward the tail
            factor = 1 - (i / max(len(self.snake), 1)) * 0.45
            if i == 0:
                color = head_col
            else:
                color = (int(body_col[0] * factor),
                         int(body_col[1] * factor),
                         int(body_col[2] * factor))
            draw_cell(self.screen, c, r, color)

        # Eyes on head
        if self.snake:
            c, r  = self.snake[0]
            ex    = c * CELL + CELL // 2
            ey    = r * CELL + CELL // 2
            pygame.draw.circle(self.screen, (10, 20, 10), (ex - 4, ey - 3), 2)
            pygame.draw.circle(self.screen, (10, 20, 10), (ex + 4, ey - 3), 2)

    def draw_food(self):
        c, r  = self.food
        cx    = c * CELL + CELL // 2
        cy    = r * CELL + CELL // 2

        # Pulsing size
        pulse = 1 + 0.18 * math.sin(self.tick * 0.15)
        radius = int((CELL // 2 - 2) * pulse)

        pygame.draw.circle(self.screen, (255, 80, 80), (cx, cy), radius)
        pygame.draw.circle(self.screen, (255, 180, 180), (cx - 3, cy - 3), 3)

        # Rotating sparkle lines
        for i in range(4):
            angle = self.tick * 0.08 + i * math.pi / 2
            x1    = cx + int(math.cos(angle) * (radius + 2))
            y1    = cy + int(math.sin(angle) * (radius + 2))
            x2    = cx + int(math.cos(angle) * (radius + 6))
            y2    = cy + int(math.sin(angle) * (radius + 6))
            pygame.draw.line(self.screen, (255, 220, 100), (x1, y1), (x2, y2), 2)

    def draw_particles(self):
        for p in self.particles:
            p.draw(self.screen)

    def draw_hud(self):
        top = ROWS * CELL
        pygame.draw.rect(self.screen, (18, 22, 38), pygame.Rect(0, top, WIDTH, 80))
        pygame.draw.line(self.screen, (40, 200, 100), (0, top), (WIDTH, top), 1)

        lvl = get_level(self.score)

        score_txt = self.font_sm.render(f"SCORE  {self.score:04d}", True, (200, 210, 255))
        hs_txt    = self.font_sm.render(f"BEST   {self.highscore:04d}", True, (255, 215, 0))
        self.screen.blit(score_txt, (16, top + 8))
        self.screen.blit(hs_txt,    (16, top + 34))

        # Level badge with pulsing glow
        badge = self.font_md.render(lvl[1], True, lvl[3])
        self.screen.blit(badge, badge.get_rect(topright=(WIDTH - 16, top + 10)))

        # Speed bar
        bx, by, bw, bh = WIDTH - 130, top + 42, 114, 8
        pygame.draw.rect(self.screen, (30, 35, 60), pygame.Rect(bx, by, bw, bh), border_radius=4)
        lvl_idx = LEVELS.index(lvl)
        fill_w  = int(bw * (lvl_idx + 1) / len(LEVELS))
        pygame.draw.rect(self.screen, lvl[3], pygame.Rect(bx, by, fill_w, bh), border_radius=4)
        self.screen.blit(self.font_xs.render("SPEED", True, (180, 190, 210)), (bx, by + 12))

        ctrl = self.font_xs.render("WASD/Arrows  R=restart  Q=quit", True, (60, 70, 110))
        self.screen.blit(ctrl, (16, top + 60))

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, ROWS * CELL), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        lvl = get_level(self.score)
        if self.new_hs:
            msg = self.font_lg.render("NEW HIGH SCORE!", True, (255, 215, 0))
            sub = self.font_md.render(f"{self.score} pts  —  Press R to restart", True, (200, 210, 255))
        else:
            msg = self.font_lg.render("GAME  OVER", True, (255, 80, 80))
            sub = self.font_md.render(
                f"Score: {self.score}    Best: {self.highscore}    R = restart",
                True, (200, 210, 255))

        lvl_txt = self.font_md.render(f"Reached: {lvl[1]}", True, lvl[3])
        cy = ROWS * CELL // 2
        self.screen.blit(msg,     msg.get_rect(center=(WIDTH // 2, cy - 40)))
        self.screen.blit(sub,     sub.get_rect(center=(WIDTH // 2, cy + 4)))
        self.screen.blit(lvl_txt, lvl_txt.get_rect(center=(WIDTH // 2, cy + 40)))

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        self.tick += 1

        # Update particles every frame regardless of alive state
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update()

        if not self.alive:
            # Spawn death explosion once
            if not self.death_done:
                spawn_death_particles(self.particles, self.snake)
                self.death_done = True
            return

        self.dir     = self.next
        hx, hy       = self.snake[0]
        dx, dy       = self.dir
        new_head     = (hx + dx, hy + dy)

        if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
            self.end_game(); return
        if new_head in self.snake:
            self.end_game(); return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            old_food = self.food
            self.score += 10
            self.food   = random_food(self.snake)

            # Eat sparkle uses current snake head colour
            head_col, _ = get_snake_colors(self.score)
            spawn_eat_particles(self.particles, old_food, head_col)
            SND_EAT.play()

            # Level up?
            new_lvl_idx = LEVELS.index(get_level(self.score))
            if new_lvl_idx > self.cur_lvl_idx:
                self.cur_lvl_idx = new_lvl_idx
                SND_LEVELUP.play()
        else:
            self.snake.pop()

    def end_game(self):
        self.alive = False
        if self.score > self.highscore:
            self.highscore = self.score
            save_highscore(self.highscore)
            self.new_hs = True
            SND_HIGHSCORE.play()
        else:
            SND_DIE.play()

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        pygame.quit(); sys.exit()
                    if event.key == pygame.K_r:
                        self.reset()
                    if event.key in (pygame.K_UP,    pygame.K_w) and self.dir != DOWN:
                        self.next = UP
                    if event.key in (pygame.K_DOWN,  pygame.K_s) and self.dir != UP:
                        self.next = DOWN
                    if event.key in (pygame.K_LEFT,  pygame.K_a) and self.dir != RIGHT:
                        self.next = LEFT
                    if event.key in (pygame.K_RIGHT, pygame.K_d) and self.dir != LEFT:
                        self.next = RIGHT

            self.update()

            fps = get_level(self.score)[2]

            self.screen.fill((10, 12, 20))
            self.draw_grid()
            self.draw_food()
            self.draw_snake()
            self.draw_particles()
            self.draw_hud()
            if not self.alive:
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(fps)

# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    SnakeGame().run()
