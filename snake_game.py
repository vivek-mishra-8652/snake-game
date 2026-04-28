import pygame
import random
import sys

# ── Init ──────────────────────────────────────────────────────────────────────
pygame.init()

# ── Constants ─────────────────────────────────────────────────────────────────
CELL      = 20
COLS      = 30
ROWS      = 25
WIDTH     = COLS * CELL
HEIGHT    = ROWS * CELL + 60          # extra 60px for score bar

FPS       = 10                        # increase for harder game

# Colours
BG        = (10,  12,  20)
GRID_C    = (20,  24,  40)
SNAKE_H   = (80,  255, 160)           # head
SNAKE_B   = (40,  200, 100)           # body
FOOD_C    = (255, 80,  80)
TEXT_C    = (200, 210, 255)
SCORE_BG  = (18,  22,  38)
OVER_BG   = (0,   0,   0,  160)      # semi-transparent (used on surface)

# Directions
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)

# ── Helpers ───────────────────────────────────────────────────────────────────
def draw_cell(surf, col, row, color, radius=4):
    rect = pygame.Rect(col * CELL + 1, row * CELL + 1, CELL - 2, CELL - 2)
    pygame.draw.rect(surf, color, rect, border_radius=radius)

def random_food(snake):
    while True:
        pos = (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
        if pos not in snake:
            return pos

# ── Game class ────────────────────────────────────────────────────────────────
class SnakeGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("🐍  Snake")
        self.clock  = pygame.time.Clock()
        self.font_lg = pygame.font.SysFont("Consolas", 36, bold=True)
        self.font_sm = pygame.font.SysFont("Consolas", 20)
        self.reset()

    def reset(self):
        mid = (COLS // 2, ROWS // 2)
        self.snake  = [mid, (mid[0]-1, mid[1]), (mid[0]-2, mid[1])]
        self.dir    = RIGHT
        self.next   = RIGHT
        self.food   = random_food(self.snake)
        self.score  = 0
        self.alive  = True

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw_grid(self):
        for c in range(COLS):
            for r in range(ROWS):
                rect = pygame.Rect(c * CELL, r * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, GRID_C, rect, 1)

    def draw_snake(self):
        for i, (c, r) in enumerate(self.snake):
            color = SNAKE_H if i == 0 else SNAKE_B
            draw_cell(self.screen, c, r, color)

    def draw_food(self):
        c, r = self.food
        cx = c * CELL + CELL // 2
        cy = r * CELL + CELL // 2
        pygame.draw.circle(self.screen, FOOD_C, (cx, cy), CELL // 2 - 2)
        # shine
        pygame.draw.circle(self.screen, (255, 180, 180), (cx - 3, cy - 3), 3)

    def draw_hud(self):
        hud = pygame.Rect(0, ROWS * CELL, WIDTH, 60)
        pygame.draw.rect(self.screen, SCORE_BG, hud)
        pygame.draw.line(self.screen, SNAKE_B, (0, ROWS * CELL), (WIDTH, ROWS * CELL), 1)
        score_txt = self.font_sm.render(f"SCORE  {self.score:04d}", True, TEXT_C)
        ctrl_txt  = self.font_sm.render("WASD / Arrows  |  R = restart  |  Q = quit", True, (80, 90, 130))
        self.screen.blit(score_txt, (16, ROWS * CELL + 10))
        self.screen.blit(ctrl_txt,  (16, ROWS * CELL + 34))

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, ROWS * CELL), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        msg  = self.font_lg.render("GAME  OVER", True, (255, 80, 80))
        sub  = self.font_sm.render(f"Score: {self.score}   —   Press R to restart", True, TEXT_C)
        self.screen.blit(msg, msg.get_rect(center=(WIDTH//2, ROWS*CELL//2 - 20)))
        self.screen.blit(sub, sub.get_rect(center=(WIDTH//2, ROWS*CELL//2 + 24)))

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        if not self.alive:
            return
        self.dir = self.next
        hx, hy = self.snake[0]
        dx, dy = self.dir
        new_head = (hx + dx, hy + dy)

        # wall collision
        if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
            self.alive = False
            return

        # self collision
        if new_head in self.snake:
            self.alive = False
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 10
            self.food = random_food(self.snake)
        else:
            self.snake.pop()

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
                    # direction (prevent 180° reversal)
                    if event.key in (pygame.K_UP,    pygame.K_w) and self.dir != DOWN:
                        self.next = UP
                    if event.key in (pygame.K_DOWN,  pygame.K_s) and self.dir != UP:
                        self.next = DOWN
                    if event.key in (pygame.K_LEFT,  pygame.K_a) and self.dir != RIGHT:
                        self.next = LEFT
                    if event.key in (pygame.K_RIGHT, pygame.K_d) and self.dir != LEFT:
                        self.next = RIGHT

            self.update()

            # render
            self.screen.fill(BG)
            self.draw_grid()
            self.draw_food()
            self.draw_snake()
            self.draw_hud()
            if not self.alive:
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    SnakeGame().run()