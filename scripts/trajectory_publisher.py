#!/usr/bin/env python3
"""走行軌跡を /traveled_path (nav_msgs/Path) に配信するノード。"""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry, Path
from geometry_msgs.msg import PoseStamped

class TrajectoryPublisher(Node):
    """一定距離ごとに /odom を Path に蓄積する（上限超過分は破棄）。"""
    def __init__(self):
        super().__init__('trajectory_publisher')
        
        self.declare_parameter('frame_id', 'odom')
        self.declare_parameter('min_distance', 0.05)  # [m] この距離以上動いたら記録
        self.declare_parameter('max_jump', 0.5)  # [m] 一気に飛んだらノイズとみなして無視
        self.declare_parameter('max_poses', 10000)  # 軌跡の保持上限
        self.frame_id = self.get_parameter('frame_id').value
        
        self.path_pub = self.create_publisher(Path, '/traveled_path', 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        
        self.path_msg = Path()
        self.path_msg.header.frame_id = self.frame_id
        
        self.last_pose = None
        self.min_distance = self.get_parameter('min_distance').value
        self.max_jump = self.get_parameter('max_jump').value
        self.max_poses = self.get_parameter('max_poses').value

    def odom_callback(self, msg):
        current_pose = msg.pose.pose
        
        if self.last_pose is None:
            self.last_pose = current_pose
            return

        dist = self.calculate_distance(self.last_pose, current_pose)

        # 異常値フィルタ: ノイズとみなして無視
        if dist > self.max_jump:
            return

        # 一定距離動いたら記録
        if dist > self.min_distance:
            pose_stamped = PoseStamped()
            pose_stamped.header = msg.header
            pose_stamped.header.frame_id = self.frame_id
            pose_stamped.pose = current_pose
            
            self.path_msg.poses.append(pose_stamped)
            if len(self.path_msg.poses) > self.max_poses:
                del self.path_msg.poses[0:len(self.path_msg.poses) - self.max_poses]
            self.path_msg.header.stamp = msg.header.stamp
            
            self.path_pub.publish(self.path_msg)
            self.last_pose = current_pose

    def calculate_distance(self, pose1, pose2):
        dx = pose1.position.x - pose2.position.x
        dy = pose1.position.y - pose2.position.y
        return (dx**2 + dy**2)**0.5

def main(args=None):
    rclpy.init(args=args)
    node = TrajectoryPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
