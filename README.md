# mirs

## 要件
### ハードウェア

- PC
- クローラ型移動ロボット
- ESP32
- PWM/DIR方式モータドライバ
- 2D LiDAR

### ソフトウェア

- Ubuntu 22.04 または Ubuntu 24.04（WSL 可）
- それぞれのUbuntu バージョンに合わせたROS2 humble / jazzy 環境 もしくは mirs_container

docker(仮想環境)を使うか生環境を使うか選ぶことができます。

## LiDAR安全停止

`mirs_launch.py` / `bringup_launch.py` では、Nav2とLiDARが有効な場合に
`scan_safety_guard` を起動します。Nav2の `collision_monitor` 出力 `/cmd_vel_safe` を監視し、
ゲート後の `/cmd_vel` をESP32へ送ります。Nav2を起動しない場合は監視ノードは起動せず、
従来どおり `/cmd_vel` がESP32への指令になります。
前方±30°の `/scan` に有効な距離があり、最小距離が0.35 m以下になるとESP32向け速度指令を
ゼロにします。0.50 m以上まで離れると停止を解除し、直近のNav2速度指令を再び通します。
ヒステリシス幅と前方角度は次のlaunch引数で変更できます。

```bash
ros2 launch mirs mirs_launch.py \
  enable_nav2:=true \
  scan_safety_stop_distance:=0.35 scan_safety_resume_distance:=0.50 \
  scan_safety_forward_angle:=30.0
```

LiDARスキャンが0.5秒以上届かない場合もゼロ指令を出します。Nav2有効時に他のノードから
`/cmd_vel` を直接publishすると安全ゲートを迂回するため、速度指令はNav2経由で出してください。
首振り2D LiDARでは角度ごとの距離を照合せず、現スキャンの正面角度帯を使います。検知距離・角度帯と
実際の停止距離は、低速・無人の条件から実機で確認してください。

## 導入

### 1. ESP32 と LiDAR の準備

ESP32 と LiDAR を、LiDAR → ESP32 の順に PC へUSB接続してください。
ESP32には事前にmirs_espもしくはmirs_esp_pioを送信しておいてください。
実機へ書き込む前に、ピン割り当て、エンコーダ、車輪径、トレッド幅、モーター出力、非常停止、バッテリー監視の設定を確認してください。

#### micro-ROSの接続方法

micro-ROS Agent はUSBシリアルとSBCのGPIO UARTのどちらでも接続できます。
ファームウェア書き込みはUSBを使用し、Piとの実行時micro-ROS通信だけをGPIO UARTにする場合は、
ESP32のUARTピンをPiのUARTピンに接続し、launch引数 `esp_port` でPi側のデバイスを指定します。
この設定はPi側Agentのポートとボーレートを選ぶものです。ESP32側ファームウェアも同じUARTピンと
ボーレートでmicro-ROSを初期化する必要があります（ファームウェアのUART設定は別途行ってください）。

Pi側でシリアルポートを有効化し、ログインシェルをシリアルへ出さない設定にしてください
（`raspi-config` の Interface Options → Serial Port で設定）。設定後、必要ならPiを再起動します。
配線はPi TX → ESP32 RX、Pi RX ← ESP32 TX、GND共通です。両方のUARTは3.3Vです。
PiのGPIOへ5V信号を接続しないでください。

```bash
# Pi GPIO UART（通常 /dev/serial0）、ESP32 micro-ROS側は115200 baud
ros2 launch mirs mirs.launch.py \
  esp_port:=/dev/serial0 esp_baudrate:=115200
```

`esp_port` と `esp_baudrate` は `slam.launch.py`、`nav.launch.py`、
`mirs_hardware.launch.py` でも指定できます。UARTを使わずUSB接続する場合は、
既定の `esp_port:=/dev/ttyUSB1` のまま起動できます。

#### USBポート番号の考え方

LinuxではUSBシリアル機器は接続順に `/dev/ttyUSB0`、`/dev/ttyUSB1`、…と番号が振られます。
先に挿した方が若い番号になります。本パッケージの既定値は以下の前提です。

| 機器 | 既定ポート | 接続順 |
|---|---|---|
| LiDAR | `/dev/ttyUSB0` | 先に接続 |
| ESP32 | `/dev/ttyUSB1` | 後に接続 |

