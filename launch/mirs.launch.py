"""mirs.launch.py: 後方互換プリセット.

実体は mirs_hardware.launch.py に集約. 旧来の `ros2 launch mirs mirs.launch.py`
呼び出しが壊れないよう委譲する.

基本方針 (静的TF運用・差動二輪):
- EKF local は有効 (odom->base_footprint)
- static base_footprint->base_link / base_link->laser を有効
- オドメトリ計算はESP32側 (/odomはmicro-ROS経由)
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
    enable_static_laser_tf = DeclareLaunchArgument(
        'enable_static_laser_tf', default_value='true',
        description='Publish static base_link->laser.')
    enable_static_odom_tf = DeclareLaunchArgument(
        'enable_static_odom_tf', default_value='false',
        description='Publish static odom->base_link (EKFと競合するためfalse維持).')
    enable_static_footprint_tf = DeclareLaunchArgument(
        'enable_static_footprint_tf', default_value='true',
        description='Publish static base_footprint->base_link.')
    enable_lidar = DeclareLaunchArgument(
        'enable_lidar', default_value='true',
        description='Enable LiDAR driver.')
    enable_micro_ros = DeclareLaunchArgument(
        'enable_micro_ros', default_value='true',
        description='Enable micro-ROS agent.')

    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'mirs_hardware.launch.py')
        ),
        launch_arguments={
            'esp_port': LaunchConfiguration('esp_port'),
            'lidar_port': LaunchConfiguration('lidar_port'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'enable_lidar': LaunchConfiguration('enable_lidar'),
            'enable_parameter_publisher': 'true',
            'enable_micro_ros': LaunchConfiguration('enable_micro_ros'),
            'enable_ekf_local': 'true',
            'enable_static_odom_tf': LaunchConfiguration('enable_static_odom_tf'),
            'enable_static_laser_tf': LaunchConfiguration('enable_static_laser_tf'),
            'enable_static_footprint_tf': LaunchConfiguration('enable_static_footprint_tf'),
        }.items(),
    )

    ld = LaunchDescription()
    ld.add_action(esp_port)
    ld.add_action(lidar_port)
    ld.add_action(use_sim_time)
    ld.add_action(enable_static_laser_tf)
    ld.add_action(enable_static_odom_tf)
    ld.add_action(enable_static_footprint_tf)
    ld.add_action(enable_lidar)
    ld.add_action(enable_micro_ros)
    ld.add_action(hardware)
    return ld
