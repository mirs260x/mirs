"""mirs.launch.py: 後方互換プリセット.

実体は mirs_hardware.launch.py に集約. 旧来の `ros2 launch mirs mirs.launch.py`
呼び出しが壊れないよう、推奨プリセット (RSPあり/EKFあり/静的TFなし) で委譲する.

旧来との差分 (意図的バグ修正):
- robot_state_publisher を有効化 (旧: コメントアウト)
- EKF local を有効化 (旧: コメントアウト)
- static odom->base_link / base_link->laser を無効化 (旧: 有効でTF競合)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_share = get_package_share_directory('mirs')

    esp_port = DeclareLaunchArgument(
        'esp_port', default_value='/dev/ttyUSB1',
        description='Set esp32 usb port.')
    lidar_port = DeclareLaunchArgument(
        'lidar_port', default_value='/dev/ttyUSB0',
        description='Set lidar usb port.')
    use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='Use simulated clock if true.')

    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'mirs_hardware.launch.py')
        ),
        launch_arguments={
            'esp_port': LaunchConfiguration('esp_port'),
            'lidar_port': LaunchConfiguration('lidar_port'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'enable_lidar': 'true',
            'enable_odometry': 'true',
            'enable_parameter_publisher': 'true',
            'enable_micro_ros': 'true',
            'enable_robot_state_publisher': 'true',
            'urdf_file': 'mirs_2.urdf',
            'enable_ekf_local': 'true',
            'enable_static_odom_tf': 'false',
            'enable_static_laser_tf': 'false',
        }.items(),
    )

    ld = LaunchDescription()
    ld.add_action(esp_port)
    ld.add_action(lidar_port)
    ld.add_action(use_sim_time)
    ld.add_action(hardware)
    return ld