#### どちらが何番か確認する方法

ケーブルを挿すたびに番号が変わることがあるため、起動前に確認してください。

```bash
# 方法1: 接続順にカーネルメッセージが出る
dmesg | grep -E "ttyUSB|cp210x|ch341" | tail -10
# 例: 「cp210x converter now attached to ttyUSB0」の直後に挿した機器が ttyUSB0

# 方法2: 機器固有名で見分ける（抜き差しに強くおすすめ）
ls -l /dev/serial/by-id/
# 例:
#   usb-<USBシリアル変換器の識別名> -> ../../ttyUSB0
#   usb-1a86_USB_Serial-if00-port0 -> ../../ttyUSB1
```

`by-id` 名は機器ごとに固有なので、一度対応をメモしておけば毎回 `dmesg` を見る必要がなくなります。
LiDAR側とESP32側は、USBシリアル変換器の製品名で表示されることがあります。

#### 順序を変えた場合の起動方法

launch ファイルを編集する必要はありません。引数で上書きしてください。

```bash
# 既定どおり（LiDAR=USB0、ESP32=USB1）の場合
ros2 launch mirs mirs.launch.py

# 逆順に挿した場合（LiDAR=USB1、ESP32=USB0）の場合
ros2 launch mirs mirs.launch.py esp_port:=/dev/ttyUSB0 lidar_port:=/dev/ttyUSB1

# by-id名で指定する場合（番号変動に強くおすすめ）
ros2 launch mirs mirs.launch.py \
  esp_port:=/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0 \
  lidar_port:=/dev/serial/by-id/<LiDAR側USBシリアル変換器の識別名>
```

`XXXX` 部分は各自の環境の `ls -l /dev/serial/by-id/` 出力に読み替えてください。
`slam.launch.py`、`nav.launch.py` でも同じ `esp_port` / `lidar_port` 引数が使えます。

### 2. ワークスペースの作成とリポジトリのクローン

方法A（推奨。人手・AI共通）：マニフェストから一括取得する。

```bash
mkdir -p mirs_workspace && cd mirs_workspace
git clone https://github.com/mirs260x/mirs.git src/original/mirs
vcs import src < src/original/mirs/workspace.repos  # 要 vcstool（pip install vcstool）
```

`workspace.repos` に全リポジトリ・配置・版が書かれている。AIエージェントに構築させる場合も、
このファイルと各リポジトリのURLだけ渡せばよい。mirs2605/org の2件は非公開のため
SSHの鍵認証が必要（HTTPSでは取得できない）。

方法B（手動）：1件ずつcloneする。

```bash
mkdir -p mirs_workspace/src/original mirs_workspace/src/thirdparty
cd mirs_workspace/src/original

# 自前パッケージ一式
# 使用する ROS 2 ディストリビューションに応じて jazzy/humble を適宜読み替えてください
git clone https://github.com/mirs260x/mirs.git
git clone https://github.com/mirs260x/mirs_msgs.git
git clone https://github.com/mirs2605/ble_server.git
git clone https://github.com/mirs2605/coverage.git

cd ../thirdparty
git clone -b jazzy https://github.com/micro-ROS/micro-ROS-Agent.git
git clone <LiDAR用ROS 2ドライバのGit URL>
git clone -b jazzy-v2 https://github.com/open-navigation/opennav_coverage.git
git clone https://github.com/Fields2Cover/Fields2Cover.git

cd ../..
```

Nav2本体（`nav2_bringup` 等）は `package.xml` の依存宣言により次の `rosdep install` で入ります。
`opennav_coverage` と `Fields2Cover` はソース配置が必要です（版は上記どおり）。

### 3. ビルド

```bash
# rosdep の更新
rosdep update

# 依存パッケージのインストール
rosdep install --from-path src --ignore-src -r -y

# 全パッケージのビルド
colcon build --symlink-install

# ビルド結果の読み込み
source install/setup.bash
```

### 4. 実行

まず基本的な動作を確認します。

```bash
# 基本的なシステム起動
ros2 launch mirs mirs.launch.py
```

LiDAR が回転していること、ターミナル上で ESP32 との通信が表示されていることを確認してください。

別のターミナルからコンテナに入り、エンコーダ値・オドメトリ値・走行試験などが正常か確認します。

