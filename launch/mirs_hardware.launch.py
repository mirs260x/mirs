"""mirs_hardware.launch.py: ハードウェア層の単一真実 (Single Source of Truth).

従来 mirs.launch.py / mirs_odom_only.launch.py / mirs_minimum.launch.py に
三重複製されていた odometry / parameter / micro_ros / sllidar 定義を集約.

上位launch (slam/nav/system_bringup*) はこのファイルを直接Includeし、
mirs.launch.py 等は後方互換のための薄いプリセットとして残す.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


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
    enable_odometry = DeclareLaunchArgument(
        'enable_odometry', default_value='true',
        description='Enable odometry_publisher.')
    enable_parameter_publisher = DeclareLaunchArgument(
        'enable_parameter_publisher', default_value='true',
        description='Enable parameter_publisher.')
    enable_micro_ros = DeclareLaunchArgument(
        'enable_micro_ros', default_value='true',
        description='Enable micro-ROS agent.')

    enable_robot_state_publisher = DeclareLaunchArgument(
        'enable_robot_state_publisher', default_value='true',
        description='Enable robot_state_publisher (URDF). '
                    'True推奨。True時は static base_link->laser を使わないこと.')
    urdf_file = DeclareLaunchArgument(
        'urdf_file', default_value='mirs_2.urdf',
        description='URDF file name under mirs/urdf (xacroで処理される).')

    enable_ekf_local = DeclareLaunchArgument(
        'enable_ekf_local', default_value='true',
        description='Enable robot_localization EKF (odom->base_link). '
                    'SLAM/Nav2使用時はtrue推奨.')
    ekf_config_file = DeclareLaunchArgument(
        'ekf_config_file',
        default_value=os.path.join(pkg_share, 'config', 'ekf', 'ekf_params.yaml'),
        description='EKF config file (absolute path推奨).')

    # 下記2つはデバッグ用。通常はfalse。EKFと同時有効化はTF競合になるため禁止.
    enable_static_odom_tf = DeclareLaunchArgument(
        'enable_static_odom_tf', default_value='false',
        description='Publish static odom->base_link (debug only, conflicts with EKF).')
    enable_static_laser_tf = DeclareLaunchArgument(
        'enable_static_laser_tf', default_value='false',
        description='Publish static base_link->laser (legacy, conflicts with URDF).')

    config_file_path = os.path.join(pkg_share, 'config', 'config.yaml')
    urdf_path = os.path.join(
        pkg_share, 'urdf', LaunchConfiguration('urdf_file'))
    # NOTE: LaunchConfigurationは文字列結合できないため、RSP用には
    # urdf_fileのデフォルト値解決をNode側に委ねず、Commandで遅延評価する.
    # ここでは代表パス (mirs_2.urdf) を使い、urdf_file変更時は下記robot_descが追従するよう
    # Command substitutionで組み立てる.
    robot_desc = ParameterValue(
        Command(['xacro ', pkg_share, '/urdf/', LaunchConfiguration('urdf_file')]),
        value_type=str)

    # --- ノード ---
    odometry_node = Node(
        package='mirs',
        executable='odometry_publisher',
        name='odometry_publisher',
        output='screen',
        parameters=[config_file_path, {'use_sim_time': LaunchConfiguration('use_sim_time')}],
        condition=IfCondition(LaunchConfiguration('enable_odometry')),
    )

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

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc,
                     'use_sim_time': LaunchConfiguration('use_sim_time')}],
        condition=IfCondition(LaunchConfiguration('enable_robot_state_publisher')),
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

    static_odom_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_transform_publisher_odom_base_link',
        arguments=['0', '0', '0', '0', '0', '0', 'odom', 'base_link'],
        condition=IfCondition(LaunchConfiguration('enable_static_odom_tf')),
    )

    static_laser_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_transform_publisher_base_laser',
        output='screen',
        arguments=['--x', '0', '--y', '0', '--z', '0.3',
                   '--roll', '1.5707963267948966', '--pitch', '0', '--yaw', '0',
                   '--frame-id', 'base_link', '--child-frame-id', 'laser'],
        condition=IfCondition(LaunchConfiguration('enable_static_laser_tf')),
    )

    _ = urdf_path  # 将来の拡張用 (現状はCommandで遅延解決するため未使用)

    ld = LaunchDescription()
    for a in (esp_port, lidar_port, lidar_baudrate, use_sim_time,
              enable_lidar, enable_odometry, enable_parameter_publisher,
              enable_micro_ros, enable_robot_state_publisher, urdf_file,
              enable_ekf_local, ekf_config_file,
              enable_static_odom_tf, enable_static_laser_tf):
        ld.add_action(a)

    for n in (odometry_node, parameter_node, micro_ros, sllidar_launch,
              robot_state_publisher_node, ekf_node_local,
              static_odom_tf_node, static_laser_tf_node):
        ld.add_action(n)

    return ld
