/*
 * tetris.c -- A complete Tetris for the Linux terminal, built on ncurses.
 *
 * Build:  gcc tetris.c -o tetris -lncurses
 * Run:    ./tetris
 *
 * Controls:
 *   Left / Right   move the falling piece
 *   Up             rotate clockwise (with wall kicks)
 *   Down           soft drop  (+1 point per cell)
 *   Space          hard drop  (+2 points per cell)
 *   P              pause / resume
 *   Q              quit
 *   R              restart (on the game over screen)
 *
 * Single-file ANSI C. The terminal is always restored via endwin(), including
 * on Ctrl-C and on abnormal exit (atexit handler).
 */

#include <ncurses.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define BOARD_W    10          /* playfield width, in cells            */
#define BOARD_H    20          /* playfield height, in cells           */
#define BOX         4          /* every tetromino lives in a 4x4 box   */
#define NUM_PIECES  7          /* I J L O S T Z                        */
#define NUM_ROTS    4          /* four quarter-turns per piece         */

#define MIN_COLS   38          /* board frame (22) + side panel (16)   */
#define MIN_LINES  22

/* Colour pairs. 1..7 are the tetrominoes, in piece-index order. */
enum {
    PAIR_I = 1, PAIR_J, PAIR_L, PAIR_O, PAIR_S, PAIR_T, PAIR_Z,
    PAIR_FRAME, PAIR_LABEL, PAIR_TEXT, PAIR_OVER
};

/* Spawn orientations, each inside a 4x4 bounding box.  Rotations 1..3 are
 * derived from these at start-up by rotating the box a quarter turn. */
static const char *SHAPE_SRC[NUM_PIECES][BOX] = {
    { "....", "XXXX", "....", "...." },  /* I -- light blue  */
    { "X...", "XXX.", "....", "...." },  /* J -- dark blue   */
    { "..X.", "XXX.", "....", "...." },  /* L -- yellow      */
    { ".XX.", ".XX.", "....", "...." },  /* O -- white       */
    { ".XX.", "XX..", "....", "...." },  /* S -- green       */
    { ".X..", "XXX.", "....", "...." },  /* T -- magenta     */
    { "XX..", ".XX.", "....", "...." }   /* Z -- red         */
};

/* shape[piece][rotation][row][col] -- 1 when the cell is filled. */
static int shape[NUM_PIECES][NUM_ROTS][BOX][BOX];

/* Wall-kick candidates, tried in order when a rotation would collide.
 * Keeps rotations feeling responsive right up against the walls. */
static const int KICKS[][2] = {
    { 0,  0}, {-1,  0}, { 1,  0}, {-2,  0}, { 2,  0},
    { 0, -1}, {-1, -1}, { 1, -1}, {-2, -1}, { 2, -1}
};
#define NUM_KICKS ((int)(sizeof KICKS / sizeof KICKS[0]))

typedef struct {
    int board[BOARD_H][BOARD_W];  /* 0 = empty, else a colour-pair index   */
    int piece;                    /* active piece index                    */
    int rot;                      /* active rotation, 0..3                 */
    int x, y;                     /* top-left of the active 4x4 box        */
    int next;                     /* next piece index                      */
    int score, level, lines;
    long last_drop;               /* CLOCK_MONOTONIC ms of last gravity step */
    int running, paused, over, restart;
} Game;

/* Screen geometry, recomputed every frame so resizes are picked up. */
typedef struct {
    int fx, fy;   /* board frame (border) origin   */
    int ix, iy;   /* board interior origin (0,0)   */
    int px, py;   /* side panel origin             */
} Layout;

static volatile sig_atomic_t g_quit = 0;

static void on_signal(int sig)
{
    (void)sig;
    g_quit = 1;
}

/* Guarantees the terminal is handed back in a usable state. */
static void cleanup(void)
{
    if (!isendwin())
        endwin();
}

static long now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long)ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

/* ------------------------------------------------------------------ setup */

