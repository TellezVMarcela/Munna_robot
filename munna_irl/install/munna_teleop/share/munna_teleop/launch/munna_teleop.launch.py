from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([

        # Driver del joystick
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            parameters=[{
                'device_id': 0,
                'deadzone': 0.0,
                'autorepeat_rate': 50.0,
            }],
        ),

        # Nodo de teleoperación
        Node(
            package='munna_teleop',
            executable='teleop_node',
            name='munna_teleop',
            output='screen',
        ),

        # Nodo autónomo
        Node(
            package='munna_teleop',
            executable='autonomous_node',
            name='munna_autonomous',
            output='screen',
        ),

        # Multiplexor de modo
        Node(
            package='munna_teleop',
            executable='mode_manager',
            name='munna_mode_manager',
            output='screen',
        ),
    ])