# サンプル地図

`es.yaml`と`es.pgm`は、地図読み込み・起動確認用の2D占有格子地図です。
YAMLには画像の参照先、解像度[m/pixel]、地図原点[m, m, rad]と占有判定閾値が含まれます。
実機の現在の環境に一致することは保証しません。

運用で作った地図はワークスペースの`maps/real/`へ保存し、
`ros2 launch mirs nav_launch.py map:=/home/developer/ws/maps/real/<名前>.yaml`
で指定してください。YAMLと画像は組で保存します。
