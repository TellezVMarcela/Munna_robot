#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import math
import tf2_ros
import geometry_msgs.msg
import turtlesim.srv

class TurtleTF2Listener(Node):

    def __init__(self):
        super().__init__('turtle_tf2_listener')

        # Declarar parámetro para el nombre de la segunda tortuga
        self.declare_parameter('turtle', 'turtle2')
        turtle_name = self.get_parameter('turtle').get_parameter_value().string_value

        # Crear buffer y listener TF
        self.tfBuffer = tf2_ros.Buffer()
        self.listener = tf2_ros.TransformListener(self.tfBuffer, self)

        # Crear cliente del servicio spawn
        self.spawn_client = self.create_client(turtlesim.srv.Spawn, 'spawn')

        # Esperar a que el servicio esté disponible
        while not self.spawn_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Esperando el servicio "spawn"...')

        # Crear segunda tortuga
        self.spawn_turtle(4.0, 2.0, 0.0, turtle_name)

        # Publicador de velocidad
        self.turtle_vel = self.create_publisher(
            geometry_msgs.msg.Twist,
            f'/{turtle_name}/cmd_vel',
            10
        )

        # Timer para actualizar movimiento
        self.timer = self.create_timer(0.1, self.update_turtle_pose)

    def spawn_turtle(self, x, y, theta, name):
        request = turtlesim.srv.Spawn.Request()
        request.x = x
        request.y = y
        request.theta = theta
        request.name = name

        future = self.spawn_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

    def update_turtle_pose(self):
        turtle_name = self.get_parameter('turtle').get_parameter_value().string_value

        try:
            # Transformación desde turtle1 hacia turtle2
            trans = self.tfBuffer.lookup_transform(
                turtle_name,      # frame destino (turtle2)
                'turtle1',        # frame origen (turtle1)
                rclpy.time.Time()
            )

            msg = geometry_msgs.msg.Twist()

            # Control proporcional simple
            x = trans.transform.translation.x
            y = trans.transform.translation.y

            msg.angular.z = 4.0 * math.atan2(y, x)
            msg.linear.x = 0.5 * math.sqrt(x**2 + y**2)

            self.turtle_vel.publish(msg)

        except Exception:
            return


def main(args=None):
    rclpy.init(args=args)

    node = TurtleTF2Listener()
    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
