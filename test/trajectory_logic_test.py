"""TrajectoryPublisher logic tests (ROSなしで実スクリプトをimport).

scripts/trajectory_publisher.py は rclpy に依存するため、
sys.modules に軽量スタブを差してから読み込む。
テスト対象: calculate_distance / 5cm記録閾値 / 0.5mジャンプ無視。
"""
import sys
import types
from unittest.mock import MagicMock


def _install_ros_stubs():
    if "rclpy" in sys.modules and hasattr(sys.modules["rclpy"], "_mirs_stub"):
        return
    rclpy = types.ModuleType("rclpy")
    rclpy._mirs_stub = True
    rclpy.init = lambda *a, **k: None
    rclpy.spin = lambda *a, **k: None
    rclpy.shutdown = lambda *a, **k: None

    node_mod = types.ModuleType("rclpy.node")

    class Node:
        def __init__(self, name):
            self._name = name
            self._params = {"frame_id": "odom"}

        def declare_parameter(self, name, value):
            self._params[name] = value

        def get_parameter(self, name):
            m = MagicMock()
            m.value = self._params[name]
            return m

        def create_publisher(self, *a, **k):
            m = MagicMock()
            m.published = []
            orig = m.publish
            m.publish = lambda msg: (m.published.append(msg), orig(msg))
            return m

        def create_subscription(self, *a, **k):
            return MagicMock()

        def get_logger(self):
            return MagicMock()

        def destroy_node(self):
            pass

    node_mod.Node = Node
    rclpy.node = node_mod

    nav_msgs = types.ModuleType("nav_msgs")
    nav_msgs_msg = types.ModuleType("nav_msgs.msg")

    class _Pos:
        def __init__(self, x=0.0, y=0.0):
            self.x, self.y = x, y

    class _Pose:
        def __init__(self, x=0.0, y=0.0):
            self.position = _Pos(x, y)

    class Odometry:
        pass

    class Path:
        def __init__(self):
            self.header = MagicMock()
            self.poses = []

    class PoseStamped:
        def __init__(self):
            self.header = MagicMock()
            self.pose = None

    nav_msgs_msg.Odometry = Odometry
    nav_msgs_msg.Path = Path
    nav_msgs_msg.PoseStamped = PoseStamped

    geom = types.ModuleType("geometry_msgs")
    geom_msg = types.ModuleType("geometry_msgs.msg")
    geom_msg.PoseStamped = PoseStamped

    sys.modules["rclpy"] = rclpy
    sys.modules["rclpy.node"] = node_mod
    sys.modules["nav_msgs"] = nav_msgs
    sys.modules["nav_msgs.msg"] = nav_msgs_msg
    sys.modules["geometry_msgs"] = geom
    sys.modules["geometry_msgs.msg"] = geom_msg


_install_ros_stubs()

import importlib.util

SPEC = importlib.util.spec_from_file_location(
    "trajectory_publisher", "scripts/trajectory_publisher.py")
_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(_mod)


def _odom(x, y):
    msg = MagicMock()
    msg.header.stamp = "t"
    msg.pose.pose.position.x = x
    msg.pose.pose.position.y = y
    msg.pose.pose = msg.pose.pose
    # 実コードは msg.pose.pose をそのまま保持するので参照を渡す
    return msg


def test_calculate_distance():
    node = _mod.TrajectoryPublisher.__new__(_mod.TrajectoryPublisher)
    a = MagicMock()
    a.position.x, a.position.y = 0.0, 0.0
    b = MagicMock()
    b.position.x, b.position.y = 3.0, 4.0
    assert node.calculate_distance(a, b) == 5.0


def test_records_only_beyond_5cm():
    node = _mod.TrajectoryPublisher()
    node.odom_callback(_odom(0, 0))       # 初回はlast_pose設定のみ
    assert len(node.path_msg.poses) == 0
    node.odom_callback(_odom(0.01, 0))    # 1cm: 記録しない
    assert len(node.path_msg.poses) == 0
    node.odom_callback(_odom(0.06, 0))    # 6cm: 記録
    assert len(node.path_msg.poses) == 1


def test_jump_over_50cm_ignored():
    node = _mod.TrajectoryPublisher()
    node.odom_callback(_odom(0, 0))
    node.odom_callback(_odom(10.0, 0))    # ジャンプは無視
    assert len(node.path_msg.poses) == 0
    # last_poseが更新されていないこと (=次に近傍点が来たら記録される)
    node.odom_callback(_odom(0.06, 0))
    assert len(node.path_msg.poses) == 1
