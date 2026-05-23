#!/usr/bin/env python3
"""
Nodo gestor de modo de operación del minisumo.
Controla qué fuente de comandos llega al robot: autónomo o teleoperado.

Tópicos:
  SUB  /autonomous/cmd_vel  – comandos del nodo autónomo
  SUB  /teleop/cmd_vel      – comandos del nodo de teleoperación
  SUB  /mode_select         – String: 'autonomous' | 'teleop'
  PUB  /cmd_vel             – salida hacia el driver de motores
  PUB  /mode_status         – String con modo actual

Servicio:
  /set_mode  (std_srvs/SetBool) – True = autónomo, False = teleop
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from std_srvs.srv import SetBool


class ModeManager(Node):

    MODE_AUTONOMOUS = 'autonomous'
    MODE_TELEOP     = 'teleop'

    def __init__(self):
        super().__init__('mode_manager')

        self.declare_parameter('default_mode', self.MODE_AUTONOMOUS)
        self.current_mode = self.get_parameter('default_mode').value

        # ── Almacenamiento de últimos comandos ────────────────────────────────
        self._auto_twist  = Twist()
        self._teleop_twist = Twist()

        # ── Suscriptores de cada fuente ───────────────────────────────────────
        self.create_subscription(
            Twist, '/autonomous/cmd_vel', self._auto_cb, 10)
        self.create_subscription(
            Twist, '/teleop/cmd_vel', self._teleop_cb, 10)
        self.create_subscription(
            String, '/mode_select', self._mode_select_cb, 10)

        # ── Publicadores ──────────────────────────────────────────────────────
        self.cmd_pub    = self.create_publisher(Twist,  '/cmd_vel',     10)
        self.status_pub = self.create_publisher(String, '/mode_status', 10)

        # ── Servicio de cambio de modo ────────────────────────────────────────
        self.create_service(SetBool, '/set_mode', self._set_mode_srv)

        # ── Timer de publicación a 20 Hz ──────────────────────────────────────
        self.create_timer(0.05, self._publish_cmd)

        self._log_mode()

    # ─────────────────────────── Callbacks ───────────────────────────────────

    def _auto_cb(self, msg: Twist):
        self._auto_twist = msg

    def _teleop_cb(self, msg: Twist):
        self._teleop_twist = msg

    def _mode_select_cb(self, msg: String):
        mode = msg.data.lower().strip()
        if mode in (self.MODE_AUTONOMOUS, self.MODE_TELEOP):
            self.current_mode = mode
            self._log_mode()
        else:
            self.get_logger().warn(
                f"Modo desconocido: '{mode}'. Usa 'autonomous' o 'teleop'.")

    def _set_mode_srv(self, request: SetBool.Request,
                      response: SetBool.Response):
        self.current_mode = (self.MODE_AUTONOMOUS
                             if request.data else self.MODE_TELEOP)
        self._log_mode()
        response.success = True
        response.message = f'Modo cambiado a: {self.current_mode}'
        return response

    # ─────────────────────────── Publicación ─────────────────────────────────

    def _publish_cmd(self):
        if self.current_mode == self.MODE_AUTONOMOUS:
            self.cmd_pub.publish(self._auto_twist)
        else:
            self.cmd_pub.publish(self._teleop_twist)

        status = String()
        status.data = self.current_mode
        self.status_pub.publish(status)

    def _log_mode(self):
        icon = '🤖' if self.current_mode == self.MODE_AUTONOMOUS else '🕹️'
        self.get_logger().info(f'{icon}  Modo activo: {self.current_mode.upper()}')


def main(args=None):
    rclpy.init(args=args)
    node = ModeManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd_pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
