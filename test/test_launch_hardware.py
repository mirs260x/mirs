"""Launch structure tests (ROS不要・AST静的解析).

- mirs_hardware.launch.py が単一真実: 期待引数を宣言し、EKFパス既定が正しい
- 静的TF既定はfalse (EKFと競合させない)
- 上位launchはhardwareを直接Includeし、esp/lidar/use_sim_timeを転送
- 削除済みlaunchへの参照が残っていない
"""
import ast
from pathlib import Path

LAUNCH = Path("launch")
HARDWARE = LAUNCH / "mirs_hardware.launch.py"
UPPERS = ["slam.launch.py", "nav.launch.py"]
DELETED = ["mirs_minimum.launch.py", "mirs_odom_only.launch.py",
           "system_bringup.launch.py", "system_bringup_odom_only.launch.py"]


def _src(name):
    return (LAUNCH / name).read_text()


def _declare_args(src):
    tree = ast.parse(src)
    args = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == "DeclareLaunchArgument" and node.args \
                    and isinstance(node.args[0], ast.Constant):
                args.add(node.args[0].value)
    return args


def test_hardware_declares_expected_args():
    args = _declare_args(HARDWARE.read_text())
    for expected in ["esp_port", "lidar_port", "use_sim_time",
                     "enable_lidar", "enable_odometry",
                     "enable_parameter_publisher", "enable_micro_ros",
                     "enable_robot_state_publisher", "urdf_file",
                     "enable_ekf_local", "ekf_config_file",
                     "enable_static_odom_tf", "enable_static_laser_tf"]:
        assert expected in args, f"missing arg: {expected}"


def test_hardware_defaults_are_safe():
    src = HARDWARE.read_text()
    assert "config', 'ekf', 'ekf_params.yaml" in src.replace('"', "'")
    # 静的TFの既定はfalseであること
    for name in ["enable_static_odom_tf", "enable_static_laser_tf"]:
        idx = src.find(f"'{name}'")
        assert idx != -1
        window = src[idx:idx + 400]
        assert "default_value='false'" in window.replace('"', "'").replace(" ", "")


def test_uppers_include_hardware_directly_with_forwarding():
    for name in UPPERS:
        src = _src(name)
        assert "mirs_hardware.launch.py" in src, f"{name} must include hardware"
        for key in ["esp_port", "lidar_port", "use_sim_time"]:
            assert key in src, f"{name} must forward {key}"


def _code_only(src):
    """コメント行を除去して実コード参照のみにする."""
    return "\n".join(
        line for line in src.splitlines()
        if not line.lstrip().startswith("#"))


def test_no_reference_to_deleted_test_launches():
    import re
    for name in UPPERS + ["mirs.launch.py", "mirs_hardware.launch.py"]:
        src = _code_only(_src(name))
        for dead in DELETED:
            # docstring/コメントは許容し、実際のInclude/パス参照のみ禁止
            pat = re.compile(r"""['"]launch['"]\s*,\s*['"]""" + re.escape(dead) + r"""['"]""")
            assert not pat.search(src), f"{name} still includes {dead}"
            assert f"launch/{dead}" not in src, f"{name} still references {dead}"
    for dead in DELETED:
        assert not (LAUNCH / dead).exists(), f"{dead} should be deleted"
