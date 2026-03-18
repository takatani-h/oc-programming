"""
STL ビューア: STL を PyGame + PyOpenGL で表示する。

操作:
  マウス左ドラッグ  : カメラ回転
  マウスホイール    : ズーム
  WASD             : 車を移動 (カメラ方向基準)
  R キー           : 視点リセット
  ESC / ウィンドウ閉 : 終了
"""

import sys
import math
import numpy as np
import pygame
from pygame.locals import (
    DOUBLEBUF, OPENGL, QUIT, KEYDOWN,
    K_ESCAPE, K_r, K_w, K_s, K_a, K_d,
)
from stl import mesh
from OpenGL.GL import (
    glBegin, glEnd, glVertex3f, glVertex3fv, glNormal3fv, glClear,
    glClearColor, glEnable, glDisable, glLightfv, glMaterialfv,
    glMatrixMode, glLoadIdentity, glTranslatef, glRotatef, glScalef,
    glPushMatrix, glPopMatrix, glViewport, glColor3f, glFrustum,
    GL_TRIANGLES, GL_LINES, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST, GL_LIGHTING, GL_LIGHT0, GL_LIGHT1,
    GL_POSITION, GL_DIFFUSE, GL_AMBIENT, GL_SPECULAR,
    GL_FRONT_AND_BACK, GL_SHININESS,
    GL_MODELVIEW, GL_PROJECTION,
    GL_COLOR_MATERIAL, GL_NORMALIZE,
)

# ── 定数 ──────────────────────────────────────────────────────────────
WINDOW_W, WINDOW_H = 800, 600
STL_PATH = "sample_car2.stl"
# STL_PATH = "sample_car.stl"
BG_COLOR = (0.15, 0.15, 0.2, 1.0)

CAR_SCALE = 2.0
CAR_SPEED = 0.05
CAR_TURN_SPEED = 2.0   # 旋回速度 (deg/frame)

GRID_CELL = 0.5   # グリッド間隔 (ワールド単位)
GRID_HALF = 30    # 描画範囲: ±30 セル


# ── STL 読み込み ──────────────────────────────────────────────────────
def load_stl(path: str):
    """numpy-stl で STL を読み込み、正規化した頂点・法線と ground_y を返す。"""
    car = mesh.Mesh.from_file(path)
    all_verts = car.vectors.reshape(-1, 3)
    center = (all_verts.max(axis=0) + all_verts.min(axis=0)) / 2
    scale = (all_verts.max(axis=0) - all_verts.min(axis=0)).max()

    triangles = (car.vectors - center) / scale   # shape: (N, 3, 3)
    normals = car.normals                         # shape: (N, 3)

    # STL Z-up: 底面の Z 値 → OpenGL Y 方向のオフセットへ変換
    # glRotatef(-90, 1,0,0) で Z → Y にマップされるため、
    # 車底面が Y=0 に乗るよう ground_y = -z_min * CAR_SCALE とする
    z_min_norm = float((all_verts[:, 2].min() - center[2]) / scale)
    ground_y = -z_min_norm * CAR_SCALE

    return triangles.astype(np.float32), normals.astype(np.float32), ground_y


