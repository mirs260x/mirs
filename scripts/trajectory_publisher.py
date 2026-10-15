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


"""Publish the traveled path as a nav_msgs/Path message."""
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, Path
import rclpy
from rclpy.node import Node


class TrajectoryPublisher(Node):
    """Accumulate /odom poses at fixed distance intervals."""

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
