"""API contract tests.

READMEの <!-- API-CONTRACT-START --> 〜 END 区間が唯一の真実。
そこに記載のトピック/サービス/フレーム/起動引数が実装と一致することを検証し、
名前変更・削除を検出する。名前を変えたらREADMEとここを同時に直すこと。
"""
import re
from pathlib import Path

ROOT = Path(".")
START = "<!-- API-CONTRACT-START -->"
END = "<!-- API-CONTRACT-END -->"


def _contract():
    readme = (ROOT / "README.md").read_text()
    body = readme.split(START)[1].split(END)[0]
    # コードブロック内の使用例は契約対象外（esp_port等の引数名は含むが検証は別途）
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    return body


def _code():
    texts = []
    for pat in ("src/*.cpp", "scripts/*.py", "launch/*.py"):
        for f in ROOT.glob(pat):
            texts.append(f.read_text())
    return "\n".join(texts)


def test_contract_section_exists():
    readme = (ROOT / "README.md").read_text()
    assert START in readme and END in readme


def test_contract_topics_exist_in_code():
    contract, code = _contract(), _code()
    topics = set(re.findall(r"`(/[a-z0-9_]+)`", contract))
    assert topics, "no topics documented"
    # 外部Pkgが発行するトピックは提供者名の存在で代替検証
    provided_by_other = {"/scan": "sllidar"}
    for t in topics:
        if t in provided_by_other:
            assert provided_by_other[t] in code, f"topic {t} provider missing"
            continue
        # /cmd_vel は本Pkgでは発行のみ・購読はESP側だが、文字列参照は存在する
        assert f'"{t}"' in code or f"'{t}'" in code, f"topic {t} not found in code"


def test_contract_services_exist_in_code():
    contract, code = _contract(), _code()
    # サービス表の `name` 列（型列の mirs_msgs/xxx を除くためバッククォート単語を抽出）
    names = set(re.findall(r"`([a-z_]+)`", contract))
    srvs = {n for n in names if n in
            ("esp_cmd", "esp_update", "reboot", "reset_encoder")}
    assert srvs == {"esp_cmd", "esp_update", "reboot", "reset_encoder"}
    for s in srvs:
        assert f'"{s}"' in code or f"'{s}'" in code, f"service {s} not found"


def test_contract_launch_args_exist_in_hardware():
    contract = _contract()
    hw = (ROOT / "launch/mirs_hardware.launch.py").read_text()
    args = set(re.findall(r"`(enable_[a-z_]+|urdf_file|ekf_config_file"
                          r"|esp_port|lidar_port|lidar_baudrate"
                          r"|use_sim_time)`", contract))
    assert len(args) >= 10, f"too few launch args documented: {args}"
    for a in args:
        assert f"'{a}'" in hw, f"launch arg {a} missing in mirs_hardware"


def test_contract_frames_exist_in_code_or_urdf():
    contract = _contract()
    frames = set(re.findall(r"`(odom|base_link|base_footprint|laser|map)`",
                            contract))
    assert {"odom", "base_link"}.issubset(frames)
    hay = _code() + (ROOT / "urdf/mirs_2.urdf").read_text()
    for f in frames:
        assert f in hay, f"frame {f} not found"
