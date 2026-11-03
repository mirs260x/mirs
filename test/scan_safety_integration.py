"""専用ドメインとトピックで安全ゲートを試し、実機への指令を送らず停止・復帰を検証する。"""

import os
import subprocess
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


def main():
    """第1引数の安全ゲート実行ファイルを起動し、障害物・入力途絶を確認する。"""
    os.environ['ROS_DOMAIN_ID'] = str(120 + os.getpid() % 80)
    prefix = '/guard_test_' + str(os.getpid())
    process = subprocess.Popen([
        sys.argv[1], '--ros-args',
        '-p', 'scan_topic:=' + prefix + '/scan',
        '-p', 'input_cmd_vel_topic:=' + prefix + '/input',
        '-p', 'output_cmd_vel_topic:=' + prefix + '/output',
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rclpy.init()
    node = rclpy.create_node('guard_test_' + str(os.getpid()))
    scan_pub = node.create_publisher(LaserScan, prefix + '/scan', qos_profile_sensor_data)
    cmd_pub = node.create_publisher(Twist, prefix + '/input', 10)
    received = []
    subscription = node.create_subscription(Twist, prefix + '/output', received.append, 10)

    def check(distance, command, expected, duration=.8):
        """距離[m]と速度指令[m/s]を継続入力し、期間末の出力を確認する。"""
        received.clear()
        end = time.monotonic() + duration
        while time.monotonic() < end:
            if distance is not None:
                scan = LaserScan()
                scan.angle_min = -.1
                scan.angle_increment = .1
                scan.range_min = .05
                scan.range_max = 10.
                scan.ranges = [distance] * 3
                scan_pub.publish(scan)
            if command:
                msg = Twist()
                msg.linear.x = .2
                cmd_pub.publish(msg)
            rclpy.spin_once(node, timeout_sec=.03)
        assert received, 'no safety output'
        assert all(abs(x.linear.x - expected) < 1e-5 for x in received[-3:]), (
            distance, command, [x.linear.x for x in received[-3:]])

    try:
        # DDSの接続待ちには停止出力だけを使う。
        check(None, False, 0., duration=1.5)
        check(1., True, .2)
        check(.2, True, 0.)
        check(.4, True, 0.)  # 解除閾値0.50mまで停止を維持する。
        check(.6, True, .2)
        check(None, True, 0.)  # スキャン途絶は0.5s以内に停止する。
        check(.6, True, .2)
        check(.6, False, 0.)  # 指令途絶も0.5s以内に停止する。
        print('scan safety: startup, obstacle, hysteresis, recovery, scan/command timeout passed')
    finally:
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == '__main__':
    main()