static void init_shapes(void)
{
    for (int p = 0; p < NUM_PIECES; p++) {
        for (int r = 0; r < BOX; r++)
            for (int c = 0; c < BOX; c++)
                shape[p][0][r][c] = (SHAPE_SRC[p][r][c] == 'X');

        /* Each further quarter-turn is the previous box rotated 90 degrees. */
        for (int rot = 1; rot < NUM_ROTS; rot++)
            for (int r = 0; r < BOX; r++)
                for (int c = 0; c < BOX; c++)
                    shape[p][rot][r][c] = shape[p][rot - 1][BOX - 1 - c][r];
    }
}

static void init_colors(void)
{
    if (!has_colors())
        return;

    start_color();
    use_default_colors();

    init_pair(PAIR_I,     COLOR_CYAN,    -1);
    init_pair(PAIR_J,     COLOR_BLUE,    -1);
    init_pair(PAIR_L,     COLOR_YELLOW,  -1);
    init_pair(PAIR_O,     COLOR_WHITE,   -1);
    init_pair(PAIR_S,     COLOR_GREEN,   -1);
    init_pair(PAIR_T,     COLOR_MAGENTA, -1);
    init_pair(PAIR_Z,     COLOR_RED,     -1);
    init_pair(PAIR_FRAME, COLOR_WHITE,   -1);
    init_pair(PAIR_LABEL, COLOR_CYAN,    -1);
    init_pair(PAIR_TEXT,  COLOR_WHITE,   -1);
    init_pair(PAIR_OVER,  COLOR_RED,     COLOR_BLACK);
}

/* 7-bag randomiser: every piece appears once per bag, so runs of bad luck
 * are bounded and the distribution stays honest. */
static int bag[NUM_PIECES];
static int bag_pos = NUM_PIECES;

static int next_piece(void)
{
    if (bag_pos >= NUM_PIECES) {
        for (int i = 0; i < NUM_PIECES; i++)
            bag[i] = i;
        for (int i = NUM_PIECES - 1; i > 0; i--) {   /* Fisher-Yates */
            int j = rand() % (i + 1);
            int t = bag[i];
            bag[i] = bag[j];
            bag[j] = t;
        }
        bag_pos = 0;
    }
    return bag[bag_pos++];
}

/* -------------------------------------------------------------- game rules */

static int collides(const Game *g, int piece, int rot, int px, int py)
{
    for (int r = 0; r < BOX; r++) {
        for (int c = 0; c < BOX; c++) {
            if (!shape[piece][rot][r][c])
                continue;

            int bx = px + c;
            int by = py + r;

            if (bx < 0 || bx >= BOARD_W || by >= BOARD_H)
                return 1;
            if (by >= 0 && g->board[by][bx])
                return 1;
        }
    }
    return 0;
}

static void spawn(Game *g)
{
    g->piece = g->next;
    g->next  = next_piece();
    g->rot   = 0;
    g->x     = (BOARD_W - BOX) / 2;
    g->y     = 0;

    /* Nowhere to put the new piece: the stack has reached the top. */
    if (collides(g, g->piece, g->rot, g->x, g->y))
        g->over = 1;
}

static int try_move(Game *g, int dx, int dy)
{
    if (collides(g, g->piece, g->rot, g->x + dx, g->y + dy))
        return 0;

    g->x += dx;
    g->y += dy;
    return 1;
}

static void try_rotate(Game *g)
{
    int nr = (g->rot + 1) % NUM_ROTS;

    for (int k = 0; k < NUM_KICKS; k++) {
        int nx = g->x + KICKS[k][0];
        int ny = g->y + KICKS[k][1];

        if (!collides(g, g->piece, nr, nx, ny)) {
            g->rot = nr;
            g->x   = nx;
            g->y   = ny;
            return;
        }
    }
    /* Every kick failed -- the rotation is not possible here. */
}

static void clear_lines(Game *g)
{
    static const int POINTS[5] = { 0, 100, 300, 500, 800 };
    int cleared = 0;

    for (int row = BOARD_H - 1; row >= 0; row--) {
        int full = 1;
        for (int c = 0; c < BOARD_W; c++) {
            if (!g->board[row][c]) {
                full = 0;
                break;
            }
        }
        if (!full)
            continue;

        /* Drop everything above this row down by one. */
        for (int r = row; r > 0; r--)
            memcpy(g->board[r], g->board[r - 1], sizeof g->board[0]);
        memset(g->board[0], 0, sizeof g->board[0]);

        cleared++;
        row++;   /* re-test the row we just refilled */
    }

    if (cleared > 0) {
        g->score += POINTS[cleared] * g->level;
        g->lines += cleared;
        g->level  = 1 + g->lines / 10;
    }
}

