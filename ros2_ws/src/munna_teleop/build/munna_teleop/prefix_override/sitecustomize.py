import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/fairytale/ros2_ws/src/munna_teleop/install/munna_teleop'
