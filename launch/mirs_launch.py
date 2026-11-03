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

"""機体のROS通信・センサ・制御パラメータを起動し、設定に応じて地図作成や走行処理を追加する。"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import (
    AnyLaunchDescriptionSource, PythonLaunchDescriptionSource)
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml


def generate_launch_description():

    # パッケージ指定
    mirs_pkg = FindPackageShare('mirs')
    nav2_bringup_pkg = FindPackageShare('nav2_bringup')

    return LaunchDescription([

        # ファイル設定
        DeclareLaunchArgument(
            'map',
            default_value=PathJoinSubstitution([mirs_pkg, 'maps', 'es.yaml'])
        ),
        DeclareLaunchArgument(
            'ekf_config_file',
            default_value=PathJoinSubstitution([mirs_pkg, 'config', 'ekf', 'ekf_params.yaml'])
        ),
        DeclareLaunchArgument(
            'rviz_config_file',
            default_value=PathJoinSubstitution([mirs_pkg, 'config', 'rviz', 'default.rviz'])
        ),
        DeclareLaunchArgument(
            'nav2_params_file',
            default_value=PathJoinSubstitution(
                [mirs_pkg, 'config', 'navigation', 'nav2_params.yaml'])
        ),
        DeclareLaunchArgument(
            'slam_toolbox_config_file',
            default_value=PathJoinSubstitution(
                [mirs_pkg, 'config', 'slam', 'slam_toolbox_config.yaml'])
        ),
        # ポート設定
        DeclareLaunchArgument('esp_port', default_value='/dev/ttyUSB1'),
        DeclareLaunchArgument('lidar_port', default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('lidar_baudrate', default_value='256000'),
        DeclareLaunchArgument('lidar_frame', default_value='laser'),
        DeclareLaunchArgument('foxglove_address', default_value='0.0.0.0'),
        DeclareLaunchArgument('foxglove_port', default_value='8765'),

        # 真偽値
        # simulation time
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        # node
        DeclareLaunchArgument('enable_lidar', default_value='true'),
        DeclareLaunchArgument('scan_safety_stop_distance', default_value='0.35'),
        DeclareLaunchArgument('scan_safety_resume_distance', default_value='0.50'),
        DeclareLaunchArgument('scan_safety_forward_angle', default_value='30.0'),
        DeclareLaunchArgument('enable_parameter_publisher', default_value='true'),
        DeclareLaunchArgument('enable_micro_ros', default_value='true'),
        DeclareLaunchArgument('enable_ekf_local', default_value='false'),
        DeclareLaunchArgument('enable_rviz', default_value='false'),
        DeclareLaunchArgument('enable_nav2', default_value='false'),
        DeclareLaunchArgument('enable_slam_toolbox', default_value='false'),
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument('slam', default_value='False'),
        DeclareLaunchArgument(
            'enable_auto_global_localization', default_value='true',
            description='AMCLを地図全体から自動初期化する'),
        # tf
        DeclareLaunchArgument('enable_static_base_link_to_laser_tf', default_value='true'),
        DeclareLaunchArgument('enable_static_base_footprint_to_base_link_tf',
                              default_value='true'),
        DeclareLaunchArgument('enable_static_base_link_to_imu_link_tf', default_value='false'),
        DeclareLaunchArgument('enable_slam_toolbox', default_value='false'),
        DeclareLaunchArgument('enable_foxglove_bridge', default_value='true'),

        Node(
            package='mirs',
            executable='parameter_publisher',
            name='parameter_publisher',
            output='screen',
            parameters=[PathJoinSubstitution([mirs_pkg, 'config', 'config.yaml']), {
                'use_sim_time': LaunchConfiguration('use_sim_time')}],
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
            parameters=[LaunchConfiguration('ekf_config_file'), {
                'use_sim_time': LaunchConfiguration('use_sim_time')}],
            remappings=[('/odometry/filtered', '/odometry/local')],
            condition=IfCondition(LaunchConfiguration('enable_ekf_local')),
        ),

        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='enable_static_base_link_to_laser_tf',
            output='screen',
            arguments=['--x', '0', '--y', '0', '--z', '0.1745', '--roll', '0', '--pitch',
                       '0', '--yaw', '0', '--frame-id', 'base_link',
                       '--child-frame-id', LaunchConfiguration('lidar_frame')],
            condition=IfCondition(LaunchConfiguration('enable_static_base_link_to_laser_tf')),
        ),

        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='enable_static_base_footprint_to_base_link_tf',
            output='screen',
            arguments=[
                '--x', '0', '--y', '0', '--z', '0.242', '--roll', '0', '--pitch', '0',
                '--yaw', '0', '--frame-id', 'base_footprint', '--child-frame-id', 'base_link',
            ],
            condition=IfCondition(LaunchConfiguration(
                'enable_static_base_footprint_to_base_link_tf')),
        ),

        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='base_link_to_imu_link',
            output='screen',
            arguments=[
                '--x', '0', '--y', '0', '--z', '0.05', '--roll', '0', '--pitch',
                '0', '--yaw', '0', '--frame-id', 'base_link', '--child-frame-id', 'imu_link',
            ],
            condition=IfCondition(LaunchConfiguration('enable_static_base_link_to_imu_link_tf')),
        ),

        Node(
            name='rviz2',
            package='rviz2',
            executable='rviz2',
            arguments=['-d', LaunchConfiguration('rviz_config_file')],
            parameters=[
                {'use_sim_time': LaunchConfiguration('use_sim_time')}
            ],
            condition=IfCondition(LaunchConfiguration('enable_rviz'))
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution(
                    [FindPackageShare('sllidar_ros2'), 'launch', 'sllidar_s1_launch.py'])
            ),
            launch_arguments={
                'serial_port': LaunchConfiguration('lidar_port'),
                'serial_baudrate': LaunchConfiguration('lidar_baudrate'),
                'frame_id': LaunchConfiguration('lidar_frame'),
            }.items(),
            condition=IfCondition(LaunchConfiguration('enable_lidar')),
        ),
        Node(
            package='mirs',
            executable='scan_safety_guard',
            name='scan_safety_guard',
            output='screen',
            parameters=[{
                'scan_topic': '/scan',
                'input_cmd_vel_topic': '/cmd_vel_nav',
                'output_cmd_vel_topic': '/cmd_vel',
                'stop_distance': ParameterValue(
                    LaunchConfiguration('scan_safety_stop_distance'), value_type=float),
                'resume_distance': ParameterValue(
                    LaunchConfiguration('scan_safety_resume_distance'), value_type=float),
                'forward_angle_deg': ParameterValue(
                    LaunchConfiguration('scan_safety_forward_angle'), value_type=float),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
            }],
            condition=IfCondition(PythonExpression([
                "'", LaunchConfiguration('enable_lidar'), "'.lower() == 'true' and '",
                LaunchConfiguration('enable_nav2'), "'.lower() == 'true'",
            ])),
        ),
        # Nav2 スタック本体の起動
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([nav2_bringup_pkg, 'launch', 'bringup_launch.py'])
            ),
            launch_arguments={
                'map': LaunchConfiguration('map'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'autostart': LaunchConfiguration('autostart'),
                'slam': LaunchConfiguration('slam'),
                'params_file': RewrittenYaml(
                    source_file=LaunchConfiguration('nav2_params_file'),
                    param_rewrites={
                        'bt_navigator.ros__parameters.navigate_complete_coverage.plugin':
                        'nav2_bt_navigator::NavigateToPoseNavigator',
                    },
                    convert_types=True,
                ),
            }.items(),
            condition=IfCondition(LaunchConfiguration('enable_nav2'))
        ),

        # AMCLを地図全体の一様分布で初期化し、2D Pose Estimateを不要にする。
        # SLAMモードではAMCLが起動しないため呼び出さない。
        TimerAction(
            period=5.0,
            actions=[ExecuteProcess(
                cmd=[
                    'ros2', 'service', 'call',
                    '/reinitialize_global_localization',
                    'std_srvs/srv/Empty', '{}',
                ],
                output='screen',
            )],
            condition=IfCondition(PythonExpression([
                "'", LaunchConfiguration('enable_nav2'),
                "'.lower() == 'true' and '",
                LaunchConfiguration('slam'),
                "'.lower() == 'false' and '",
                LaunchConfiguration('enable_auto_global_localization'),
                "'.lower() == 'true'",
            ])),
        ),

        # slam toolboxの起動
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution(
                    [FindPackageShare('slam_toolbox'), 'launch', 'online_async_launch.py'])
            ),
            launch_arguments={
                'slam_params_file': LaunchConfiguration('slam_toolbox_config_file'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'autostart': 'true',
            }.items(),
            condition=IfCondition(LaunchConfiguration('enable_slam_toolbox'))
        ),

        # foxglove bridgeの起動
        IncludeLaunchDescription(
            AnyLaunchDescriptionSource(
                PathJoinSubstitution([
                    FindPackageShare('foxglove_bridge'), 'launch',
                    'foxglove_bridge_launch.xml']),
            ),
            launch_arguments={
                'address': LaunchConfiguration('foxglove_address'),
                'port': LaunchConfiguration('foxglove_port'),
                }.items(),
            condition=IfCondition(LaunchConfiguration('enable_foxglove_bridge'))
            ),
    ])
