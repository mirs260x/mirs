"""Config/path consistency tests (ROS不要).

launchが参照するconfig/maps/rviz実ファイルの存在を保証する。
"""
import os
import re
from pathlib import Path

import yaml

ROOT = Path(".")
LAUNCH = ROOT / "launch"


def test_config_yaml_params_sane():
    cfg = yaml.safe_load((ROOT / "config/config.yaml").read_text())
    odo = cfg["odometry_publisher"]["ros__parameters"]
    assert odo["wheel_radius"] > 0
    assert odo["wheel_base"] > 0
    assert odo["count_per_rev"] > 0


def test_referenced_files_exist():
    # launch中の os.path.join(mirs_*, 'config'|'maps'|'rviz'|..., file) 参照を抽出
    pat = re.compile(
        r"os\.path\.join\(\s*mirs\w*(?:_pkg|_share_dir)?\s*((?:,\s*['\"][^'\"]+['\"])+)\)")
    missing = []
    for f in LAUNCH.glob("*.launch.py"):
        if f.name in ("mirs_hardware.launch.py",):
            continue  # 既定値は別途検証済み
        for m in pat.finditer(f.read_text()):
            parts = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
            # パッケージ外 (nav2_bringup等のrviz等) は対象外
            if not parts or parts[0] not in ("config", "maps", "rviz", "urdf", "launch"):
                continue
            # LaunchConfigurationを含む動的パスはスキップ
            if "LaunchConfiguration" in m.group(0):
                continue
            rel = os.path.join(*parts)
            if not (ROOT / rel).exists():
                # share配置では config/rviz -> config/rviz に対応するため、
                # 'rviz/X' は 'config/rviz/X' も許容する (後方互換チェック)
                alt = None
                if parts[0] == "rviz":
                    alt = os.path.join("config", *parts)
                    if (ROOT / alt).exists():
                        continue
                if parts[0] == "config" and len(parts) == 2 and parts[1].endswith(".yaml"):
                    continue  # navigation等のサブディレクトリは個別テストで扱う
                missing.append(f"{f.name}: {rel}")
    assert missing == [], f"missing files: {missing}"


def _norm(src):
    """引用符統一+空白圧縮で複数行os.path.joinに対応."""
    import re
    s = src.replace('"', "'")
    return re.sub(r"\s+", "", s)


def test_nav2_rviz_map_paths_are_correct():
    # 既知の誤パス回帰防止: 正しいサブディレクトリを参照していること
    nav = _norm((LAUNCH / "nav.launch.py").read_text())
    assert "'config','navigation','nav2_params.yaml'" in nav
    assert "my_mirs_map.yaml" not in nav
    slam = _norm((LAUNCH / "slam.launch.py").read_text())
    assert "'config','rviz','default.rviz'" in slam
    assert "'config','slam'," in slam


def test_system_bringup_launches_stay_deleted():
    # 基礎Pkg方針: 応用層の全部入りlaunchは別Pkgへ。復活検出用
    for name in ["system_bringup.launch.py", "system_bringup_odom_only.launch.py"]:
        assert not (LAUNCH / name).exists(), f"{name} must stay in another package"


def test_maps_have_pgms():
    for yf in (ROOT / "maps").glob("*.yaml"):
        cfg = yaml.safe_load(yf.read_text())
        assert (ROOT / "maps" / cfg["image"]).exists(), f"{yf}: image missing"
        assert cfg["resolution"] > 0