PID 値の設定ファイル: `mirs_workspace/src/original/mirs/config/config.yaml`

```bash
# 前進（0.2 m/s）
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# 後退（0.2 m/s）
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# 回転（0.5 rad/s）
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"

# 停止
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

直進・回転のテストスクリプトも用意されています。

```bash
# 3m 直進テスト
ros2 run mirs odom_linear_test.py

# 回転テスト
ros2 run mirs odom_rotate_test.py
```

## 動作確認

```bash
# ノード一覧の表示
ros2 node list

# トピック一覧の表示
ros2 topic list

# x, y, z 軸でロボットがどこにいるかの確認
ros2 topic echo /odom

# エンコーダの値の確認（左右2系統の値が出ます）
ros2 topic echo /encoder

# TF ツリーの確認
ros2 run tf2_tools view_frames
```

## マッピングと自律走行

### 地図作成（SLAM）

```bash
# マップ作成
ros2 launch mirs slam_launch.py
```

SLAM Toolboxのscan matchingとループクロージャを使って、ロボットを動かしながら地図を作成します。`slam_launch.py` はオドメトリTF用のEKFも有効にします。ループクロージャは `config/slam/slam_toolbox_config.yaml` の `do_loop_closing: true` で有効です。既走行箇所を十分に重ねて走行すると、LiDARスキャンの一致から過去の姿勢を補正します。

### 地図作成（SLAM）

```bash
ros2 launch mirs mirs_launch.py enable_slam_toolbox:=true enable_rviz:=true
```

コントローラでロボットを動かしながら地図を作成します。移動中は RViz2 上でもロボットが動いていることを確認してください（地図作成には LiDAR だけでなくエンコーダの接続が必要です）。

地図ができたら、以下のコマンドで保存してください。`<マップ名>` は保存したいファイル名に置き換えてください。
運用地図は`/home/developer/ws/maps/real/`に保存します。
パッケージの`maps/`にはサンプル`es.yaml`と`es.pgm`だけを残します。
slam_toolbox の `/map` は Durability `Transient Local` で配信されるため、
関数内で `map_subscribe_transient_local:=true` を付けています。

```bash
# /map が出ていることを先に確認（Hzが出なければSLAM側の問題）
ros2 topic info /map -v
ros2 topic hz /map

# 保存（Dockerイメージの再ビルド前でも同じ場所へ保存できる）
mkdir -p /home/developer/ws/maps/real
ros2 run nav2_map_server map_saver_cli -f /home/developer/ws/maps/real/<マップ名> \
  --ros-args -p map_subscribe_transient_local:=true -p save_map_timeout:=10.0
# 再ビルド済みコンテナでは savemap <マップ名> も同じ保存先を使う
```

作成した地図をそのまま使うと正常に動作しないことがあります。ペイントアプリ等で、点のまばらな箇所を塗りつぶす、足跡を壁として誤認識した箇所を白く塗りつぶすなどの後処理を行うとよいです。

### 自律走行（Navigation2）

保存したマップを使って、スタート地点とゴール地点を定めて自律走行させることができます。

```bash
# サンプル地図（es.yaml）で起動する場合
ros2 launch mirs nav_launch.py

