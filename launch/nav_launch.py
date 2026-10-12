"""nav.launch.py: ハードウェア＋Nav2＋RVizの起動構成。"""
import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

def generate_launch_description():

    pkg_share = PathJoinSubstitution([FindPackageShare('mirs'), 'launch'])
    mirs_share_dir = get_package_share_directory('mirs')

    return LaunchDescription([
        DeclareLaunchArgument(
            'map',
            default_value=default_map_path
            ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock if true'
            ),
        DeclareLaunchArgument(
            'ekf_config_file',
            default_value=os.path.join(mirs_share_dir, 'config', 'ekf', 'ekf_params.yaml'),
            ),

        # MIRS本体のハードウェア (mirs_launch.pyを直接Include)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(mirs_share_dir, 'launch', 'mirs_launch.py')
                ),
            launch_arguments={
                'ekf_config_file': LaunchConfiguration('ekf_config_file'),
                'use_sim_time': 'false',
                'enable_ekf_local': 'true',
                'use_rviz': 'true',
                }.items()
            ),
    ])
