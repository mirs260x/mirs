"""mirs_hardware.launch.py: ハードウェア層の単一真実 (Single Source of Truth).

parameter / micro_ros / sllidar 定義を集約.
機体は単純な差動二輪として扱う (URDFなし。静的TF運用)。
(オドメトリ計算はESP32側に移管し、本ファイルでは扱わない)

上位launch (slam/nav) はこのファイルを直接Includeし、
mirs.launch.py は後方互換のための薄いプリセットとして残す.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('mirs')

    # --- 引数 ---
    esp_port = DeclareLaunchArgument(
        'esp_port', default_value='/dev/ttyUSB1',
        description='ESP32 USB port.')
    lidar_port = DeclareLaunchArgument(
        'lidar_port', default_value='/dev/ttyUSB0',
        description='LiDAR USB port.')
    lidar_baudrate = DeclareLaunchArgument(
        'lidar_baudrate', default_value='256000',
        description='LiDAR baudrate.')
    use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='Use simulated clock if true.')

    enable_lidar = DeclareLaunchArgument(
        'enable_lidar', default_value='true',
        description='Enable LiDAR driver.')
    enable_parameter_publisher = DeclareLaunchArgument(
        'enable_parameter_publisher', default_value='true',
        description='Enable parameter_publisher.')
    enable_micro_ros = DeclareLaunchArgument(
        'enable_micro_ros', default_value='true',
        description='Enable micro-ROS agent.')

    enable_ekf_local = DeclareLaunchArgument(
        'enable_ekf_local', default_value='true',
        description='Enable robot_localization EKF (odom->base_link). '
                    'SLAM/Nav2使用時はtrue推奨.')
    ekf_config_file = DeclareLaunchArgument(
        'ekf_config_file',
        default_value=os.path.join(pkg_share, 'config', 'ekf', 'ekf_params.yaml'),
        description='EKF config file (absolute path推奨).')

    # 静的TF運用が基本。odom->base_linkはEKFが出すためfalse維持。
    enable_static_odom_tf = DeclareLaunchArgument(
        'enable_static_odom_tf', default_value='false',
        description='Publish static odom->base_link (conflicts with EKF, keep false).')
    enable_static_laser_tf = DeclareLaunchArgument(
        'enable_static_laser_tf', default_value='true',
        description='Publish static base_link->laser.')
    # base_footprint->base_linkの静的TF。
    enable_static_footprint_tf = DeclareLaunchArgument(
        'enable_static_footprint_tf', default_value='true',
        description='Publish static base_footprint->base_link.')

    config_file_path = os.path.join(pkg_share, 'config', 'config.yaml')

    # --- ノード (オドメトリ計算はESP32側。/odomはmicro-ROS経由) ---
    parameter_node = Node(
        package='mirs',
        executable='parameter_publisher',
        name='parameter_publisher',
        output='screen',
        parameters=[config_file_path, {'use_sim_time': LaunchConfiguration('use_sim_time')}],
        condition=IfCondition(LaunchConfiguration('enable_parameter_publisher')),
    )

    micro_ros = Node(
        package='micro_ros_agent',
        executable='micro_ros_agent',
        name='micro_ros_agent',
        output='screen',
        arguments=['serial', '--dev', LaunchConfiguration('esp_port'), '-v6'],
        condition=IfCondition(LaunchConfiguration('enable_micro_ros')),
    )

    sllidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('sllidar_ros2'),
                         'launch', 'sllidar_s1_launch.py')
        ),
        launch_arguments={
            'serial_port': LaunchConfiguration('lidar_port'),
            'serial_baudrate': LaunchConfiguration('lidar_baudrate'),
        }.items(),
        condition=IfCondition(LaunchConfiguration('enable_lidar')),
    )

    ekf_node_local = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node_local',
        output='screen',
        parameters=[LaunchConfiguration('ekf_config_file'),
                    {'use_sim_time': LaunchConfiguration('use_sim_time')}],
        remappings=[('/odometry/filtered', '/odometry/local')],
        condition=IfCondition(LaunchConfiguration('enable_ekf_local')),
    )

    def static_tf_node(name, arguments, condition):
        """tf2_ros static_transform_publisherの定型Node。"""
        return Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name=name,
            output='screen',
            arguments=arguments,
            condition=condition,
        )

    static_odom_tf_node = static_tf_node(
        'static_transform_publisher_odom_base_link',
        ['0', '0', '0', '0', '0', '0', 'odom', 'base_link'],
        IfCondition(LaunchConfiguration('enable_static_odom_tf')),
    )

    static_laser_tf_node = static_tf_node(
        'static_transform_publisher_base_laser',
        # z = 0.06 + 0.178/2 + 0.051/2 = 0.1745, rpy 0 0 0
        ['--x', '0', '--y', '0', '--z', '0.1745',
         '--roll', '0', '--pitch', '0', '--yaw', '0',
         '--frame-id', 'base_link', '--child-frame-id', 'laser'],
        IfCondition(LaunchConfiguration('enable_static_laser_tf')),
    )

    static_footprint_tf_node = static_tf_node(
        'static_transform_publisher_footprint_base_link',
        # z = 0.0665*2 + 0.02 + 0.178/2 = 0.242, rpy 0 0 0
        ['--x', '0', '--y', '0', '--z', '0.242',
         '--roll', '0', '--pitch', '0', '--yaw', '0',
         '--frame-id', 'base_footprint', '--child-frame-id', 'base_link'],
        IfCondition(LaunchConfiguration('enable_static_footprint_tf')),
    )

    ld = LaunchDescription()
    for a in (esp_port, lidar_port, lidar_baudrate, use_sim_time,
              enable_lidar, enable_parameter_publisher,
              enable_micro_ros,
              enable_ekf_local, ekf_config_file,
              enable_static_odom_tf, enable_static_laser_tf,
              enable_static_footprint_tf):
        ld.add_action(a)

    for n in (parameter_node, micro_ros, sllidar_launch,
              ekf_node_local,
              static_odom_tf_node, static_laser_tf_node,
              static_footprint_tf_node):
        ld.add_action(n)

    return ld