# コマンドラインでマップを指定する場合
ros2 launch mirs nav_launch.py map:=/home/developer/ws/maps/real/<マップ名>.yaml
```

Nav2は起動時にAMCLを地図全体の一様分布で自動初期化します。ロボットをゆっくり動かすと、LiDARスキャンとオドメトリから候補が収束します。
対称な場所などで自動推定が一意に決まらない場合だけ、RViz2の「2D Pose Estimate」で初期位置を指定してください。

自動推定が収束しない場合のみ、次の手順で手動指定します。

1. RViz2 上部ツールバーの「2D Pose Estimate」をクリック
2. 地図上の、実際のロボットが存在する位置・向きをドラッグして指定
3. パーティクルクラウド（緑の矢印群）がロボット周辺に収束することを確認する

続けてゴール（目標地点）を指定します。

1. RViz2 上部ツールバーの「Nav2 Goal」（または「2D Nav Goal」）をクリック
2. 地図上で行きたい位置・向きをクリック＆ドラッグして指定
3. 経路（グローバルパス／ローカルパス）が表示され、ロボットが自律的に走行を開始する

### 本番一発起動（Nav2＋coverage＋BLE）

清掃範囲の自動走行まで行う場合は `coverage` パッケージの本番launchを使います。
詳細は [`coverage/README.md`](../coverage/README.md) を参照してください。

```bash
# RVizなし・BLEなしの手動テスト構成
ros2 launch coverage production.launch.py use_rviz:=false enable_ble:=false
```

BLE実機なしで起動する場合は `enable_ble:=false` が必須です（GATT不在では
`ble_receiver_node` が即死します）。清掃範囲は `/cleaning_zone` への投入で与えます。

## API リファレンス（安定インターフェース）

このパッケージを直接編集せずに使うための契約です。下表の名前はバージョンをまたいで維持されます。
拡張したい場合はこのAPI越しに別パッケージから利用してください。

<!-- API-CONTRACT-START -->

### トピック

| 名前 | 型 | 方向 | 説明 |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | Nav2時: 安全ゲート→ESP32 / Nav2なし: 入力→ESP32 | Nav2起動時はLiDAR判定後の速度指令 |
| `/cmd_vel_nav` | `geometry_msgs/Twist` | Nav2制御器→速度平滑化 | 平滑化前の指令 |
| `/cmd_vel_safe` | `geometry_msgs/Twist` | 衝突監視→安全ゲート | 最終ゲートに渡す指令 |
| `/odom` | `nav_msgs/Odometry` | 出力 | オドメトリ（ESP32がmicro-ROS経由で配信、`frame_id=odom`） |
| `/params` | `mirs_msgs/BasicParam` | 出力 | ESP用パラメータ転送（2Hz） |
| `/scan` | `sensor_msgs/LaserScan` | 出力 | LiDARドライバ（sllidar_ros2経由） |
| `/traveled_path` | `nav_msgs/Path` | 出力 | 走行軌跡（可視化用） |

### サービス（クライアントは本Pkg、サーバはESP側）

| 名前 | 型 | 用途 |
|---|---|---|
| `esp_cmd` | `mirs_msgs/BasicCommand` | 汎用コマンド（`param1`〜`param4`） |
| `esp_update` | `mirs_msgs/ParameterUpdate` | 車輪・PIDパラメータ更新 |
| `reboot` | `mirs_msgs/SimpleCommand` | ESP再起動 |
| `reset_encoder` | `mirs_msgs/SimpleCommand` | エンコーダリセット |

### フレーム

| 名前 | 親 | 発行元 | 説明 |
|---|---|---|---|
| `odom` | `map`（SLAM/Nav2時） | EKF（`robot_localization`） | オドメトリ原点 |
| `base_footprint` | `odom` | EKF（`robot_localization`） | 地面投影 |
| `base_link` | `base_footprint` | 静的TF | 機体中心 |
| `imu_link` | `base_link` | 静的TF | IMU取付位置（xyzは実測後に更新） |
| `laser` | `base_link` | 静的TF | LiDAR取付位置 |

### パラメータ（`config/config.yaml`）

| ノード | キー | 説明 |
|---|---|---|
| `parameter_publisher` | `wheel_radius`、`wheel_base`、`rkp`、`rki`、`rkd`、`lkp`、`lki`、`lkd` | ESPへ転送する車輪・PID値 |

### 起動引数（`mirs_launch.py` API）

上位launchから機体の基本ノードを利用する場合は、`mirs_launch.py` をincludeしてください。
この表にあるlaunch引数を外部APIとして扱い、ノード名・内部topic・設定ファイルの構造は実装詳細です。

| 引数 | 既定値 | 説明 |
|---|---|---|
| `esp_port` | `/dev/ttyUSB1` | ESP32 micro-ROSのシリアルデバイス（USBまたはUART） |
| `lidar_port` | `/dev/ttyUSB0` | LiDARのUSBポート |
| `lidar_baudrate` | `256000` | LiDARボーレート |
| `lidar_frame` | `laser` | LiDARのフレーム名 |
| `use_sim_time` | `false` | シミュレーション時刻 |
| `enable_lidar` | `true` | LiDARドライバの有効化 |
| `scan_safety_stop_distance` | `0.35` | 安全停止距離（m） |
| `scan_safety_resume_distance` | `0.50` | 安全停止解除距離（m） |
| `scan_safety_forward_angle` | `30.0` | 前方監視角度（±度） |
| `enable_parameter_publisher` | `true` | `parameter_publisher` の有効化 |
| `enable_micro_ros` | `true` | micro-ROS agentの有効化 |
| `enable_ekf_local` | `false` | EKF（`odom`→`base_footprint`）の有効化 |
| `enable_rviz` | `false` | MIRS標準RVizの有効化 |
| `enable_nav2` | `false` | Nav2の有効化 |
| `enable_slam_toolbox` | `false` | SLAM Toolboxの有効化 |
| `autostart` | `true` | Nav2ライフサイクルの自動起動 |
| `slam` | `False` | Nav2のSLAMモード切替 |
| `enable_auto_global_localization` | `true` | AMCLを地図全体から自動初期化 |
| `ekf_config_file` | `config/ekf/ekf_params.yaml` | EKF設定ファイル |
| `nav2_params_file` | `config/navigation/nav2_params.yaml` | Nav2設定ファイル |
| `rviz_config_file` | `config/rviz/default.rviz` | RViz設定ファイル |
| `slam_toolbox_config_file` | `config/slam/slam_toolbox_config.yaml` | SLAM Toolbox設定ファイル |
| `enable_static_base_link_to_laser_tf` | `true` | 静的TF（`base_link`→LiDAR） |
| `enable_static_base_footprint_to_base_link_tf` | `true` | 静的TF（`base_footprint`→`base_link`） |
| `enable_static_base_link_to_imu_link_tf` | `false` | 静的TF（`base_link`→`imu_link`） |

別パッケージから基礎機能を使う例：

```python
IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        PathJoinSubstitution([
            FindPackageShare('mirs'), 'launch', 'mirs_launch.py'])),
    launch_arguments={
        'esp_port': '/dev/ttyUSB1',
        'enable_ekf_local': 'true',
        'enable_rviz': 'false',
        'enable_nav2': 'false',
        'enable_slam_toolbox': 'false',
    }.items())
