"""Odometry math tests (mirrors src/odometry_publisher.cpp).

ROS不要の純粋計算テスト。C++側の式と1:1に対応させる:
  delta_rad = (delta_count / count_per_rev) * 2*pi
  left/right_distance = delta_rad * wheel_radius
  delta_distance = (l+r)/2, delta_theta = (r-l)/wheel_base
  x += d*cos(theta), y += d*sin(theta), theta += dtheta
  vx = d/0.05, wz = dtheta/0.05
"""
import math

WHEEL_RADIUS = 0.0391
WHEEL_BASE = 0.39
COUNT_PER_REV = 4096.0
DT = 0.05


def step(x, y, theta, dl_counts, dr_counts,
         wheel_radius=WHEEL_RADIUS, wheel_base=WHEEL_BASE,
         count_per_rev=COUNT_PER_REV, dt=DT):
    dl_rad = (dl_counts / count_per_rev) * 2.0 * math.pi
    dr_rad = (dr_counts / count_per_rev) * 2.0 * math.pi
    l = dl_rad * wheel_radius
    r = dr_rad * wheel_radius
    d = (l + r) / 2.0
    dtheta = (r - l) / wheel_base
    theta2 = theta + dtheta
    return (x + d * math.cos(theta2), y + d * math.sin(theta2), theta2,
            d / dt, dtheta / dt)


def test_straight_no_rotation():
    x, y, th, vx, wz = step(0, 0, 0, 4096, 4096)
    expected = 2 * math.pi * WHEEL_RADIUS  # 1回転分
    assert th == 0.0
    assert y == 0.0
    assert x == expected
    assert vx == expected / DT
    assert wz == 0.0


def test_zero_delta_stays():
    x, y, th, vx, wz = step(1.0, 2.0, 0.5, 0, 0)
    assert (x, y, th) == (1.0, 2.0, 0.5)
    assert vx == 0.0 and wz == 0.0


def test_spin_in_place():
    # 左右逆回転: 移動なし・thetaのみ変化
    x, y, th, vx, wz = step(0, 0, 0, -2048, 2048)
    assert x == 0.0 and y == 0.0
    # r-l = 2 * (0.5回転分の距離)
    one_rev = 2 * math.pi * WHEEL_RADIUS
    assert th == one_rev / WHEEL_BASE
    assert vx == 0.0
    assert wz != 0.0


def test_velocity_scale_matches_timer():
    # 50msタイマーなので/0.05。コメントの0.1は誤り(回帰防止)。
    import ast
    src = open("src/odometry_publisher.cpp").read()
    assert "std::chrono::milliseconds(50)" in src
    assert "/ 0.05" in src
    tree = ast.parse(open("scripts/odom_linear_test.py").read())  # 構文健全性
    assert tree is not None
