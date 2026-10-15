#!/usr/bin/env python3

# Copyright 2026 mirs260x
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


"""Odometer straight-line accuracy test node (move 3 m and stop)."""

import math
import time

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node

TIMER_PERIOD = 0.1  # [s] 制御周期
TARGET_DISTANCE = 3.0  # [m] 目標移動距離
P_GAIN = 0.5  # Pゲイン [1/s]
MAX_SPEED = 0.3  # [m/s] 指令上限
MIN_SPEED = 0.05  # [m/s] 指令下限（静摩擦に勝つため）


class OdomLinearTest(Node):
    """P-control test node that drives forward to a target distance."""

    def __init__(self):
        super().__init__('odom_linear_test')

        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        self.subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10)

        self.start_x = None
        self.start_y = None
        self.current_distance = 0.0  # [m] 起点からの移動距離
        self.target_distance = TARGET_DISTANCE  # [m]
        self.is_moving = False

        self.timer = self.create_timer(TIMER_PERIOD, self.control_loop)

        self.get_logger().info('Odom Linear Test Node Started')
        self.get_logger().info(f'Target Distance: {self.target_distance} meters')
        self.get_logger().info('Waiting for /odom data...')

    def odom_callback(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y

        if self.start_x is None:
            self.start_x = x
            self.start_y = y
            self.get_logger().info(f'Start Position: x={x:.3f}, y={y:.3f}')
            self.is_moving = True
            return

        dx = x - self.start_x
        dy = y - self.start_y
        self.current_distance = math.sqrt(dx*dx + dy*dy)

    def control_loop(self):
        if not self.is_moving:
            return

        twist = Twist()

        remaining_distance = self.target_distance - self.current_distance

        if remaining_distance <= 0:
            twist.linear.x = 0.0
            self.publisher_.publish(twist)
            self.get_logger().info(
                f'Target Reached! Final Distance: {self.current_distance:.3f} m')
            self.is_moving = False
            time.sleep(1.0)
            raise SystemExit
        else:
            speed = P_GAIN * remaining_distance
            speed = max(MIN_SPEED, min(MAX_SPEED, speed))

            twist.linear.x = speed
            self.publisher_.publish(twist)

            self.get_logger().info(
                f'Distance: {self.current_distance:.3f} m / '
                f'{self.target_distance:.1f} m (Speed: {speed:.3f} m/s)')


def main(args=None):
    rclpy.init(args=args)
    node = OdomLinearTest()

    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    except Exception as e:
        print(e)
    finally:
        # 停止コマンドを送って終了する
        node.publisher_.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
