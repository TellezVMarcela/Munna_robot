#!/usr/bin/env python3
"""
Nodo de teleoperación para robot minisumo.
Soporta:
  1. Teclado  – ejecutar con argumento --keyboard
  2. Joystick / Control (gamepad) – topic /joy de joy_node

Publicación:
  /cmd_vel   Twist
"""

import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
import threading

# ─── Mapa de teclas (modo teclado) ──────────────────────────────────────────
KEY_BINDINGS = {
    'w': ( 1,  0),   # adelante
    's': (-1,  0),   # atrás
    'a': ( 0,  1),   # girar izquierda
    'd': ( 0, -1),   # girar derecha
    'q': ( 1,  1),   # diagonal izq-adelante
    'e': ( 1, -1),   # diagonal der-adelante
    ' ': ( 0,  0),   # stop (espacio)
}

TELEOP_HELP = """
╔══════════════════════════════════════╗
║   MINISUMO – Teleoperación Teclado   ║
╠══════════════════════════════════════╣
║  w / s  →  Adelante / Atrás          ║
║  a / d  →  Girar Izq / Der           ║
║  q / e  →  Diagonal Izq / Der        ║
║  SPACE  →  Stop                      ║
║  +/-    →  Aumentar/reducir vel      ║
║  Ctrl+C →  Salir                     ║
╚══════════════════════════════════════╝
"""


class TeleopNode(Node):
    """
    Nodo de teleoperación que acepta entrada de teclado O joystick.

    Joystick (joy_node):
      Eje 1 (stick izquierdo vertical)  → velocidad lineal
      Eje 0 (stick izquierdo horizontal)→ velocidad angular
      Botón 4 (LB) → turbo
    """

    MAX_LINEAR  = 0.5   # m/s
    MAX_ANGULAR = 2.0   # rad/s
    TURBO_MULT  = 1.8

    def __init__(self, use_keyboard: bool = False):
        super().__init__('teleop_node')

        self.declare_parameter('max_linear',  self.MAX_LINEAR)
        self.declare_parameter('max_angular', self.MAX_ANGULAR)
        self.declare_parameter('turbo_mult',  self.TURBO_MULT)

        self.max_linear  = self.get_parameter('max_linear').value
        self.max_angular = self.get_parameter('max_angular').value
        self.turbo_mult  = self.get_parameter('turbo_mult').value
        self.speed_scale = 1.0

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        if use_keyboard:
            self._start_keyboard_thread()
        else:
            self.create_subscription(Joy, '/joy', self._joy_cb, 10)
            self.get_logger().info(
                '🎮  Modo joystick activo – conecta tu control y ejecuta joy_node')

        self.get_logger().info('✅  Nodo de teleoperación iniciado')

    # ─────────────────────────── Joystick ────────────────────────────────────

    def _joy_cb(self, msg: Joy):
        twist = Twist()
        turbo = msg.buttons[4] if len(msg.buttons) > 4 else 0
        mult  = self.turbo_mult if turbo else 1.0

        if len(msg.axes) > 1:
            twist.linear.x  = msg.axes[1] * self.max_linear  * mult
            twist.angular.z = msg.axes[0] * self.max_angular * mult

        # Clamp
        twist.linear.x  = max(-self.max_linear,  min(self.max_linear,  twist.linear.x))
        twist.angular.z = max(-self.max_angular, min(self.max_angular, twist.angular.z))

        self.cmd_pub.publish(twist)

    # ─────────────────────────── Teclado ─────────────────────────────────────

    def _start_keyboard_thread(self):
        """Lanza un hilo para leer teclas sin bloquear el spin de ROS."""
        print(TELEOP_HELP)
        t = threading.Thread(target=self._keyboard_loop, daemon=True)
        t.start()

    def _keyboard_loop(self):
        import tty
        import termios

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while rclpy.ok():
                ch = sys.stdin.read(1)

                if ch == '\x03':  # Ctrl+C
                    break

                if ch == '+':
                    self.speed_scale = min(2.0, self.speed_scale + 0.1)
                    self.get_logger().info(f'⚡ Velocidad: {self.speed_scale:.1f}x')
                    continue
                if ch == '-':
                    self.speed_scale = max(0.1, self.speed_scale - 0.1)
                    self.get_logger().info(f'🐢 Velocidad: {self.speed_scale:.1f}x')
                    continue

                twist = Twist()
                if ch in KEY_BINDINGS:
                    lin, ang = KEY_BINDINGS[ch]
                    twist.linear.x  = lin * self.max_linear  * self.speed_scale
                    twist.angular.z = ang * self.max_angular * self.speed_scale
                self.cmd_pub.publish(twist)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            # Enviar stop al salir
            self.cmd_pub.publish(Twist())


def main(args=None):
    rclpy.init(args=args)
    use_kb = '--keyboard' in sys.argv
    node = TeleopNode(use_keyboard=use_kb)
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
