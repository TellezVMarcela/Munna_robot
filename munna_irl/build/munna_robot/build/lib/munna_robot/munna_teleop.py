#!/usr/bin/env python3
"""
Munna – Nodo teleoperación PS4
================================
Botones PS4 (joy_node):
  OPTIONS  (9) → modo autónomo
  SHARE    (8) → modo teleop
  X/Cruz   (0) → rutina AUTO (alterna)
  Círculo  (1) → rutina fija CÍRCULO
  Cuadrado (3) → rutina fija CUADRADO

Ejes:
  axes[1] → velocidad lineal  (stick izq vertical)
  axes[0] → velocidad angular (stick izq horizontal)
  buttons[6] → L2 turbo

Tópicos:
  SUB  /joy              → sensor_msgs/Joy
  PUB  /teleop/cmd_vel   → Twist
  PUB  /mode_select      → String ('autonomous' | 'teleop')
  PUB  /rutina           → String ('auto' | 'cuadrado' | 'circulo')
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from std_msgs.msg import String


class MunnaTeleop(Node):

    MAX_LIN = 0.3    # m/s
    MAX_ANG = 1.5    # rad/s
    TURBO   = 1.8    # multiplicador L2

    def __init__(self):
        super().__init__('munna_teleop')

        self.pub_cmd  = self.create_publisher(Twist,  '/teleop/cmd_vel', 10)
        self.pub_mode = self.create_publisher(String, '/mode_select',    10)
        self.pub_rut  = self.create_publisher(String, '/rutina',         10)

        self.create_subscription(Joy, '/joy', self._joy_cb, 10)

        # Control de botones (evita repetición al mantener presionado)
        self._btn_prev = []

        self.get_logger().info('✅ Munna teleop iniciado')

    def _joy_cb(self, msg: Joy):
        btns = list(msg.buttons)
        axes = list(msg.axes)

        # Inicializar estado previo
        if not self._btn_prev:
            self._btn_prev = [0] * len(btns)

        def presionado(i):
            return i < len(btns) and btns[i] == 1 and self._btn_prev[i] == 0

        # ── Cambio de modo ────────────────────────────────────
        if presionado(9):   # OPTIONS → autónomo
            self._publicar_modo('autonomous')

        if presionado(8):   # SHARE → teleop
            self._publicar_modo('teleop')

        # ── Selección de rutina (solo en modo autónomo) ───────
        if presionado(0):   # X → AUTO (alterna)
            self._publicar_rutina('auto')

        if presionado(1):   # Círculo → rutina círculo fija
            self._publicar_rutina('circulo')

        if presionado(3):   # Cuadrado → rutina cuadrado fija
            self._publicar_rutina('cuadrado')

        # ── Velocidades teleop ────────────────────────────────
        turbo = self.TURBO if len(btns) > 6 and btns[6] else 1.0
        twist = Twist()
        if len(axes) > 1:
            twist.linear.x  = axes[1] * self.MAX_LIN * turbo
            twist.angular.z = axes[0] * self.MAX_ANG * turbo
        self.pub_cmd.publish(twist)

        self._btn_prev = btns

    def _publicar_modo(self, modo: str):
        msg = String()
        msg.data = modo
        self.pub_mode.publish(msg)
        self.get_logger().info(f'Modo → {modo}')

    def _publicar_rutina(self, rutina: str):
        msg = String()
        msg.data = rutina
        self.pub_rut.publish(msg)
        self.get_logger().info(f'Rutina → {rutina}')


def main(args=None):
    rclpy.init(args=args)
    node = MunnaTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub_cmd.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
