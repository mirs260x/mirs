# AGENTS.md — mirs

MIRS本体パッケージ（ハード・Nav2設定・launch）。CI: `pytest` ワークフロー（ROS不要テスト）。

## ブランチ運用

- `main` / `develop` 直commit・直push禁止。`feature/*` → `develop` → `main` のPRのみ
- 1コミット1話題。`git add -p` で分割する

## テスト・ビルド

```bash
python3 -m pytest test/ -q
colcon build --symlink-install --packages-select mirs
```

## 注意

- `config/navigation/nav2_params.yaml` がNav2設定の単一真実
- launchの `slam` 引数は `'True'`/`'False'`（Pythonリテラル。小文字はNav2側の式評価で死ぬ）
- launchの数値引数は文字列で届く。Pythonノード側で寛容パースすること
- root権限を使う操作（apt等）はしない。ファイル参照・編集とworkspace内コマンドのみ
