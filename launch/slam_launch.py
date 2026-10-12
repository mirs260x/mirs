"""slam.launch.py: ハードウェア＋slam_toolbox＋RVizの起動構成。"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():

    mirs_pkg = FindPackageShare('mirs')

    return LaunchDescription([

        DeclareLaunchArgument(
            'ekf_config_file',
            default_value = PathJoinSubstitution([mirs_pkg, 'config', 'ekf', 'ekf_params.yaml'])
            ),

        # mirs_launch.py
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([mirs_pkg, 'launch', 'mirs_launch.py'])
                ),
            launch_arguments = {
                'ekf_config_file': LaunchConfiguration('ekf_config_file'),
                'enable_ekf_local': 'true',
                'enable_slam_toolbox': 'true',
                'enable_rviz': 'true'
                }.items()
            )
        ])
