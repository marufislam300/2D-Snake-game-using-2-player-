from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import sys
import math
import os  # Added import for os module

# -------------------------------------------------------------------------
# WINDOW & GLOBAL VARIABLES
# -------------------------------------------------------------------------
width, height = 800, 600

snake1 = [(40, 40)]
snake2 = [(760, 560)]
direction1 = 'RIGHT'
direction2 = 'LEFT'
food = None

# Track if snakes are alive (for Two-Player mode)
snake1_alive = True
snake2_alive = True

game_mode = None   # 'SINGLE' or 'TWO'
scores = [0, 0]
game_over = False
cell_size = 10

# Speed variables
base_speed = 100   # Base timer in milliseconds
min_speed = 30     # Minimum possible timer interval

# Time-tracking for special food
time_passed = 0                  # Accumulates total ms since game start
last_special_food_time = 0       # When the special food was last spawned (ms)
special_food_interval = 15000    # Spawn special food every 15 seconds
special_food_duration = 7000     # Special food remains for 7 seconds
special_food_active = False
special_food_position = None
special_food_start_time = 0

# Radii for foods
NORMAL_FOOD_RADIUS = 5
SPECIAL_FOOD_RADIUS = 10  # 2x the normal size

# The snake radius (approx) used for collision with obstacles
SNAKE_RADIUS = 5

# Obstacles
obstacles_lines = []
obstacles_points = []

# Pause state
paused = False

# Window ID (to be set in main)
window_id = None

# -------------------------------------------------------------------------
# BUTTON DEFINITIONS
# -------------------------------------------------------------------------
# Button dimensions
BUTTON_SIZE = 40  # Width and height of buttons

# Restart Button (Top-Left)
restart_button_top_left = (10, height - 10)
restart_button_bottom_right = (10 + BUTTON_SIZE, height - BUTTON_SIZE)