# ── OpenGL 初期設定 ──────────────────────────────────────────────────
def setup_gl(width: int, height: int):
    glClearColor(*BG_COLOR)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_NORMALIZE)

    glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 2.0, 2.0, 0.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 1.0, 1.0, 1.0])
    glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.2, 0.2, 1.0])

    glLightfv(GL_LIGHT1, GL_POSITION, [-1.0, -1.0, -1.0, 0.0])
    glLightfv(GL_LIGHT1, GL_DIFFUSE,  [0.4, 0.4, 0.5, 1.0])

    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE,   [0.7, 0.7, 0.85, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR,  [0.9, 0.9, 0.9, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, [60.0])

    set_projection(width, height)


def set_projection(width: int, height: int):
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    fov_y, aspect, near, far = 45.0, width / height, 0.01, 500.0
    f = 1.0 / math.tan(math.radians(fov_y) / 2.0)
    glFrustum(-near / f * aspect, near / f * aspect, -near / f, near / f, near, far)
    glMatrixMode(GL_MODELVIEW)
    glViewport(0, 0, width, height)


# ── グリッド描画 ──────────────────────────────────────────────────────
def draw_grid(cam_x: float, cam_z: float):
    """無限に続く水平グリッドをカメラ位置に追従させて描画する。"""
    glDisable(GL_LIGHTING)
    glBegin(GL_LINES)

    # グリッド原点をセルにスナップ → タイリングで無限感を演出
    ox = math.floor(cam_x / GRID_CELL) * GRID_CELL
    oz = math.floor(cam_z / GRID_CELL) * GRID_CELL
    half = GRID_HALF * GRID_CELL

    for i in range(-GRID_HALF, GRID_HALF + 1):
        # 5 セルごとに明るい線
        bright = (i % 5 == 0)
        glColor3f(0.5 if bright else 0.3, 0.5 if bright else 0.3, 0.6 if bright else 0.4)

        x = ox + i * GRID_CELL
        glVertex3f(x, 0.0, oz - half)
        glVertex3f(x, 0.0, oz + half)

    for i in range(-GRID_HALF, GRID_HALF + 1):
        bright = (i % 5 == 0)
        glColor3f(0.5 if bright else 0.3, 0.5 if bright else 0.3, 0.6 if bright else 0.4)

        z = oz + i * GRID_CELL
        glVertex3f(ox - half, 0.0, z)
        glVertex3f(ox + half, 0.0, z)

    glEnd()
    glEnable(GL_LIGHTING)
    glColor3f(1.0, 1.0, 1.0)


# ── モデル描画 ────────────────────────────────────────────────────────
def draw_model(triangles: np.ndarray, normals: np.ndarray):
    glBegin(GL_TRIANGLES)
    for tri, nrm in zip(triangles, normals):
        glNormal3fv(nrm)
        for vert in tri:
            glVertex3fv(vert)
    glEnd()


# ── メインループ ─────────────────────────────────────────────────────
def main():
    triangles, normals, ground_y = load_stl(STL_PATH)

    pygame.init()
    pygame.display.set_mode((WINDOW_W, WINDOW_H), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("STL Viewer")

    setup_gl(WINDOW_W, WINDOW_H)

    rot_x, rot_y = 20.0, -30.0   # カメラ回転角 (deg)
    zoom = -5.0                   # カメラ距離
    dragging = False
    last_mouse = (0, 0)

    car_x, car_z = 0.0, 0.0      # 車のワールド座標 (XZ 平面)
    car_angle = 0.0               # 車の向き (deg, OpenGL Y 軸回転)

    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == K_r:
                    rot_x, rot_y = 20.0, -30.0
                    zoom = -5.0
                    car_angle = 0.0

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    dragging = True
                    last_mouse = event.pos
                elif event.button == 4:
                    zoom = min(zoom + 0.3, -1.0)
                elif event.button == 5:
                    zoom = max(zoom - 0.3, -20.0)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    dx = event.pos[0] - last_mouse[0]
                    dy = event.pos[1] - last_mouse[1]
                    rot_y += dx * 0.5
                    rot_x += dy * 0.5
                    last_mouse = event.pos

        # ── WASD 操作 (車体系基準) ────────────────────────────────────
        keys = pygame.key.get_pressed()

        # A/D: 旋回
        if keys[K_a]:
            car_angle += CAR_TURN_SPEED
        if keys[K_d]:
            car_angle -= CAR_TURN_SPEED

        # W/S: 車体の向きに沿って前進・後退
        # car_angle=0 で -Z 方向を前とし、Y 軸回転で向きを決める
        rad = math.radians(car_angle)
        fwd_x = -math.sin(rad)
        fwd_z = -math.cos(rad)
        if keys[K_w]:
            car_x += fwd_x * CAR_SPEED
            car_z += fwd_z * CAR_SPEED
        if keys[K_s]:
            car_x -= fwd_x * CAR_SPEED
            car_z -= fwd_z * CAR_SPEED

        # ── 描画 ──────────────────────────────────────────────────────
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # ビュー変換: カメラが車を追従しつつ回転
        glTranslatef(0.0, 0.0, zoom)
        glRotatef(rot_x, 1, 0, 0)
        glRotatef(rot_y, 0, 1, 0)
        glTranslatef(-car_x, 0.0, -car_z)

        # グリッド (Y=0 平面、ワールド座標)
        draw_grid(car_x, car_z)

        # 車 (ワールド座標)
        glPushMatrix()
        glTranslatef(car_x, ground_y, car_z)
        glRotatef(car_angle, 0, 1, 0)   # 車体の向き
        glRotatef(-90.0, 1, 0, 0)       # STL Z-up → OpenGL Y-up
        glScalef(CAR_SCALE, CAR_SCALE, CAR_SCALE)
        draw_model(triangles, normals)
        glPopMatrix()

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
