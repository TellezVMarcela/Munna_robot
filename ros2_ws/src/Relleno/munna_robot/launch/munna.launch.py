"""
Munna – Launch file
====================
Lanza todos los nodos + micro_ros_agent

Uso:
  # Modo autónomo (default):
  ros2 launch munna_robot munna.launch.py

  # Modo teleop inicial:
  ros2 launch munna_robot munna.launch.py modo_inicial:=teleop

  # Cambiar figura desde terminal:
  ros2 topic pub /rutina std_msgs/msg/String "data: 'circulo'" --once
  ros2 topic pub /rutina std_msgs/msg/String "data: 'cuadrado'" --once
  ros2 topic pub /rutina std_msgs/msg/String "data: 'auto'" --once
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    modo_arg = DeclareLaunchArgument(
        'modo_inicial', default_value='autonomous',
        description='autonomous | teleop')

    modo = LaunchConfiguration('modo_inicial')

    # micro-ROS agent (WiFi UDP puerto 8888)
    agent = ExecuteProcess(
        cmd=['ros2', 'run', 'micro_ros_agent',
             'micro_ros_agent', 'udp4', '--port', '8888'],
        output='screen')

    # joy_node para PS4
    joy = Node(
        package='joy', executable='joy_node',
        name='joy_node', output='screen')

    # Nodos Munna
    autonomo = Node(
        package='munna_robot', executable='munna_autonomo',
        name='munna_autonomo', output='screen',
        parameters=[{
            'lado_m':     0.5,
            'vel_lin':    0.2,
            'vel_ang':    0.8,
            't_auto':     10.0,
            't_esquivar': 0.5,
        }],
        remappings=[('/autonomous/cmd_vel', '/autonomous/cmd_vel')])

    teleop = Node(
        package='munna_robot', executable='munna_teleop',
        name='munna_teleop', output='screen')

    manager = Node(
        package='munna_robot', executable='munna_mode_manager',
        name='mode_manager', output='screen',
        parameters=[{'modo_inicial': modo}])

    return LaunchDescription([
        modo_arg,
        agent,
        joy,
        autonomo,
        teleop,
        manager,
    ])