# Pause Button (Top-Middle)
pause_button_top_left = (width // 2 - BUTTON_SIZE // 2, height - 10)
pause_button_bottom_right = (width // 2 + BUTTON_SIZE // 2, height - BUTTON_SIZE)

# Close (Cross) Button (Top-Right)
close_button_top_left = (width - 10 - BUTTON_SIZE, height - 10)
close_button_bottom_right = (width - 10, height - BUTTON_SIZE)

# -------------------------------------------------------------------------
# TEXT & UI FUNCTIONS
# -------------------------------------------------------------------------
def render_text(x, y, text):
    """
    Renders text on the screen at position (x, y).
    """
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_9_BY_15, ord(ch))

def display_score():
    """
    Displays the current scores of the snakes.
    """
    glColor3f(1.0, 1.0, 1.0)  # White color for the score
    score_text = f"Score - Snake 1 (BL): {scores[0]}   Snake 2: {scores[1]}"
    render_text(10, height - 20, score_text)

def display_mode():
    """
    Displays the current game mode.
    """
    if game_mode:
        mode_text = f"Mode: {'Single-Player' if game_mode == 'SINGLE' else 'Two-Player'}"
        glColor3f(1.0, 1.0, 1.0)  # White color for the mode
        render_text(width // 2 - 50, height - 40, mode_text)

def print_score():
    """
    Prints the final scores to the terminal.
    """
    print(f"Score - Snake 1: {scores[0]}   Score - Snake 2: {scores[1]}")

# -------------------------------------------------------------------------
# MIDPOINT LINE HELPER FUNCTIONS
# -------------------------------------------------------------------------
def get_zone(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    
    if dx >= 0 and dy >= 0:
        if abs(dx) >= abs(dy):
            return 0
        return 1
    elif dx < 0 and dy >= 0:
        if abs(dx) >= abs(dy):
            return 3
        return 2
    elif dx < 0 and dy < 0:
        if abs(dx) >= abs(dy):
            return 4
        return 5
    else:  # dx >= 0 and dy < 0
        if abs(dx) >= abs(dy):
            return 7
        return 6

def convert_to_zone0(x, y, zone):
    if zone == 0: return (x, y)
    elif zone == 1: return (y, x)
    elif zone == 2: return (y, -x)
    elif zone == 3: return (-x, y)
    elif zone == 4: return (-x, -y)
    elif zone == 5: return (-y, -x)
    elif zone == 6: return (-y, x)
    elif zone == 7: return (x, -y)

def convert_from_zone0(x, y, zone):
    if zone == 0: return (x, y)
    elif zone == 1: return (y, x)
    elif zone == 2: return (-y, x)
    elif zone == 3: return (-x, y)
    elif zone == 4: return (-x, -y)
    elif zone == 5: return (-y, -x)
    elif zone == 6: return (y, -x)
    elif zone == 7: return (x, -y)

def midpoint_line(x1, y1, x2, y2):
    """
    Draws a line using the Midpoint (Bresenham) line algorithm.
    Returns a list of all (x,y) points on the line (for collision checks).
    """
    points = []
    zone = get_zone(x1, y1, x2, y2)
    
    x1_z0, y1_z0 = convert_to_zone0(x1, y1, zone)
    x2_z0, y2_z0 = convert_to_zone0(x2, y2, zone)
    
    dx = x2_z0 - x1_z0
    dy = y2_z0 - y1_z0
    d = 2 * dy - dx
    d_E = 2 * dy
    d_NE = 2 * (dy - dx)
    
    x = x1_z0
    y = y1_z0
    
    while x <= x2_z0:
        orig_x, orig_y = convert_from_zone0(x, y, zone)
        points.append((orig_x, orig_y))
        
        if d <= 0:
            d += d_E
        else:
            y += 1
            d += d_NE
        x += 1
    
    return points

def draw_boundaries():
    """
    Draws boundary lines around the game field using the Midpoint line algorithm.
    """
    boundaries = [
        (0, 0, width-1, 0),               # Bottom
        (0, height-1, width-1, height-1), # Top
        (0, 0, 0, height-1),              # Left
        (width-1, 0, width-1, height-1)   # Right
    ]
    
    for x1, y1, x2, y2 in boundaries:
        boundary_pts = midpoint_line(x1, y1, x2, y2)
        glBegin(GL_POINTS)
        for (x, y) in boundary_pts:
            glVertex2i(x, y)
        glEnd()

# -------------------------------------------------------------------------
# MIDPOINT CIRCLE ALGORITHM FUNCTIONS
# -------------------------------------------------------------------------
def draw_circle_points(xc, yc, x, y):
    """
    Plots all eight symmetrical points of a circle based on the current (x, y).
    """
    points = [
        (xc + x, yc + y),
        (xc - x, yc + y),
        (xc + x, yc - y),
        (xc - x, yc - y),
        (xc + y, yc + x),
        (xc - y, yc + x),
        (xc + y, yc - x),
        (xc - y, yc - x)
    ]
    glBegin(GL_POINTS)
    for px, py in points:
        glVertex2i(px, py)
    glEnd()

def draw_circle(xc, yc, radius):
    """
    Exact midpoint circle algorithm implementation.
    """
    x = 0
    y = radius
    d = 1 - radius  # Initial decision parameter

    draw_circle_points(xc, yc, x, y)

    while x < y:
        if d < 0:
            d += 2*x + 3
        else:
            y -= 1
            d += 2*(x - y) + 5
        x += 1
        draw_circle_points(xc, yc, x, y)

# -------------------------------------------------------------------------
# OBSTACLE GENERATION FUNCTIONS
# -------------------------------------------------------------------------
def generate_obstacle():
    """
    Returns a random horizontal or vertical line using (x1, y1, x2, y2).
    """
    orientation = random.choice(["H", "V"])
    if orientation == "H":
        # Horizontal line
        y = random.randint(1, height - 2)
        x1 = random.randint(1, width // 2)
        x2 = random.randint(width // 2, width - 2)
        return (x1, y, x2, y)
    else:
        # Vertical line
        x = random.randint(1, width - 2)
        y1 = random.randint(1, height // 2)
        y2 = random.randint(height // 2, height - 2)
        return (x, y1, x, y2)

def add_obstacle():
    """
    Generates a new obstacle line, adds it to obstacles_lines,
    and also stores all its points in obstacles_points for collision checks.
    """
    line = generate_obstacle()
    obstacles_lines.append(line)

    # Convert the line into a set of points
    pts = set(midpoint_line(*line))
    obstacles_points.append(pts)

    print(f"New obstacle added: {line}")

# -------------------------------------------------------------------------
# GAME LOGIC FUNCTIONS
# -------------------------------------------------------------------------
def generate_food():
    """
    Generate normal or special food positions, ensuring they're within boundaries.
    """
    x = random.randint(1, (width // cell_size) - 1) * cell_size
    y = random.randint(1, (height // cell_size) - 1) * cell_size
    return x, y

def special_keys(key, x, y):
    """
    Arrow keys for Snake 2 (Two-Player mode).
    """
    global direction2
    if game_mode == 'TWO' and snake2_alive:
        if key == GLUT_KEY_LEFT:
            direction2 = 'LEFT'
        elif key == GLUT_KEY_RIGHT:
            direction2 = 'RIGHT'
        elif key == GLUT_KEY_UP:
            direction2 = 'UP'
        elif key == GLUT_KEY_DOWN:
            direction2 = 'DOWN'

def keyboard(key, x, y):
    """
    Keyboard handler for:
      - '1' key: Single-Player mode
      - '2' key: Two-Player mode
      - WASD for Snake 1 movement
    """
    global direction1, game_mode, paused, game_over
    try:
        key = key.decode('utf-8')  # Decode byte to string
    except AttributeError:
        # In Python 3, key is already a string
        pass

    if key == '1':
        print("Single-Player Mode Selected")
        game_mode = 'SINGLE'
        reset_game()
        paused = False
    elif key == '2':
        print("Two-Player Mode Selected")
        game_mode = 'TWO'
        reset_game()
        paused = False
    elif game_mode == 'SINGLE' or game_mode == 'TWO':
        if game_mode == 'SINGLE' or (game_mode == 'TWO' and snake1_alive):
            if key.lower() == 'a':
                direction1 = 'LEFT'
            elif key.lower() == 'd':
                direction1 = 'RIGHT'
            elif key.lower() == 'w':
                direction1 = 'UP'
            elif key.lower() == 's':
                direction1 = 'DOWN'

def mouse(button, state, x, y):
    """
    Mouse click interacts with buttons:
      - Click on Restart, Pause, or Close buttons perform respective actions
    """
    global paused, game_over
    if state == GLUT_DOWN:
        # Convert GLUT y coordinate to OpenGL y coordinate
        ogl_y = height - y
        ogl_x = x

        # Check if click is within Restart Button
        if (restart_button_top_left[0] <= ogl_x <= restart_button_bottom_right[0] and
            restart_button_bottom_right[1] <= ogl_y <= restart_button_top_left[1]):
            print("Restart Button Clicked")
            reset_game()
            paused = False
            return

        # Check if click is within Pause Button
        if (pause_button_top_left[0] <= ogl_x <= pause_button_bottom_right[0] and
            pause_button_bottom_right[1] <= ogl_y <= pause_button_top_left[1]):
            print("Pause Button Clicked")
            paused = not paused
            if not paused:
                # Reschedule the update function when unpausing
                glutTimerFunc(get_game_speed(), update, 0)
            return

        # Check if click is within Close Button
        if (close_button_top_left[0] <= ogl_x <= close_button_bottom_right[0] and
            close_button_bottom_right[1] <= ogl_y <= close_button_top_left[1]):
            print("Close Button Clicked")
            # Destroy the window and exit
            glutDestroyWindow(window_id)
            os._exit(0)  # Replaced sys.exit() with os._exit(0) for immediate termination

    # Removed mode selection via mouse clicks

def reset_game():
    """
    Reset all game variables.
    """
    global snake1, snake2, food, scores, game_over
    global special_food_active, special_food_position
    global time_passed, last_special_food_time
    global snake1_alive, snake2_alive, direction1, direction2
    global obstacles_lines, obstacles_points, paused

    snake1 = [(40, 40)]
    snake2 = [(760, 560)]
    direction1 = 'RIGHT'
    direction2 = 'LEFT'

    scores = [0, 0]
    food = generate_food()
    game_over = False

    snake1_alive = True
    snake2_alive = True

    # Reset special-food-related variables
    special_food_active = False
    special_food_position = None
    time_passed = 0
    last_special_food_time = 0

    # Clear out any old obstacles
    obstacles_lines = []
    obstacles_points = []

def move_snake(snake, direction):
    """
    Moves a snake one cell in the given direction.
    """
    x, y = snake[-1]
    moves = {
        'LEFT':  (-cell_size,  0),
        'RIGHT': ( cell_size,  0),
        'UP':    ( 0,  cell_size),
        'DOWN':  ( 0, -cell_size)
    }
    dx, dy = moves.get(direction, (0, 0))
    new_head = (x + dx, y + dy)
    snake.append(new_head)
    snake.pop(0)

# -------------------------------------------------------------------------
# COLLISIONS & WIN/LOSS FUNCTIONS
# -------------------------------------------------------------------------
def decide_winner():
    """
    Compare scores and declare who won in the terminal.
    """
    global game_over
    game_over = True

    print_score()  # Print final scores

    if scores[0] > scores[1]:
        print("Snake 1 is the winner!")
    elif scores[0] < scores[1]:
        print("Snake 2 is the winner!")
    else:
        print("It's a tie!")

def kill_snake1(reason):
    """
    Handles Snake 1's death.
    """
    global snake1_alive
    snake1_alive = False
    print(f"Snake 1 died ({reason}).")

def kill_snake2(reason):
    """
    Handles Snake 2's death.
    """
    global snake2_alive
    snake2_alive = False
    print(f"Snake 2 died ({reason}).")

def check_obstacle_collision(head, radius=SNAKE_RADIUS):
    """
    Checks if the snake's head collides with any obstacles.
    Uses a radius-based collision detection.
    """
    hx, hy = head
    r2 = radius * radius

    for obs_set in obstacles_points:
        for (px, py) in obs_set:
            dx = px - hx
            dy = py - hy
            if dx*dx + dy*dy <= r2:
                return True
    return False

def check_collision():
    """
    Checks collisions for each snake:
      - Boundaries
      - Snake biting itself
      - Obstacles (using radius-based check)
      - Normal food
      - Special food
      - Snakes colliding (only if both alive)
      - If one snake dies, the other continues (Two-Player mode).
      - If eventually both die => game over => decide winner.
    Returns True if the game completely ends, False if it continues.
    """
    global game_over, snake1_alive, snake2_alive, food
    global special_food_active, special_food_position

    # --- SNAKE 1 ---
    if snake1_alive:
        head1 = snake1[-1]
        # 1) Boundary check
        if not (0 <= head1[0] < width and 0 <= head1[1] < height):
            kill_snake1("hit boundary")
        # 2) Self-bite check
        elif head1 in snake1[:-1]:
            kill_snake1("bit itself")
        # 3) Obstacle collision
        elif check_obstacle_collision(head1, SNAKE_RADIUS):
            kill_snake1("touched obstacle")

        # If STILL alive => handle food
        if snake1_alive:
            if head1 == food:
                scores[0] += 1
                snake1.insert(0, snake1[0])  # Grow
                food = generate_food()
                print(f"Score Updated - Snake 1: {scores[0]}")

            if special_food_active and head1 == special_food_position:
                scores[0] += 3
                print(f"Snake 1 ate special food! +3 points. Total = {scores[0]}")
                special_food_active = False
                add_obstacle()

    # --- SNAKE 2 (Two-Player only) ---
    if game_mode == 'TWO' and snake2_alive:
        head2 = snake2[-1]
        # 1) Boundary check
        if not (0 <= head2[0] < width and 0 <= head2[1] < height):
            kill_snake2("hit boundary")
        # 2) Self-bite check
        elif head2 in snake2[:-1]:
            kill_snake2("bit itself")
        # 3) Obstacle collision
        elif check_obstacle_collision(head2, SNAKE_RADIUS):
            kill_snake2("touched obstacle")

        # If STILL alive => handle food
        if snake2_alive:
            if head2 == food:
                scores[1] += 1
                snake2.insert(0, snake2[0])  # Grow
                food = generate_food()
                print(f"Score Updated - Snake 2: {scores[1]}")

            if special_food_active and head2 == special_food_position:
                scores[1] += 3
                print(f"Snake 2 ate special food! +3 points. Total = {scores[1]}")
                special_food_active = False
                add_obstacle()

    # --- Snakes Colliding with Each Other ---
    if game_mode == 'TWO' and snake1_alive and snake2_alive:
        head1 = snake1[-1]
        head2 = snake2[-1]
        if head1 in snake2:
            kill_snake1("collided with Snake 2")
            kill_snake2("collided with Snake 1")
            print("Game Over: Snakes collided with each other!")
        elif head2 in snake1:
            kill_snake2("collided with Snake 1")
            kill_snake1("collided with Snake 2")
            print("Game Over: Snakes collided with each other!")

    # --- Check if both dead => game over ---
    if game_mode == 'TWO':
        if (not snake1_alive) and (not snake2_alive):
            decide_winner()
            return True
        return False

    # --- Single-player logic ---
    if game_mode == 'SINGLE':
        if not snake1_alive:
            print("Game Over: Snake 1 died.")
            decide_winner()
            return True
        return False

    return False  # Default

# -------------------------------------------------------------------------
# SPEED INCREASE FUNCTION
# -------------------------------------------------------------------------
def get_game_speed():
    """
    For each set of 6 total points, reduce the interval by 10 ms.
    Minimum is min_speed.
    """
    total_increments = (scores[0] // 6) + (scores[1] // 6)
    new_speed = base_speed - 10 * total_increments
    if new_speed < min_speed:
        new_speed = min_speed
    return new_speed

# -------------------------------------------------------------------------
# UPDATE FUNCTION (GAME LOOP)
# -------------------------------------------------------------------------
def update(value):
    """
    Main update function called periodically by GLUT.
    Handles game state updates such as moving snakes, spawning food, etc.
    """
    global time_passed, last_special_food_time
    global special_food_active, special_food_position, special_food_start_time

    if game_over or paused:
        return  # No updates if the game is over or paused

    interval = get_game_speed()
    time_passed += interval

    # Spawn special food every 15s if not active
    if (not special_food_active) and (time_passed - last_special_food_time >= special_food_interval):
        special_food_active = True
        special_food_position = generate_food()
        special_food_start_time = time_passed
        last_special_food_time = time_passed

    # If special food is active, check if 7s have passed
    if special_food_active and (time_passed - special_food_start_time > special_food_duration):
        special_food_active = False

    # Move the snakes that are alive
    if game_mode is not None:
        if snake1_alive:
            move_snake(snake1, direction1)
        if game_mode == 'TWO' and snake2_alive:
            move_snake(snake2, direction2)

        # Check collisions
        if check_collision():
            return

    glutPostRedisplay()
    glutTimerFunc(get_game_speed(), update, 0)

# -------------------------------------------------------------------------
# DISPLAY FUNCTION
# -------------------------------------------------------------------------
def display():
    """
    Render the entire game scene.
    """
    glClear(GL_COLOR_BUFFER_BIT)
    
    # Draw Boundaries (Magenta)
    glColor3f(1.0, 0.0, 1.0)
    draw_boundaries()

    # --- Draw Obstacles (Yellow) ---
    glColor3f(1.0, 1.0, 0.0)
    for line in obstacles_lines:
        (ox1, oy1, ox2, oy2) = line
        pts = midpoint_line(ox1, oy1, ox2, oy2)
        glBegin(GL_POINTS)
        for (px, py) in pts:
            glVertex2i(px, py)
        glEnd()

    # --- Draw Buttons ---
    draw_buttons()

    # Snake 1 (Green)
    if snake1_alive:
        glColor3f(0.0, 1.0, 0.0)
        for segment in snake1:
            draw_circle(segment[0], segment[1], 5)

    # Snake 2 (Blue)
    if game_mode == 'TWO' and snake2_alive:
        glColor3f(0.0, 0.0, 1.0)
        for segment in snake2:
            draw_circle(segment[0], segment[1], 5)

    # Normal Food (Red)
    glColor3f(1.0, 0.0, 0.0)
    draw_circle(food[0], food[1], NORMAL_FOOD_RADIUS)

    # Special Food (Blinking Red & Bigger) if active
    if special_food_active:
        blink_rate = 500
        if ((time_passed // blink_rate) % 2) == 0:
            glColor3f(1.0, 0.0, 0.0)
            draw_circle(special_food_position[0], special_food_position[1], SPECIAL_FOOD_RADIUS)

    # Display scores and mode
    display_score()
    display_mode()
    glutSwapBuffers()

# -------------------------------------------------------------------------
# BUTTON DRAWING FUNCTION
# -------------------------------------------------------------------------
def draw_buttons():
    """
    Draws Restart, Pause, and Close buttons using the Midpoint line algorithm.
    """
    # --- Restart Button (Top-Left) - Left Arrow ---
    glColor3f(0.0, 1.0, 1.0)  # Cyan color for buttons
    # Define arrow parameters
    arrow_length = 20
    arrow_head_size = 10

    # Shaft of the arrow
    shaft_start = (restart_button_bottom_right[0] - arrow_length, restart_button_bottom_right[1] + BUTTON_SIZE//2)
    shaft_end = (restart_button_bottom_right[0], restart_button_bottom_right[1] + BUTTON_SIZE//2)
    shaft_line = midpoint_line(*shaft_start, *shaft_end)
    glBegin(GL_POINTS)
    for (x, y) in shaft_line:
        glVertex2i(x, y)
    glEnd()

    # Arrowhead lines
    # Upper diagonal
    head_upper_start = shaft_end
    head_upper_end = (shaft_end[0] - arrow_head_size, shaft_end[1] + arrow_head_size)
    head_upper_line = midpoint_line(*head_upper_start, *head_upper_end)
    glBegin(GL_POINTS)
    for (x, y) in head_upper_line:
        glVertex2i(x, y)
    glEnd()

    # Lower diagonal
    head_lower_start = shaft_end
    head_lower_end = (shaft_end[0] - arrow_head_size, shaft_end[1] - arrow_head_size)
    head_lower_line = midpoint_line(*head_lower_start, *head_lower_end)
    glBegin(GL_POINTS)
    for (x, y) in head_lower_line:
        glVertex2i(x, y)
    glEnd()

    # --- Pause Button (Top-Middle) - Two Vertical Bars ---
    glColor3f(0.0, 1.0, 1.0)  # Cyan color for buttons
    bar_width = BUTTON_SIZE // 4
    bar_spacing = BUTTON_SIZE // 2

    # Left bar
    bar1_start = (pause_button_top_left[0] + bar_spacing//2 - bar_width//2, pause_button_top_left[1])
    bar1_end = (pause_button_top_left[0] + bar_spacing//2 - bar_width//2, pause_button_bottom_right[1])
    bar_line1 = midpoint_line(*bar1_start, *bar1_end)
    glBegin(GL_POINTS)
    for (x, y) in bar_line1:
        glVertex2i(x, y)
    glEnd()

    # Right bar
    bar2_start = (pause_button_top_left[0] + 3*bar_spacing//2 - bar_width//2, pause_button_top_left[1])
    bar2_end = (pause_button_top_left[0] + 3*bar_spacing//2 - bar_width//2, pause_button_bottom_right[1])
    bar_line2 = midpoint_line(*bar2_start, *bar2_end)
    glBegin(GL_POINTS)
    for (x, y) in bar_line2:
        glVertex2i(x, y)
    glEnd()

    # --- Close Button (Top-Right) - X ---
    glColor3f(1.0, 0.0, 0.0)  # Red color for Close button
    # Diagonal from top-left to bottom-right
    cross_line1 = midpoint_line(close_button_top_left[0], close_button_top_left[1],
                                close_button_bottom_right[0], close_button_bottom_right[1])
    glBegin(GL_POINTS)
    for (x, y) in cross_line1:
        glVertex2i(x, y)
    glEnd()
    # Diagonal from bottom-left to top-right
    cross_line2 = midpoint_line(close_button_top_left[0], close_button_bottom_right[1],
                                close_button_bottom_right[0], close_button_top_left[1])
    glBegin(GL_POINTS)
    for (x, y) in cross_line2:
        glVertex2i(x, y)
    glEnd()

# -------------------------------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------------------------------
def main():
    """
    Initializes the GLUT window and starts the main loop.
    """
    global window_id
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(width, height)
    window_id = glutCreateWindow(b"Snake Game")
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glOrtho(0, width, 0, height, -1, 1)

    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutMouseFunc(mouse)

    reset_game()
    glutTimerFunc(base_speed, update, 0)

    glutMainLoop()

if __name__ == "__main__":
    main()
