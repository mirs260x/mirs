#!/usr/bin/env python3
"""オドメトリ直進精度の手動テストノード（3m前進して停止）。"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import math
import time

class OdomLinearTest(Node):
    """P制御で目標距離だけ前進するテストノード。"""
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
        self.current_distance = 0.0
        self.target_distance = 3.0
        self.is_moving = False
        
        # 制御ループ
        self.timer = self.create_timer(0.1, self.control_loop)
        
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
            # 目標到達
            twist.linear.x = 0.0
            self.publisher_.publish(twist)
            self.get_logger().info(f'Target Reached! Final Distance: {self.current_distance:.3f} m')
            self.is_moving = False
            # 少し待ってから終了
            time.sleep(1.0)
            raise SystemExit
        else:
            # P制御的な速度調整 (最大0.3m/s, 最小0.05m/s)
            speed = 0.5 * remaining_distance
            speed = max(0.05, min(0.3, speed))
            
            twist.linear.x = speed
            self.publisher_.publish(twist)
            
            # ログ出力 (0.5mごとに表示など間引いても良いが、今回は毎回出す)
            self.get_logger().info(f'Distance: {self.current_distance:.3f} m / {self.target_distance:.1f} m (Speed: {speed:.3f} m/s)')

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
        # 安全のため停止コマンドを送る
        node.publisher_.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