static void lock_piece(Game *g)
{
    for (int r = 0; r < BOX; r++)
        for (int c = 0; c < BOX; c++)
            if (shape[g->piece][g->rot][r][c]) {
                int bx = g->x + c;
                int by = g->y + r;
                if (by >= 0 && by < BOARD_H && bx >= 0 && bx < BOARD_W)
                    g->board[by][bx] = g->piece + 1;
            }

    clear_lines(g);
    spawn(g);
}

static void hard_drop(Game *g)
{
    int dist = 0;

    while (!collides(g, g->piece, g->rot, g->x, g->y + 1)) {
        g->y++;
        dist++;
    }

    g->score += dist * 2;
    lock_piece(g);
}

/* Speed ramps up with level, from a lazy 800 ms down to a floor of 80 ms. */
static int drop_interval_ms(const Game *g)
{
    int ms = 800 - (g->level - 1) * 70;
    return ms < 80 ? 80 : ms;
}

static void handle_input(Game *g, int ch, long now)
{
    if (ch == ERR)
        return;

    if (g->over) {
        if (ch == 'r' || ch == 'R') {
            g->restart = 1;
            g->running = 0;
        } else if (ch == 'q' || ch == 'Q') {
            g->running = 0;
        }
        return;
    }

    switch (ch) {
    case 'q': case 'Q':
        g->running = 0;
        break;
    case 'p': case 'P':
        g->paused = !g->paused;
        g->last_drop = now;      /* don't dump a piece the instant we resume */
        break;
    case KEY_LEFT:
        if (!g->paused) try_move(g, -1, 0);
        break;
    case KEY_RIGHT:
        if (!g->paused) try_move(g, 1, 0);
        break;
    case KEY_UP:
        if (!g->paused) try_rotate(g);
        break;
    case KEY_DOWN:
        if (!g->paused && try_move(g, 0, 1)) {
            g->score += 1;
            g->last_drop = now;
        }
        break;
    case ' ':
        if (!g->paused) hard_drop(g);
        break;
    default:
        break;
    }
}

/* ---------------------------------------------------------------- drawing */

static void compute_layout(Layout *L)
{
    int frame_w = BOARD_W * 2 + 2;    /* two characters per cell + borders */
    int frame_h = BOARD_H + 2;
    int panel_w = 16;
    int total_w = frame_w + panel_w;

    L->fx = (COLS - total_w) / 2;
    L->fy = (LINES - frame_h) / 2;
    if (L->fx < 0) L->fx = 0;
    if (L->fy < 0) L->fy = 0;

    L->ix = L->fx + 1;                /* inside the border */
    L->iy = L->fy + 1;
    L->px = L->fx + frame_w + 2;
    L->py = L->fy;
}

static void draw_frame(int fx, int fy, int w, int h, int pair)
{
    attron(COLOR_PAIR(pair));
    mvaddch(fy, fx, ACS_ULCORNER);
    mvhline(fy, fx + 1, ACS_HLINE, w - 2);
    mvaddch(fy, fx + w - 1, ACS_URCORNER);
    mvaddch(fy + h - 1, fx, ACS_LLCORNER);
    mvhline(fy + h - 1, fx + 1, ACS_HLINE, w - 2);
    mvaddch(fy + h - 1, fx + w - 1, ACS_LRCORNER);
    mvvline(fy + 1, fx, ACS_VLINE, h - 2);
    mvvline(fy + 1, fx + w - 1, ACS_VLINE, h - 2);
    attroff(COLOR_PAIR(pair));
}

static void draw_cell(int x, int y, int pair, int filled)
{
    if (filled) {
        attron(COLOR_PAIR(pair) | A_BOLD);
        mvaddstr(y, x, "[]");
        attroff(COLOR_PAIR(pair) | A_BOLD);
    } else {
        attron(A_DIM);
        mvaddstr(y, x, ". ");
        attroff(A_DIM);
    }
}

