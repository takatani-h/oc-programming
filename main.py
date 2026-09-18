import pyxel
import math

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 256
MIN_SPEED_TO_TURM = 0.5

pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT)
pyxel.load("my_resource.pyxres")

for x in range(SCREEN_WIDTH//8):
    for y in range(SCREEN_HEIGHT//8):
        if pyxel.tilemaps[0].pget(x, y) == (2, 0):
            print(x*8, y*8)
            car_x, car_y = x*8, y*8

start_x, start_y = car_x, car_y
car_angle = 0
car_speed = 0
start_frame = None
finish_frame = None
course_out = False

def update():
    global car_x, car_y, car_angle, car_speed, start_frame, finish_frame, course_out

    if pyxel.btnp(pyxel.KEY_R):
        car_x, car_y = start_x, start_y
        car_angle = 0
        car_speed = 0
        start_frame = None
        finish_frame = None
        course_out = False
        return

    TURN_SPEED = 0.8
    if car_speed > MIN_SPEED_TO_TURM and pyxel.btn(pyxel.KEY_LEFT):
        car_angle -= TURN_SPEED
    if car_speed > MIN_SPEED_TO_TURM and pyxel.btn(pyxel.KEY_RIGHT):
        car_angle += TURN_SPEED

    ACCELERATION = 0.03
    DECELERATION = 0.50
    if pyxel.btn(pyxel.KEY_UP):
        if start_frame is None:
            start_frame = pyxel.frame_count
        car_speed = min(car_speed + ACCELERATION, 2)
    if pyxel.btn(pyxel.KEY_DOWN):
        car_speed = max(car_speed - DECELERATION, 0)

    car_x += math.sin(math.radians(car_angle)) * car_speed
    car_y -= math.cos(math.radians(car_angle)) * car_speed

    center_x = int(car_x + 8) // 8
    center_y = int(car_y + 12) // 8
    if not (0 <= center_x < 32 and 0 <= center_y < 32):
        course_out = True
    else:
        current_tile = pyxel.tilemaps[0].pget(center_x, center_y)
        if current_tile not in ((1, 0), (2, 0), (3, 0)):
            course_out = True
        elif (
            current_tile == (3, 0)
            and start_frame is not None
            and finish_frame is None
            and not course_out
        ):
            finish_frame = pyxel.frame_count

def draw():
    global car_x, car_y
    pyxel.bltm(0, 0, 0, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
    pyxel.blt(car_x, car_y, 0, 0, 0, 16, 24, colkey=15, rotate=car_angle, scale=1)
    end_frame = finish_frame if finish_frame is not None else pyxel.frame_count
    elapsed_time = 0 if start_frame is None else (end_frame - start_frame) / 30
    if course_out:
        pyxel.text(2, 2, "COURSE OUT! PRESS 'R' TO RETRY", 8)
    else:
        time_color = 11 if finish_frame is not None else 7
        pyxel.text(2, 2, f"TIME {elapsed_time:.2f}", time_color)

pyxel.run(update, draw)