```

<!-- API-CONTRACT-END -->

## ライセンス

各ディレクトリの `LICENSE` および各パッケージのライセンス表記を確認してください。

## 謝辞

このプロジェクトは、以下の先行開発の成果を継承しています。

- **mirs2502** ([GitHub](https://github.com/mirs2502))
- **mirs240x** ([GitHub](https://github.com/mirs240x))

開発に携わった皆様に感謝申し上げます。

## 参考リンク

- [ROS 2 Documentation](https://docs.ros.org/en/jazzy/)
- [Navigation2](https://navigation.ros.org/)
- [SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox)
- [micro-ROS](https://micro.ros.org/)


### 実機とGazeboの分離

`mirs_launch.py`は子プロセスのROS_DOMAIN_IDを90に設定します。simulationは91を使います。
端末でのtopic確認・rosbag記録にも対応するComposeサービス（実機は`ros`、Gazeboは`ros-simulation`）を使ってください。
Foxgloveの待受ポートは実機8765、Gazebo8766です。同一Domain内では、一台分の機体・Nav2・地図作成のlaunchだけを起動します。

速度指令は`cmd_vel_nav → cmd_vel_smoothed → cmd_vel_safe → cmd_vel`へ流れます。
衝突監視の出力を`cmd_vel_nav`へ戻すと速度平滑化への循環が生じるため、別の名前を使います。
`enable_scan_safety`の既定値は`enable_lidar`です。外部launchがLiDARドライバを起動する場合は、
`enable_lidar:=false enable_scan_safety:=true`でスキャン監視を有効にできます。
Nav2を無効にした状態では、この引数をtrueにしても安全ゲートは起動しません。

`nav_launch.py`はEKFとIMU取付TFを有効にします。SLAMとNav2を使う場合は
`enable_nav2:=true slam:=True enable_slam_toolbox:=false`とし、独立SLAMとAMCLによるmap→odomの二重配信を避けます。

`nav2_params_file`を独自の設定へ差し替える場合も、衝突監視の出力を`cmd_vel_safe`に合わせてください。`cmd_vel`へ直接出すと最終安全ゲートと同じトピックへ二重に配信されます。