static void draw_board(const Game *g, const Layout *L)
{
    /* Settled stack. */
    for (int r = 0; r < BOARD_H; r++)
        for (int c = 0; c < BOARD_W; c++)
            draw_cell(L->ix + c * 2, L->iy + r, g->board[r][c],
                      g->board[r][c] != 0);

    if (g->over)
        return;

    /* Ghost: where the piece lands on a hard drop. */
    int gy = g->y;
    while (!collides(g, g->piece, g->rot, g->x, gy + 1))
        gy++;

    if (gy != g->y) {
        for (int r = 0; r < BOX; r++)
            for (int c = 0; c < BOX; c++)
                if (shape[g->piece][g->rot][r][c]) {
                    int bx = g->x + c;
                    int by = gy + r;
                    if (by < 0 || by >= BOARD_H || bx < 0 || bx >= BOARD_W)
                        continue;
                    attron(COLOR_PAIR(g->piece + 1) | A_DIM);
                    mvaddstr(L->iy + by, L->ix + bx * 2, "[]");
                    attroff(COLOR_PAIR(g->piece + 1) | A_DIM);
                }
    }

    /* Active piece. */
    for (int r = 0; r < BOX; r++)
        for (int c = 0; c < BOX; c++) {
            if (!shape[g->piece][g->rot][r][c])
                continue;
            int bx = g->x + c;
            int by = g->y + r;
            if (by < 0 || by >= BOARD_H || bx < 0 || bx >= BOARD_W)
                continue;
            draw_cell(L->ix + bx * 2, L->iy + by, g->piece + 1, 1);
        }
}

static void draw_preview(const Game *g, int x, int y)
{
    int p = g->next;
    int minr = BOX, maxr = -1, minc = BOX, maxc = -1;

    /* Trim the 4x4 box down to the cells the piece actually uses. */
    for (int r = 0; r < BOX; r++)
        for (int c = 0; c < BOX; c++)
            if (shape[p][0][r][c]) {
                if (r < minr) minr = r;
                if (r > maxr) maxr = r;
                if (c < minc) minc = c;
                if (c > maxc) maxc = c;
            }

    if (maxr < 0)
        return;

    for (int r = minr; r <= maxr; r++)
        for (int c = minc; c <= maxc; c++)
            draw_cell(x + (c - minc) * 2, y + (r - minr), p + 1,
                      shape[p][0][r][c]);
}

static void panel_label(int y, int x, const char *s)
{
    attron(COLOR_PAIR(PAIR_LABEL));
    mvaddstr(y, x, s);
    attroff(COLOR_PAIR(PAIR_LABEL));
}

static void panel_field(int *y, int x, const char *label, const char *value)
{
    panel_label(*y, x, label);
    attron(COLOR_PAIR(PAIR_TEXT) | A_BOLD);
    mvaddstr(*y + 1, x, value);
    attroff(COLOR_PAIR(PAIR_TEXT) | A_BOLD);
    *y += 3;
}

static void panel_row(int *y, int x, const char *s)
{
    attron(COLOR_PAIR(PAIR_TEXT));
    mvaddstr(*y, x, s);
    attroff(COLOR_PAIR(PAIR_TEXT));
    *y += 1;
}

static void draw_panel(const Game *g, const Layout *L)
{
    char buf[32];
    int x = L->px, y = L->py;

    attron(COLOR_PAIR(PAIR_LABEL) | A_BOLD);
    mvaddstr(y, x, "TETRIS");
    attroff(COLOR_PAIR(PAIR_LABEL) | A_BOLD);

    attron(COLOR_PAIR(PAIR_FRAME));
    mvhline(y + 1, x, ACS_HLINE, 14);
    attroff(COLOR_PAIR(PAIR_FRAME));

    int cy = y + 3;

    snprintf(buf, sizeof buf, "%d", g->score);
    panel_field(&cy, x, "Score", buf);
    snprintf(buf, sizeof buf, "%d", g->level);
    panel_field(&cy, x, "Level", buf);
    snprintf(buf, sizeof buf, "%d", g->lines);
    panel_field(&cy, x, "Lines", buf);

    panel_label(cy, x, "Next");
    draw_preview(g, x, cy + 1);
    cy += 4;

    panel_row(&cy, x, "L/R   move");
    panel_row(&cy, x, "Up    rotate");
    panel_row(&cy, x, "Dn    soft drop");
    panel_row(&cy, x, "Space hard drop");
    panel_row(&cy, x, "P     pause");
    panel_row(&cy, x, "Q     quit");
}

