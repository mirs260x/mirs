"""nav.launch.py: ハードウェア＋Nav2＋RVizの起動構成。"""
import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():

    mirs_pkg = FindPackageShare('mirs')

    return LaunchDescription([

        DeclareLaunchArgument(
            'map',
            default_value = PathJoinSubstitution([mirs_pkg, 'maps', 'es.yaml']) 
            ),

        # mirs_launch.py
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([mirs_pkg, 'launch', 'mirs_launch.py'])
                ),
            launch_arguments = {
                'map': LaunchConfiguration('map'),
                'enable_ekf_local': 'true',
                'enable_rviz': 'true',
                'enable_nav2': 'true',
                }.items()
            )
    ])
