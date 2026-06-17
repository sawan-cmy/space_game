import curses
import random
import time

W, H = 60, 24

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)

    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN,   curses.COLOR_BLACK)  # player
    curses.init_pair(2, curses.COLOR_RED,     curses.COLOR_BLACK)  # enemies
    curses.init_pair(3, curses.COLOR_YELLOW,  curses.COLOR_BLACK)  # bullets
    curses.init_pair(4, curses.COLOR_CYAN,    curses.COLOR_BLACK)  # stars
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # explosions
    curses.init_pair(6, curses.COLOR_WHITE,   curses.COLOR_BLACK)  # UI

    PLAYER  = curses.color_pair(1)
    ENEMY   = curses.color_pair(2)
    BULLET  = curses.color_pair(3)
    STAR    = curses.color_pair(4)
    EXPLODE = curses.color_pair(5)
    UI      = curses.color_pair(6)

    # ── game state ──────────────────────────────────────────────
    px = W // 2
    py = H - 3
    pbullets   = []   # {x, y}
    ebullets   = []   # {x, y}
    enemies    = []   # {x, y, ch, dir, hp}
    explosions = []   # {x, y, frames}
    stars      = [(random.randint(0, W-1), random.randint(0, H-1)) for _ in range(25)]
    star_timer = 0

    score    = 0
    lives    = 3
    wave     = 1
    hi_score = 0
    game_over = False
    paused   = False

    shoot_cool   = 0
    enemy_timer  = 0
    eshoot_timer = 0
    frame        = 0

    ENEMY_SHAPES = ['(+)', '<+>', '[+]', '{+}', '/*\\']

    def spawn_wave(w):
        elist = []
        cols = min(6 + w, 10)
        rows = min(1 + (w // 2), 4)
        for r in range(rows):
            shape = ENEMY_SHAPES[(r + w) % len(ENEMY_SHAPES)]
            for c in range(cols):
                x = 4 + c * ((W - 8) // cols)
                elist.append({'x': x, 'y': 2 + r * 2,
                              'ch': shape, 'dir': 1,
                              'hp': 1 + (w // 3)})
        return elist

    enemies = spawn_wave(wave)
    enemy_speed = max(4, 12 - wave)   # frames per move

    # ── draw helpers ────────────────────────────────────────────
    def safe_addstr(y, x, s, attr=0):
        if 0 <= y < H and 0 <= x < W - len(s):
            try:
                stdscr.addstr(y, x, s, attr)
            except curses.error:
                pass

    def draw_border():
        for y in range(H):
            safe_addstr(y, 0,   '|', UI)
            safe_addstr(y, W-1, '|', UI)
        for x in range(W):
            safe_addstr(0,   x, '-', UI)
            safe_addstr(H-1, x, '-', UI)

    # ── main loop ───────────────────────────────────────────────
    while True:
        key = stdscr.getch()

        if key == ord('q'):
            break
        if key == ord('p'):
            paused = not paused
        if game_over and key == ord('r'):
            px, py     = W // 2, H - 3
            pbullets   = []
            ebullets   = []
            enemies    = spawn_wave(1)
            explosions = []
            score = 0; lives = 3; wave = 1
            game_over  = False
            shoot_cool = 0; enemy_timer = 0; eshoot_timer = 0; frame = 0
            enemy_speed = 11

        if not game_over and not paused:
            # player movement
            if key == curses.KEY_LEFT  and px > 2:        px -= 1
            if key == curses.KEY_RIGHT and px < W - 4:    px += 1
            if key == curses.KEY_UP    and py > H // 2:   py -= 1
            if key == curses.KEY_DOWN  and py < H - 2:    py += 1

            # shoot
            if key == ord(' ') and shoot_cool <= 0:
                pbullets.append({'x': px, 'y': py - 1})
                pbullets.append({'x': px - 1, 'y': py - 1})
                pbullets.append({'x': px + 1, 'y': py - 1})
                shoot_cool = 6

            shoot_cool   = max(0, shoot_cool - 1)
            enemy_timer += 1
            eshoot_timer += 1
            frame += 1

            # scroll stars
            star_timer += 1
            if star_timer >= 3:
                star_timer = 0
                stars = [(x, (y + 1) % (H - 1)) for x, y in stars]

            # move player bullets
            pbullets = [b for b in pbullets if b['y'] > 1]
            for b in pbullets:
                b['y'] -= 1

            # move enemy bullets
            ebullets = [b for b in ebullets if b['y'] < H - 1]
            for b in ebullets:
                b['y'] += 1

            # move enemies
            if enemy_timer >= enemy_speed:
                enemy_timer = 0
                min_x = min((e['x'] for e in enemies), default=2)
                max_x = max((e['x'] + len(e['ch']) for e in enemies), default=W-2)
                if max_x >= W - 2:
                    for e in enemies: e['dir'] = -1; e['y'] += 1
                elif min_x <= 1:
                    for e in enemies: e['dir'] = 1;  e['y'] += 1
                for e in enemies:
                    e['x'] += e['dir']

            # enemy shoot
            if eshoot_timer >= max(10, 30 - wave * 2) and enemies:
                eshoot_timer = 0
                shooter = random.choice(enemies)
                mid = shooter['x'] + len(shooter['ch']) // 2
                ebullets.append({'x': mid, 'y': shooter['y'] + 1})

            # tick explosions
            explosions = [e for e in explosions if e['frames'] > 0]
            for e in explosions:
                e['frames'] -= 1

            # bullet hits enemy
            killed = set()
            for b in pbullets:
                for i, e in enumerate(enemies):
                    if i in killed: continue
                    if e['y'] == b['y'] and e['x'] <= b['x'] < e['x'] + len(e['ch']):
                        e['hp'] -= 1
                        b['y'] = -99
                        if e['hp'] <= 0:
                            killed.add(i)
                            score += 10 * wave
                            for dx in range(-1, 2):
                                explosions.append({'x': e['x'] + dx, 'y': e['y'], 'frames': 6})

            enemies = [e for i, e in enumerate(enemies) if i not in killed]

            # enemy bullet hits player
            ship_xs = [px - 1, px, px + 1]
            for b in ebullets:
                if b['y'] == py and b['x'] in ship_xs:
                    b['y'] = H + 99
                    lives -= 1
                    for dx in range(-2, 3):
                        explosions.append({'x': px + dx, 'y': py, 'frames': 8})
                    if lives <= 0:
                        hi_score = max(hi_score, score)
                        game_over = True

            # enemy reaches bottom
            if any(e['y'] >= H - 2 for e in enemies):
                lives -= 1
                if lives <= 0:
                    hi_score = max(hi_score, score)
                    game_over = True

            # next wave
            if not enemies:
                wave += 1
                enemy_speed = max(3, 12 - wave)
                enemies = spawn_wave(wave)
                ebullets = []

        # ── DRAW ────────────────────────────────────────────────
        stdscr.erase()
        draw_border()

        # stars
        for sx, sy in stars:
            if sy != 0 and sy != H - 1:
                safe_addstr(sy, sx, '.', STAR)

        # enemies
        for e in enemies:
            col = ENEMY | (curses.A_BOLD if frame % 10 < 5 and e['hp'] > 1 else 0)
            safe_addstr(e['y'], e['x'], e['ch'], col)

        # player ship (ASCII art)
        if not game_over:
            safe_addstr(py - 1, px,     '|',   PLAYER)
            safe_addstr(py,     px - 1, '>A<', PLAYER | curses.A_BOLD)
            safe_addstr(py + 1, px - 1, '/|\\', PLAYER)

        # player bullets
        for b in pbullets:
            safe_addstr(b['y'], b['x'], '^', BULLET | curses.A_BOLD)

        # enemy bullets
        for b in ebullets:
            safe_addstr(b['y'], b['x'], '*', ENEMY)

        # explosions
        chars = ['*', '+', '.', ' ']
        for ex in explosions:
            ch = chars[min(3, 6 - ex['frames'])]
            safe_addstr(ex['y'], ex['x'], ch, EXPLODE | curses.A_BOLD)

        # HUD
        hud = f" SCORE:{score:05d}  LIVES:{'<'*lives}  WAVE:{wave}  HI:{hi_score:05d} "
        safe_addstr(0, 2, hud[:W-4], UI | curses.A_BOLD)

        if game_over:
            cx = W // 2
            safe_addstr(H//2 - 2, cx - 5, '***********', EXPLODE | curses.A_BOLD)
            safe_addstr(H//2 - 1, cx - 4, ' GAME OVER ', UI | curses.A_BOLD)
            safe_addstr(H//2,     cx - 6, f' SCORE: {score:05d} ', UI)
            safe_addstr(H//2 + 1, cx - 5, '  R to retry', UI)
            safe_addstr(H//2 + 2, cx - 5, '  Q to quit ', UI)
            safe_addstr(H//2 + 3, cx - 5, '***********', EXPLODE | curses.A_BOLD)

        if paused:
            safe_addstr(H//2, W//2 - 4, '[ PAUSED ]', UI | curses.A_BOLD)

        # controls reminder at bottom
        safe_addstr(H-1, 2, ' Arrows:Move  Space:Shoot  P:Pause  Q:Quit ', UI)

        stdscr.refresh()

curses.wrapper(main)