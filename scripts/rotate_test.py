#!/usr/bin/env python3
"""オドメトリ回転精度の手動テストノード（一回転して停止）。"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import math
import time
from tf_transformations import euler_from_quaternion

TIMER_PERIOD = 0.1  # [s] 制御周期
TARGET_ANGLE = 2.0 * math.pi  # [rad] 目標回転角（一回転）
P_GAIN = 0.5  # Pゲイン [1/s]
MAX_SPEED = 0.5  # [rad/s] 指令上限
MIN_SPEED = 0.1  # [rad/s] 指令下限

class OdomRotateTest(Node):
    """P制御で目標角度だけ回転するテストノード。"""
    def __init__(self):
        super().__init__('odom_rotate_test')

        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        self.subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10)

        self.last_yaw = None
        self.accumulated_angle = 0.0  # [rad] 積算回転角
        self.target_angle = TARGET_ANGLE  # [rad]
        self.is_moving = False

        self.timer = self.create_timer(TIMER_PERIOD, self.control_loop)

        self.get_logger().info('Odom Rotate Test Node Started')
        self.get_logger().info(f'Target Angle: {math.degrees(self.target_angle):.1f} degrees')
        self.get_logger().info('Waiting for /odom data...')

    def odom_callback(self, msg):
        orientation_q = msg.pose.pose.orientation
        orientation_list = [orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w]
        ( _roll, _pitch, current_yaw) = euler_from_quaternion(orientation_list)

        if self.last_yaw is None:
            self.last_yaw = current_yaw
            self.get_logger().info(f'Start Yaw: {math.degrees(current_yaw):.3f} deg')
            self.is_moving = True
            return

        # ±PI境界の跳びを補正して積算する
        delta = current_yaw - self.last_yaw
        if delta < -math.pi:
            delta += 2 * math.pi
        elif delta > math.pi:
            delta -= 2 * math.pi

        self.accumulated_angle += delta
        self.last_yaw = current_yaw

    def control_loop(self):
        if not self.is_moving:
            return

        twist = Twist()

        remaining_angle = self.target_angle - abs(self.accumulated_angle)

        if remaining_angle <= 0:
            twist.angular.z = 0.0
            self.publisher_.publish(twist)
            final_deg = math.degrees(self.accumulated_angle)
            self.get_logger().info(f'Target Reached! Final Angle: {final_deg:.3f} deg')
            self.is_moving = False
            time.sleep(1.0)
            raise SystemExit
        else:
            speed = P_GAIN * remaining_angle
            speed = max(MIN_SPEED, min(MAX_SPEED, speed))

            twist.angular.z = speed  # 左回転（反時計回り）
            self.publisher_.publish(twist)

            current_deg = math.degrees(self.accumulated_angle)
            self.get_logger().info(f'Angle: {current_deg:.1f} / 360.0 deg (Speed: {speed:.3f} rad/s)')

def main(args=None):
    rclpy.init(args=args)
    node = OdomRotateTest()

    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    except Exception as e:
        print(e)
    finally:
        node.publisher_.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
