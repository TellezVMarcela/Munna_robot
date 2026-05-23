#!/usr/bin/env python3
"""
MUNNA — Mode Manager (multiplexor de comandos de movimiento)

Selecciona entre /teleop/cmd_vel y /autonomous/cmd_vel según /munna/mode,
y reenvía el ganador a /cmd_vel (que es el que escucha la ESP32).

Suscribe:
  /teleop/cmd_vel      (Twist)
  /autonomous/cmd_vel  (Twist)
  /munna/mode          (String)  — "TELEOP" o "AUTONOMO"

Publica:
  /cmd_vel             (Twist)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String


class ModeManager(Node):

    MODO_TELEOP   = "TELEOP"
    MODO_AUTONOMO = "AUTONOMO"

    def __init__(self):
        super().__init__('munna_mode_manager')

        # Estado inicial: TELEOP (por seguridad, sin movimiento autónomo al arrancar)
        self.modo_actual = self.MODO_TELEOP

        # Último Twist recibido de cada fuente
        self.ultimo_twist_teleop     = Twist()
        self.ultimo_twist_autonomous = Twist()

        # Publicador hacia la ESP32
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Suscripciones
        self.create_subscription(Twist,  '/teleop/cmd_vel',     self.teleop_cb,     10)
        self.create_subscription(Twist,  '/autonomous/cmd_vel', self.autonomous_cb, 10)
        self.create_subscription(String, '/munna/mode',         self.mode_cb,       10)

        # Timer de publicación a 50 Hz hacia /cmd_vel
        # (Garantiza un stream constante aunque alguna fuente deje de publicar)
        self.create_timer(0.02, self.publicar_cmd_vel)

        self.get_logger().info(f'Mode Manager iniciado. Modo inicial: {self.modo_actual}')
        self.get_logger().info('  Publica /cmd_vel · suscribe /teleop/cmd_vel, /autonomous/cmd_vel, /munna/mode')

    # ---------------------------------------------------------------------
    def teleop_cb(self, msg: Twist):
        self.ultimo_twist_teleop = msg

    def autonomous_cb(self, msg: Twist):
        self.ultimo_twist_autonomous = msg

    def mode_cb(self, msg: String):
        nuevo = msg.data.strip().upper()
        if nuevo in (self.MODO_TELEOP, self.MODO_AUTONOMO):
            if nuevo != self.modo_actual:
                self.modo_actual = nuevo
                self.get_logger().info(f'>> Modo cambiado a: {self.modo_actual}')
                # Al cambiar de modo, publica un Twist de seguridad (cero) inmediato
                self.cmd_pub.publish(Twist())
        else:
            self.get_logger().warn(f'Modo desconocido recibido: "{msg.data}"')

    # ---------------------------------------------------------------------
    def publicar_cmd_vel(self):
        """Republica a 50 Hz el Twist de la fuente activa."""
        if self.modo_actual == self.MODO_TELEOP:
            self.cmd_pub.publish(self.ultimo_twist_teleop)
        elif self.modo_actual == self.MODO_AUTONOMO:
            self.cmd_pub.publish(self.ultimo_twist_autonomous)
        else:
            self.cmd_pub.publish(Twist())  # ceros por seguridad


def main(args=None):
    rclpy.init(args=args)
    node = ModeManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()