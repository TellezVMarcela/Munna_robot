"""
Launch file principal del robot minisumo.

Argumentos:
  mode        := autonomous | teleop   (default: autonomous)
  use_joystick:= true | false          (default: true)
  sim_sensors := true | false          (default: false)
  serial_port := /dev/ttyUSB0         (default)

Uso:
  # Competencia autónoma:
  ros2 launch minisumo_robot minisumo.launch.py

  # Teleoperación con joystick:
  ros2 launch minisumo_robot minisumo.launch.py mode:=teleop use_joystick:=true

  # Teleoperación con teclado:
  ros2 launch minisumo_robot minisumo.launch.py mode:=teleop use_joystick:=false

  # Simulación (sin hardware):
  ros2 launch minisumo_robot minisumo.launch.py sim_sensors:=true
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, GroupAction
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():

    # ── Argumentos ────────────────────────────────────────────────────────────
    mode_arg = DeclareLaunchArgument(
        'mode', default_value='autonomous',
        description='Modo inicial: autonomous o teleop')

    joystick_arg = DeclareLaunchArgument(
        'use_joystick', default_value='true',
        description='true = control físico, false = teclado')

    sim_arg = DeclareLaunchArgument(
        'sim_sensors', default_value='false',
        description='true = sensores simulados (sin hardware)')

    port_arg = DeclareLaunchArgument(
        'serial_port', default_value='/dev/ttyUSB0',
        description='Puerto serial del ESP32/Arduino')

    mode       = LaunchConfiguration('mode')
    joy_mode   = LaunchConfiguration('use_joystick')
    sim        = LaunchConfiguration('sim_sensors')
    serial_port = LaunchConfiguration('serial_port')

    # ── Nodo gestor de modo ───────────────────────────────────────────────────
    mode_manager = Node(
        package='minisumo_robot',
        executable='mode_manager',
        name='mode_manager',
        output='screen',
        parameters=[{'default_mode': mode}],
        remappings=[
            ('/autonomous/cmd_vel', '/autonomous/cmd_vel'),
            ('/teleop/cmd_vel',     '/teleop/cmd_vel'),
        ]
    )

    # ── Sensores ──────────────────────────────────────────────────────────────
    sensor_node = Node(
        package='minisumo_robot',
        executable='sensor_node',
        name='sensor_node',
        output='screen',
        parameters=[{
            'serial_port': serial_port,
            'sim_mode':    sim,
        }]
    )

    # ── Motor driver ──────────────────────────────────────────────────────────
    motor_driver = Node(
        package='minisumo_robot',
        executable='motor_driver',
        name='motor_driver',
        output='screen',
        parameters=[{
            'serial_port': serial_port,
            'wheel_base':  0.10,
            'max_pwm':     255,
            'min_pwm':     60,
        }]
    )

    # ── Nodo autónomo – remapea /cmd_vel → /autonomous/cmd_vel ───────────────
    autonomous_node = Node(
        package='minisumo_robot',
        executable='autonomous_node',
        name='autonomous_controller',
        output='screen',
        parameters=[{
            'attack_speed':  0.5,
            'search_speed':  1.2,
            'reverse_speed': 0.35,
            'detect_dist':   0.30,
        }],
        remappings=[('/cmd_vel', '/autonomous/cmd_vel')]
    )

    # ── Teleop con joystick ───────────────────────────────────────────────────
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        output='screen',
        condition=IfCondition(joy_mode)
    )

    teleop_joystick = Node(
        package='minisumo_robot',
        executable='teleop_node',
        name='teleop_joystick',
        output='screen',
        condition=IfCondition(joy_mode),
        remappings=[('/cmd_vel', '/teleop/cmd_vel')]
    )

    # ── Teleop con teclado ────────────────────────────────────────────────────
    teleop_keyboard = Node(
        package='minisumo_robot',
        executable='teleop_node',
        name='teleop_keyboard',
        output='screen',
        condition=UnlessCondition(joy_mode),
        arguments=['--keyboard'],
        remappings=[('/cmd_vel', '/teleop/cmd_vel')]
    )

    return LaunchDescription([
        mode_arg,
        joystick_arg,
        sim_arg,
        port_arg,
        LogInfo(msg=['🤖 Minisumo – modo: ', mode, ' | joystick: ', joy_mode]),
        sensor_node,
        motor_driver,
        mode_manager,
        autonomous_node,
        joy_node,
        teleop_joystick,
        teleop_keyboard,
    ])
