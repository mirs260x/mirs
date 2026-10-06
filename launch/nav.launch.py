"""nav.launch.py: ハードウェア＋Nav2＋RVizの起動構成。"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from nav2_common.launch import RewrittenYaml

def generate_launch_description():

    mirs_share_dir = get_package_share_directory('mirs')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # --- 引数の定義 ---
    # マップファイルのデフォルトパス (パッケージ内の maps/gakuseigenkan.yaml)
    default_map_path = os.path.join(mirs_share_dir, 'maps', 'es.yaml')
    
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
        description='ESP32 micro-ROS serial device (USB or UART).')
    esp_baudrate = DeclareLaunchArgument(
        'esp_baudrate', default_value='115200',
        description='ESP32 micro-ROS serial baudrate.')
    lidar_port = DeclareLaunchArgument(
        'lidar_port', default_value='/dev/ttyUSB0',
        description='Set lidar usb port.')
    lidar_baudrate = DeclareLaunchArgument(
        'lidar_baudrate', default_value='256000',
        description='LiDAR baudrate.')
    ekf_config_file = DeclareLaunchArgument(
        'ekf_config_file',
        default_value=os.path.join(mirs_share_dir, 'config', 'ekf', 'ekf_params.yaml'),
        description='EKF config file.')

    # MIRS本体のハードウェア (mirs_hardware.launch.pyを直接Include)
    mirs_hardware_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(mirs_share_dir, 'launch', 'mirs_hardware.launch.py')
        ),
        launch_arguments={
            'esp_port': LaunchConfiguration('esp_port'),
            'esp_baudrate': LaunchConfiguration('esp_baudrate'),
            'lidar_port': LaunchConfiguration('lidar_port'),
            'lidar_baudrate': LaunchConfiguration('lidar_baudrate'),
            'ekf_config_file': LaunchConfiguration('ekf_config_file'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'enable_ekf_local': 'true',
        }.items()
    )

    # Nav2 の設定ファイル（mirsパッケージのものを使用）
    nav2_params_file = os.path.join(
        mirs_share_dir, 'config', 'navigation', 'nav2_params.yaml'
    )

    # nav単体にはcoverage_serverが居ないため、coverageナビゲータの実体を
    # 標準ToPoseに差し替える。production.launch.pyは素のparamsを使いcoverageのまま。
    # 文字列書換えのみ（RewrittenYamlはlistを扱えないためplugin指定だけ変える）。
    # nav単体でCompleteCoverageゴールを送るとToPose動作になる点に注意。
    nav_only_params = RewrittenYaml(
        source_file=nav2_params_file,
        param_rewrites={
            'bt_navigator.ros__parameters.navigate_complete_coverage.plugin':
                'nav2_bt_navigator::NavigateToPoseNavigator',
        },
        convert_types=True,
    )

    # Rviz の設定ファイル（Nav2標準のものを使用）
    rviz_config_file = os.path.join(
        nav2_bringup_dir, 'rviz', 'nav2_default_view.rviz'
    )

    # Nav2 スタック本体の起動
    nav2_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        # Nav2に渡す引数
        launch_arguments={
            'map': LaunchConfiguration('map'), # 引数で指定されたマップを使用
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'params_file': nav_only_params,   # coverage差替え済み（上記）
        }.items()
    )

    # Rviz の起動
    rviz_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'rviz_launch.py')
        ),
        launch_arguments={
            'rviz_config': rviz_config_file
        }.items(),
        condition=IfCondition(LaunchConfiguration('use_rviz'))
    )

    # 起動するものをリストにして返す
    return LaunchDescription([
        map_yaml_file,         # マップ引数
        use_rviz,              # RViz起動フラグ
        use_sim_time,          # シミュレーション時間フラグ
        esp_port,
        esp_baudrate,
        lidar_port,
        lidar_baudrate,
        ekf_config_file,
        mirs_hardware_launch,  # MIRS本体
        nav2_bringup_launch,   # Nav2本体
        rviz_node,              # Rviz
    ])
