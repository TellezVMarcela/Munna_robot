#!/usr/bin/env python3
"""
Munna – Gestor de modos
========================
GRAFCET N1:
  E1 Autónomo  → reenvía /autonomous/cmd_vel → /cmd_vel
  E2 Teleop    → reenvía /teleop/cmd_vel     → /cmd_vel
  Transición E1→E2: /mode_select = 'teleop'   (SHARE PS4)
  Transición E2→E1: /mode_select = 'autonomous' (OPTIONS PS4)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String


class ModeManager(Node):

    def __init__(self):
        super().__init__('mode_manager')

        self.declare_parameter('modo_inicial', 'autonomous')
        self.modo = self.get_parameter('modo_inicial').value

        # Publicador salida
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Suscriptores fuentes
        self.create_subscription(Twist,  '/autonomous/cmd_vel', self._auto_cb,  10)
        self.create_subscription(Twist,  '/teleop/cmd_vel',     self._teleop_cb, 10)
        self.create_subscription(String, '/mode_select',        self._mode_cb,   10)

        self._auto_twist   = Twist()
        self._teleop_twist = Twist()

        self.create_timer(0.05, self._publicar)
        self._log_modo()

    def _auto_cb(self, msg):   self._auto_twist   = msg
    def _teleop_cb(self, msg): self._teleop_twist = msg

    def _mode_cb(self, msg):
        modo = msg.data.lower().strip()
        if modo in ('autonomous', 'teleop'):
            self.modo = modo
            self._log_modo()

    def _publicar(self):
        self.pub.publish(
            self._auto_twist if self.modo == 'autonomous'
            else self._teleop_twist)

    def _log_modo(self):
        icono = '🤖' if self.modo == 'autonomous' else '🕹️'
        self.get_logger().info(f'{icono} Modo: {self.modo.upper()}')


def main(args=None):
    rclpy.init(args=args)
    node = ModeManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
