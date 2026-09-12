import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

def generate_launch_description():

    mirs_share_dir = get_package_share_directory('mirs')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # --- 引数の定義 ---
    # マップファイルのデフォルトパス (パッケージ内の maps/rouka7.yaml)
    default_map_path = os.path.join(mirs_share_dir, 'maps', 'rouka7.yaml')
    
    map_yaml_file = DeclareLaunchArgument(
        'map',
        default_value=default_map_path
    )

    use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Whether to start RViz'
    )

    use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )

    esp_port = DeclareLaunchArgument(
        'esp_port', default_value='/dev/ttyUSB1',
        description='Set esp32 usb port.')
    lidar_port = DeclareLaunchArgument(
        'lidar_port', default_value='/dev/ttyUSB0',
        description='Set lidar usb port.')

    # 3. MIRS本体のハードウェア (mirs_hardware.launch.pyを直接Include)
    mirs_hardware_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(mirs_share_dir, 'launch', 'mirs_hardware.launch.py')
        ),
        launch_arguments={
            'esp_port': LaunchConfiguration('esp_port'),
            'lidar_port': LaunchConfiguration('lidar_port'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'enable_ekf_local': 'true',
            'enable_robot_state_publisher': 'true',
        }.items()
    )

    # 5. Nav2 の設定ファイル（mirsパッケージのものを使用）
    nav2_params_file = os.path.join(
        mirs_share_dir, 'config', 'navigation', 'nav2_params.yaml'
    )

    # 6. Rviz の設定ファイル（Nav2標準のものを使用）
    rviz_config_file = os.path.join(
        nav2_bringup_dir, 'rviz', 'nav2_default_view.rviz'
    )

    # 7. Nav2 スタック本体の起動
    nav2_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        # Nav2に渡す引数
        launch_arguments={
            'map': LaunchConfiguration('map'), # 引数で指定されたマップを使用
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'params_file': nav2_params_file,   # Nav2の設定ファイルを指定
        }.items()
    )

    # 8. Rviz の起動
    rviz_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'rviz_launch.py')
        ),
        launch_arguments={
            'rviz_config': rviz_config_file
        }.items(),
        condition=IfCondition(LaunchConfiguration('use_rviz'))
    )

    # 9. 起動するものをリストにして返す
    return LaunchDescription([
        map_yaml_file,         # マップ引数
        use_rviz,              # RViz起動フラグ
        use_sim_time,          # シミュレーション時間フラグ
        esp_port,
        lidar_port,
        mirs_hardware_launch,  # MIRS本体 (T1の代わり)
        nav2_bringup_launch,   # Nav2本体 (T2の代わり)
        rviz_node,              # Rviz (T3の代わり)
    ])
