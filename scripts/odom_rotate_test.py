#!/usr/bin/env python3
"""オドメトリ回転精度の手動テストノード（一回転して停止）。"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import math
import time
from tf_transformations import euler_from_quaternion

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
        self.accumulated_angle = 0.0
        self.target_angle = 2.0 * math.pi # 360 degrees in radians
        self.is_moving = False
        
        # 制御ループ
        self.timer = self.create_timer(0.1, self.control_loop)
        
        self.get_logger().info('Odom Rotate Test Node Started')
        self.get_logger().info(f'Target Angle: {math.degrees(self.target_angle):.1f} degrees')
        self.get_logger().info('Waiting for /odom data...')

    def get_yaw(self, msg):
        orientation_q = msg.pose.pose.orientation
        orientation_list = [orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w]
        (roll, pitch, yaw) = euler_from_quaternion(orientation_list)
        return yaw

    def odom_callback(self, msg):
        current_yaw = self.get_yaw(msg)
        
        if self.last_yaw is None:
            self.last_yaw = current_yaw
            self.get_logger().info(f'Start Yaw: {math.degrees(current_yaw):.3f} deg')
            self.is_moving = True
            return

        # 角度の差分を計算 (ラップアラウンド処理)
        delta = current_yaw - self.last_yaw
        
        # -PIからPIの範囲に正規化されているため、急激な変化(PI -> -PIなど)を補正
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
        
        # 絶対値で比較
        remaining_angle = self.target_angle - abs(self.accumulated_angle)
        
        if remaining_angle <= 0:
            # 目標到達
            twist.angular.z = 0.0
            self.publisher_.publish(twist)
            final_deg = math.degrees(self.accumulated_angle)
            self.get_logger().info(f'Target Reached! Final Angle: {final_deg:.3f} deg')
            self.is_moving = False
            time.sleep(1.0)
            raise SystemExit
        else:
            # P制御的な速度調整 (最大0.5rad/s, 最小0.1rad/s)
            speed = 0.5 * remaining_angle
            speed = max(0.1, min(0.5, speed))
            
            # 左回転(反時計回り)
            twist.angular.z = speed
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
