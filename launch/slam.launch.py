"""slam.launch.py: ハードウェア＋slam_toolbox＋RVizの起動構成。"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():

    # パッケージの 'share' ディレクトリへのパスを取得
    mirs_share_dir = get_package_share_directory('mirs')

    # --- 1. ハードウェア起動 (mirs_hardware.launch.pyを直接Include) ---
    esp_port = DeclareLaunchArgument(
        'esp_port', default_value='/dev/ttyUSB1',
        description='Set esp32 usb port.')
    lidar_port = DeclareLaunchArgument(
        'lidar_port', default_value='/dev/ttyUSB0',
        description='Set lidar usb port.')
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='Use simulated clock if true.')

    mirs_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(mirs_share_dir, 'launch', 'mirs_hardware.launch.py')
        ),
        launch_arguments={
            'esp_port': LaunchConfiguration('esp_port'),
            'lidar_port': LaunchConfiguration('lidar_port'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'enable_ekf_local': 'true',
        }.items()
    )
    
    use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Whether to start RViz'
    )

    # --- 2. SLAM (slam_toolbox) の設定 ---
    slam_config_file = LaunchConfiguration('slam_config_file')
    declare_arg_slam_config_file = DeclareLaunchArgument(
        'slam_config_file',
        default_value=os.path.join(
            mirs_share_dir,
            'config',
            'slam',
            'slam_toolbox_config.yaml')
    )

    # slam_toolbox ノードの定義
    slam_toolbox_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('slam_toolbox'),
                'launch',
                'online_async_launch.py'
            )
        ),
        launch_arguments={
            'slam_params_file': slam_config_file,
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': 'true',
        }.items()
    )
 

    # --- 3. Rviz の設定 ---
    rviz2_file = LaunchConfiguration('rviz2_file')
    declare_arg_rviz2_config_path = DeclareLaunchArgument(
        'rviz2_file', 
        default_value=os.path.join(
            mirs_share_dir,
            'config',
            'rviz',
            'default.rviz')
    )

    # Rviz ノードの定義
    rviz2_node = Node(
        name='rviz2',
        package='rviz2', 
        executable='rviz2', 
        output='screen',
        arguments=['-d', rviz2_file],
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')}
        ],
        condition=IfCondition(LaunchConfiguration('use_rviz'))
    )


    ld = LaunchDescription()
    
    ld.add_action(esp_port)
    ld.add_action(lidar_port)
    ld.add_action(use_sim_time_arg)
    ld.add_action(declare_arg_slam_config_file)
    ld.add_action(declare_arg_rviz2_config_path)
    ld.add_action(use_rviz)
    ld.add_action(mirs_launch)
    ld.add_action(slam_toolbox_launch)
    ld.add_action(rviz2_node)

    return ld