static void draw_overlay(const Layout *L, const char *title, const char *sub)
{
    int w = 18, h = 5;
    int x = L->ix + (BOARD_W * 2 - w) / 2;
    int y = L->iy + (BOARD_H - h) / 2;

    for (int r = 0; r < h; r++)
        for (int c = 0; c < w; c++) {
            attron(COLOR_PAIR(PAIR_OVER));
            mvaddch(y + r, x + c, ' ');
            attroff(COLOR_PAIR(PAIR_OVER));
        }

    draw_frame(x, y, w, h, PAIR_OVER);

    attron(COLOR_PAIR(PAIR_OVER) | A_BOLD);
    mvaddstr(y + 2, x + (w - (int)strlen(title)) / 2, title);
    mvaddstr(y + 3, x + (w - (int)strlen(sub)) / 2, sub);
    attroff(COLOR_PAIR(PAIR_OVER) | A_BOLD);
}

static void draw(const Game *g)
{
    Layout L;

    erase();

    if (COLS < MIN_COLS || LINES < MIN_LINES) {
        attron(COLOR_PAIR(PAIR_OVER) | A_BOLD);
        mvaddstr(LINES / 2, 0, "Terminal too small");
        attroff(COLOR_PAIR(PAIR_OVER) | A_BOLD);
        mvprintw(LINES / 2 + 1, 0, "Need %dx%d, have %dx%d", MIN_COLS,
                 MIN_LINES, COLS, LINES);
        refresh();
        return;
    }

    compute_layout(&L);

    draw_frame(L.fx, L.fy, BOARD_W * 2 + 2, BOARD_H + 2, PAIR_FRAME);
    draw_board(g, &L);
    draw_panel(g, &L);

    if (g->paused)
        draw_overlay(&L, "PAUSED", "press P");
    else if (g->over)
        draw_overlay(&L, "GAME OVER", "Q quit  R retry");

    refresh();
}

/* ------------------------------------------------------------------- main */

int main(void)
{
    Game g;
    int again = 1;

    if (initscr() == NULL) {
        fprintf(stderr, "tetris: failed to initialise ncurses\n");
        return 1;
    }
    atexit(cleanup);          /* restore the terminal on any exit path */

    cbreak();
    noecho();
    keypad(stdscr, TRUE);
    nodelay(stdscr, TRUE);    /* non-blocking input */
    curs_set(0);

    init_colors();
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    srand((unsigned)time(NULL) ^ (unsigned)getpid());
    init_shapes();

    while (again) {
        memset(&g, 0, sizeof g);
        g.level     = 1;
        g.running   = 1;
        g.last_drop = now_ms();

        bag_pos = NUM_PIECES;          /* fresh bag each game */
        g.next  = next_piece();
        spawn(&g);

        while (g.running && !g_quit) {
            int ch;

            /* Drain every pending keypress before ticking the clock. */
            while ((ch = getch()) != ERR)
                handle_input(&g, ch, now_ms());

            if (g_quit)
                break;

            if (!g.over && !g.paused) {
                long now = now_ms();
                if (now - g.last_drop >= drop_interval_ms(&g)) {
                    g.last_drop = now;
                    if (!try_move(&g, 0, 1))
                        lock_piece(&g);
                }
            }

            draw(&g);
            napms(16);                /* ~60 fps */
        }

        again = g.restart && !g_quit;
    }

    endwin();

    if (g.over)
        printf("Game over -- final score %d, %d lines, level %d.\n",
               g.score, g.lines, g.level);

    return 0;
}
