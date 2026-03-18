# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 実行

```bash
uv run main.py
```

## 依存パッケージ追加

```bash
uv add <package>
```

## アーキテクチャ

`main.py` 1ファイル構成の STL ビューア。

| 関数             | 役割                                                                                        |
| ---------------- | --------------------------------------------------------------------                        |
| `load_stl`       | numpy-stl で STL を読み込み、バウンディングボックスで正規化。底面の ground_y を計算して返す |
| `setup_gl`       | ライティング・マテリアル初期化                                                              |
| `set_projection` | `gluPerspective` の代替として `glFrustum` で透視投影を設定 (WSL では libGLU 不在のため)     |
| `draw_grid`      | カメラ位置をセルにスナップして追従させることで「無限グリッド」を演出                        |
| `draw_model`     | 即時モード (glBegin/glEnd) でポリゴン描画                                                   |
| `main`           | イベントループ・状態管理・描画呼び出し                                                      |

## 座標系

STL は Z-up、OpenGL は Y-up。描画時に `glRotatef(-90, 1, 0, 0)` で変換している。
車体の向き (`car_angle`) は OpenGL Y 軸回転で管理し、`-90` 変換より前に適用する。

## 操作

| 入力             | 動作                   |
| ---------------- | ---------------------  |
| マウス左ドラッグ | カメラ回転             |
| マウスホイール   | ズーム                 |
| W / S            | 車体前進 / 後退        |
| A / D            | 車体左旋回 / 右旋回    |
| R                | 視点・車体向きリセット |
| ESC              | 終了                   |
