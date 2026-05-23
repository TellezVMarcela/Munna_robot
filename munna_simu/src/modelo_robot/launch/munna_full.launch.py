"""
MUNNA - Launch unificado de simulacion en Gazebo Classic

Arranca con un solo comando:
  - Gazebo (mundo vacio, plugins ROS cargados)
  - robot_state_publisher con el URDF
  - joint_state_publisher
  - spawn del robot en (0, 0, 0.05)
  - joy_node (lectura del control PS3/PS4)
  - munna_nodes: teleop_node, mode_manager, autonomous_node

Uso:
  ros2 launch modelo_robot munna_full.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # --- Parametros y rutas ---
    package_name = 'modelo_robot'
    robot_name_in_model = 'munna'
    urdf_file_name = 'uurdf_munna.urdf'

    use_sim_time = LaunchConfiguration('use_sim_time')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='true',
        description='Usar reloj de simulacion (Gazebo) si true'
    )

    # --- URDF ---
    urdf = os.path.join(
        get_package_share_directory(package_name),
        'urdf',
        urdf_file_name
    )
    with open(urdf, 'r') as infp:
        robot_desc = infp.read()

    # --- Nodos basicos (robot description + estado) ---
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'use_sim_time': use_sim_time,
            'robot_description': robot_desc
        }]
    )

    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # --- Gazebo ---
    gazebo = ExecuteProcess(
        cmd=[
            'gazebo', '--verbose',
            '-s', 'libgazebo_ros_factory.so',
            '-s', 'libgazebo_ros_init.so'
        ],
        output='screen'
    )

    spawn = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', '/robot_description',
            '-entity', robot_name_in_model,
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.05',
            '-Y', '0.0'
        ]
    )

    # --- Control PS3/PS4 ---
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autorepeat_rate': 20.0,
            'deadzone': 0.1
        }]
    )

    # --- Nodos de Munna ---
    teleop_node = Node(
        package='munna_nodes',
        executable='teleop_node',
        name='munna_teleop',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )

    mode_manager_node = Node(
        package='munna_nodes',
        executable='mode_manager',
        name='munna_mode_manager',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )

    autonomous_node = Node(
        package='munna_nodes',
        executable='autonomous_node',
        name='munna_autonomous',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )

    return LaunchDescription([
        declare_use_sim_time_cmd,
        # 1) Gazebo primero (debe estar listo antes del spawn)
        gazebo,
        # 2) Publishers del modelo
        robot_state_publisher_node,
        joint_state_publisher_node,
        # 3) Spawn del robot
        spawn,
        # 4) Control y nodos de Munna
        joy_node,
        teleop_node,
        mode_manager_node,
        autonomous_node,
    ])
