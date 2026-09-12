# mirs

## 要件
### ハードウェア

- PC
- cugo v3i
- ESP32
- Cytron MD10C
- RPLiDAR S1

### ソフトウェア

- Ubuntu 22.04 または Ubuntu 24.04（WSL 可）
- それぞれのUbuntu バージョンに合わせたROS2 humble / jazzy 環境 もしくは mirs_container

docker(仮想環境)を使うか生環境を使うか選ぶことができます。

## 導入

### 1. ESP32 と LiDAR の準備

ESP32 と LiDAR を、LiDAR → ESP32 の順に PC へ接続してください。
ESP32には事前にmirs_espもしくはmirs_esp_pioを送信しておいてください。

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
#   usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_XXXX-if00-port0 -> ../../ttyUSB0
#   usb-1a86_USB_Serial-if00-port0 -> ../../ttyUSB1
```

`by-id` 名は機器ごとに固有なので、一度対応をメモしておけば毎回 `dmesg` を見る必要がなくなります。
LiDAR側は `CP2102`、ESP32側は `CP2102` または `CH340（1a86）` と表示されることが多いです。

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
  lidar_port:=/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_XXXX-if00-port0
```

`XXXX` 部分は各自の環境の `ls -l /dev/serial/by-id/` 出力に読み替えてください。
`slam.launch.py`、`nav.launch.py` でも同じ `esp_port` / `lidar_port` 引数が使えます。

### 2. ワークスペースの作成とリポジトリのクローン

```bash
mkdir -p mirs_workspace/src
cd mirs_workspace/src

# mirs パッケージを使う場合に必要な一式
# 使用する ROS 2 ディストリビューションに応じて jazzy/humble を適宜読み替えてください
git clone https://github.com/mirs260x/mirs.git
git clone -b jazzy https://github.com/micro-ROS/micro-ROS-Agent.git
git clone https://github.com/Slamtec/sllidar_ros2.git

cd ..
```

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

PID 値の設定ファイル: `mirs_workspace/src/mirs/config/config.yaml`

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

# エンコーダの値の確認（cugo v3 はクローラのため値は2つ出ます）
ros2 topic echo /encoder

# TF ツリーの確認
ros2 run tf2_tools view_frames
```

## マッピングと自律走行

### 地図作成（SLAM）

```bash
# マップ作成
ros2 launch mirs slam.launch.py
```

コントローラでロボットを動かしながら地図を作成します。移動中は RViz2 上でもロボットが動いていることを確認してください（地図作成には LiDAR だけでなくエンコーダの接続が必要です）。

地図ができたら、以下のコマンドで保存してください。`<マップ名>` は保存したいファイル名に置き換えてください。

```bash
ros2 run nav2_map_server map_saver_cli -f <保存先パス>/<マップ名>
```

作成した地図をそのまま使うと正常に動作しないことがあります。ペイントアプリ等で、点のまばらな箇所を塗りつぶす、足跡を壁として誤認識した箇所を白く塗りつぶすなどの後処理を行うとよいです。

### 自律走行（Navigation2）

保存したマップを使って、スタート地点とゴール地点を定めて自律走行させることができます。

```bash
# 起動時にデフォルトのマップパスを使う場合（launch ファイル内の default_map_path を変更）
ros2 launch mirs nav.launch.py

# コマンドラインでマップを指定する場合
ros2 launch mirs nav.launch.py map:=<保存先パス>/<マップ名>.yaml
```

nav2 は起動直後、ロボットの正確な位置を把握していないため、必ず初期位置合わせを行ってください。

1. RViz2 上部ツールバーの「2D Pose Estimate」をクリック
2. 地図上の、実際のロボットが存在する位置・向きをドラッグして指定
3. パーティクルクラウド（緑の矢印群）がロボット周辺に収束することを確認する

続けてゴール（目標地点）を指定します。

1. RViz2 上部ツールバーの「Nav2 Goal」（または「2D Nav Goal」）をクリック
2. 地図上で行きたい位置・向きをクリック＆ドラッグして指定
3. 経路（グローバルパス／ローカルパス）が表示され、ロボットが自律的に走行を開始する

実機へ書き込む前に、ピン割り当て、エンコーダ、車輪径、トレッド幅、モーター出力、非常停止、バッテリー監視の設定を確認してください。

## API リファレンス（安定インターフェース）

このパッケージを直接編集せずに使うための契約です。下表の名前はバージョンをまたいで維持されます。
拡張したい場合はこのAPI越しに別パッケージから利用してください。

<!-- API-CONTRACT-START -->

### トピック

| 名前 | 型 | 方向 | 説明 |
|---|---|---|---|
| `/encoder` | `std_msgs/Int32MultiArray` | 入力（ESP→本Pkg） | `[左, 右]` のエンコーダカウント |
| `/cmd_vel` | `geometry_msgs/Twist` | 入力（利用者→ESP） | 速度指令（本Pkgはテストスクリプトが発行、購読はESP側） |
| `/odom` | `nav_msgs/Odometry` | 出力 | オドメトリ（20Hz、`frame_id=odom`） |
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
| `base_link` | `odom` | EKF | 機体中心 |
| `base_footprint` | `base_link` | URDF（`robot_state_publisher`） | 地面投影 |
| `laser` | `base_link` | URDF | LiDAR取付位置 |

### パラメータ（`config/config.yaml`）

| ノード | キー | 説明 |
|---|---|---|
| `odometry_publisher` | `wheel_radius`、`wheel_base`、`count_per_rev` | 車輪径、トレッド幅、1回転カウント |
| `parameter_publisher` | `wheel_radius`、`wheel_base`、`rkp`、`rki`、`rkd`、`lkp`、`lki`、`lkd` | ESPへ転送する車輪・PID値 |

### 起動引数（`mirs_hardware.launch.py`）

| 引数 | 既定値 | 説明 |
|---|---|---|
| `esp_port` | `/dev/ttyUSB1` | ESP32のUSBポート |
| `lidar_port` | `/dev/ttyUSB0` | LiDARのUSBポート |
| `lidar_baudrate` | `256000` | LiDARボーレート |
| `use_sim_time` | `false` | シミュレーション時刻 |
| `enable_lidar` | `true` | LiDARドライバの有効化 |
| `enable_odometry` | `true` | `odometry_publisher` の有効化 |
| `enable_parameter_publisher` | `true` | `parameter_publisher` の有効化 |
| `enable_micro_ros` | `true` | micro-ROS agentの有効化 |
| `enable_robot_state_publisher` | `true` | URDF配信の有効化 |
| `urdf_file` | `mirs_2.urdf` | `urdf/` 以下の機体モデル |
| `enable_ekf_local` | `true` | EKF（`odom`→`base_link`）の有効化 |
| `ekf_config_file` | `config/ekf/ekf_params.yaml` | EKF設定ファイル |
| `enable_static_odom_tf` | `false` | デバッグ用静的TF（EKFと併用不可） |
| `enable_static_laser_tf` | `false` | 旧仕様静的TF（URDFと併用不可） |

別パッケージから基礎機能を使う例：

```python
IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(get_package_share_directory('mirs'),
                     'launch', 'mirs_hardware.launch.py')),
    launch_arguments={'esp_port': '/dev/ttyUSB1',
                      'enable_ekf_local': 'true'}.items())
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