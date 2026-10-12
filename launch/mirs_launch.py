"""mirs_launch.py
上位launchはこのファイルを直接Includeすること
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml

def generate_launch_description():

    #ファイル指定
    mirs_pkg = FindPackageShare('mirs')
    nav2_bringup_pkg = FindPackageShare('nav2_bringup')
    rviz_config_file = PathJoinSubstitution([nav2_bringup_pkg, 'rviz', 'nav2_default_view.rviz'])
    nav2_params_file = PathJoinSubstitution([mirs_pkg, 'config', 'navigation', 'nav2_params.yaml'])
    ekf_config_file = PathJoinSubstitution([mirs_pkg, 'config', 'ekf', 'ekf_params.yaml'])

    return LaunchDescription([

        DeclareLaunchArgument(
            'ekf_config_file',
            default_value=PathJoinSubstitution([mirs_pkg, 'config', 'ekf', 'ekf_params.yaml']),
            ),
        # ポート設定
        DeclareLaunchArgument(
            'esp_port', default_value='/dev/ttyUSB1'
            ),
        DeclareLaunchArgument(
            'lidar_port', default_value='/dev/ttyUSB0'
            ),
        DeclareLaunchArgument(
            'lidar_baudrate', default_value='256000'
            ),

        # 真偽値
        DeclareLaunchArgument(
            'use_sim_time', default_value='false'
            ),
        DeclareLaunchArgument(
            'enable_lidar', default_value='true'
            ),
        DeclareLaunchArgument(
            'enable_parameter_publisher', default_value='true'
            ),
        DeclareLaunchArgument(
            'enable_micro_ros', default_value='true'
            ),
        DeclareLaunchArgument(
            'enable_ekf_local', default_value='true'
            ),
        # EKFを使うならodom->base_linkはfalse
        DeclareLaunchArgument(
            'enable_static_odom_to_base_footprint_tf', default_value='false'
            ),
        DeclareLaunchArgument(
            'enable_static_base_link_to_laser_tf', default_value='true'
            ),
        DeclareLaunchArgument(
            'enable_static_base_footprint_to_base_link_tf', default_value='true',
            ),
        DeclareLaunchArgument(
            'enable_static_base_link_to_imu_link_tf', default_value='true',
            ),
        DeclareLaunchArgument(
            'use_rviz', default_value='true',
            ),

        Node(
            package='mirs',
            executable='parameter_publisher',
            name='parameter_publisher',
            output='screen',
            parameters=[PathJoinSubstitution([mirs_pkg, 'config', 'config.yaml']), {'use_sim_time': LaunchConfiguration('use_sim_time')}],
            condition=IfCondition(LaunchConfiguration('enable_parameter_publisher')),
            ),

        Node(
            package='micro_ros_agent',
            executable='micro_ros_agent',
            name='micro_ros_agent',
            output='screen',
            arguments=['serial', '--dev', LaunchConfiguration('esp_port'), '-v6'],
            condition=IfCondition(LaunchConfiguration('enable_micro_ros')),
            ),

        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_local',
            output='screen',
            parameters=[LaunchConfiguration('ekf_config_file'), {'use_sim_time': LaunchConfiguration('use_sim_time')}],
            remappings=[('/odometry/filtered', '/odometry/local')],
            condition=IfCondition(LaunchConfiguration('enable_ekf_local')),
            ),

        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='enable_static_odom_to_base_footprint_tf',
            output='screen',
            arguments=
            ['0', '0', '0', '0', '0', '0', 'odom', 'base_footprint'],
            condition=IfCondition(LaunchConfiguration('enable_static_odom_to_base_footprint_tf')),
            ),

        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='enable_static_base_link_to_laser_tf',
            output='screen',
            arguments=['--x', '0', '--y', '0', '--z', '0.1745', '--roll', '0', '--pitch', '0', '--yaw', '0', '--frame-id', 'base_link', '--child-frame-id', 'laser'],
            condition=IfCondition(LaunchConfiguration('enable_static_base_link_to_laser_tf')),
            ),

        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='enable_static_base_footprint_to_base_link_tf',
            output='screen',
            arguments=['--x', '0', '--y', '0', '--z', '0.242', '--roll', '0', '--pitch', '0', '--yaw', '0', '--frame-id', 'base_footprint', '--child-frame-id', 'base_link'],
            condition=IfCondition(LaunchConfiguration('enable_static_base_footprint_to_base_link_tf')),
            ),

        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='base_link_to_imu_link',
            output='screen',
            arguments=['--x', '0', '--y', '0', '--z', '0.05', '--roll', '0', '--pitch', '0', '--yaw', '0', '--frame-id', 'base_link', '--child-frame-id', 'imu_link'],
            condition=IfCondition(LaunchConfiguration('enable_static_base_link_to_imu_link_tf')),
            ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare('sllidar_ros2'), 'launch', 'sllidar_s1_launch.py'])
                ),
            launch_arguments={
                'serial_port': LaunchConfiguration('lidar_port'),
                'serial_baudrate': LaunchConfiguration('lidar_baudrate'),
                }.items(),
            condition=IfCondition(LaunchConfiguration('enable_lidar')),
            ),

        # Nav2 スタック本体の起動
        IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([nav2_bringup_pkg, 'launch', 'bringup_launch.py'])
                    ),
                launch_arguments={
                    'map': PathJoinSubstitution([mirs_pkg, 'maps', 'youkanato.yaml']),
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                    'params_file': RewrittenYaml(
                        source_file=nav2_params_file,
                        param_rewrites={
                            'bt_navigator.ros__parameters.navigate_complete_coverage.plugin':
                            'nav2_bt_navigator::NavigateToPoseNavigator',
                            },
                        convert_types=True,
                        ),
                    }.items()
                ),

        IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([nav2_bringup_pkg, 'launch', 'rviz_launch.py'])
                    ),
                launch_arguments={
                    'rviz_config': rviz_config_file
                    }.items(),
                condition=IfCondition(LaunchConfiguration('use_rviz'))
                )
    ])
