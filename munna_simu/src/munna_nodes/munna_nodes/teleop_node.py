#!/usr/bin/env python3
"""
MUNNA — Nodo de teleoperación (PS3 GUO_HUA → ROS2)

Publica:
  /teleop/cmd_vel  (Twist)  — comandos de movimiento desde el stick
  /munna/mode      (String) — modo seleccionado: "TELEOP" o "AUTONOMO"
  /rutina          (String) — rutina autónoma: "AUTO", "CUADRADO", "CIRCULO"

Suscribe:
  /joy             (Joy)

Esquema de control del PS3:
  Stick izquierdo Y (axes[1])  → velocidad lineal (avance/retroceso)
  Stick izquierdo X (axes[0])  → velocidad angular (giro)
  L1 (buttons[4])  mantenido   → modo preciso (30%)
  R1 (buttons[5])  mantenido   → modo turbo  (100%)
  Sin modificadores            → modo normal (60%)
  Select (buttons[8])          → modo TELEOP
  Start  (buttons[9])          → modo AUTONOMO
  X      (buttons[0])          → rutina AUTO (alterna)
  Circulo (buttons[1])         → rutina CIRCULO
  Cuadrado (buttons[3])        → rutina CUADRADO
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist
from std_msgs.msg import String


class TeleopNode(Node):

    # Valores por defecto
    MAX_LINEAR   = 0.30   # m/s
    MAX_ANGULAR  = 4.00   # rad/s
    SCALE_NORMAL = 0.60
    SCALE_SLOW   = 0.30
    SCALE_TURBO  = 1.00
    DEADZONE     = 0.20

    # Mapeo del GUO_HUA PS3 GamePad
    AX_LIN       = 1   # stick izquierdo Y
    AX_ANG       = 0   # stick izquierdo X
    BTN_L1       = 4
    BTN_R1       = 5
    BTN_SELECT   = 8   # → TELEOP
    BTN_START    = 9   # → AUTONOMO
    BTN_X        = 0   # → rutina AUTO
    BTN_CIRCULO  = 1   # → rutina CIRCULO
    BTN_CUADRADO = 3   # → rutina Zigzag

    def __init__(self):
        super().__init__('munna_teleop')

        # Parámetros declarables
        self.declare_parameter('max_linear',   self.MAX_LINEAR)
        self.declare_parameter('max_angular',  self.MAX_ANGULAR)
        self.declare_parameter('scale_normal', self.SCALE_NORMAL)
        self.declare_parameter('scale_slow',   self.SCALE_SLOW)
        self.declare_parameter('scale_turbo',  self.SCALE_TURBO)
        self.declare_parameter('deadzone',     self.DEADZONE)

        self.max_linear   = self.get_parameter('max_linear').value
        self.max_angular  = self.get_parameter('max_angular').value
        self.scale_normal = self.get_parameter('scale_normal').value
        self.scale_slow   = self.get_parameter('scale_slow').value
        self.scale_turbo  = self.get_parameter('scale_turbo').value
        self.deadzone     = self.get_parameter('deadzone').value

        # Publishers
        self.cmd_pub    = self.create_publisher(Twist,  '/teleop/cmd_vel', 10)
        self.mode_pub   = self.create_publisher(String, '/munna/mode',     10)
        self.rutina_pub = self.create_publisher(String, '/rutina',         10)

        # Subscriber
        self.create_subscription(Joy, '/joy', self.joy_cb, 10)

        # Estado anterior de los botones (para detección por flanco)
        self.prev_btn_select   = 0
        self.prev_btn_start    = 0
        self.prev_btn_x        = 0
        self.prev_btn_circulo  = 0
        self.prev_btn_cuadrado = 0

        self.get_logger().info('MUNNA teleop iniciado.')
        self.get_logger().info(
            f'  max_linear  = {self.max_linear} m/s'
        )
        self.get_logger().info(
            f'  max_angular = {self.max_angular} rad/s'
        )
        self.get_logger().info('  Publica /teleop/cmd_vel · /munna/mode · /rutina')

    # ---------------------------------------------------------------------
    def deadzone_filter(self, v):
        return 0.0 if abs(v) < self.deadzone else v

    def select_scale(self, msg: Joy):
        l1 = msg.buttons[self.BTN_L1] if len(msg.buttons) > self.BTN_L1 else 0
        r1 = msg.buttons[self.BTN_R1] if len(msg.buttons) > self.BTN_R1 else 0
        if r1:
            return self.scale_turbo
        if l1:
            return self.scale_slow
        return self.scale_normal

    def detectar_flanco(self, actual, previo):
        """Devuelve True solo si pasó de 0 a 1 en este ciclo."""
        return (actual == 1) and (previo == 0)

    # ---------------------------------------------------------------------
    def joy_cb(self, msg: Joy):
        # --- 1) Publicar Twist ---
        twist = Twist()

        if len(msg.axes) > max(self.AX_LIN, self.AX_ANG):
            scale = self.select_scale(msg)
            ax_lin = self.deadzone_filter(msg.axes[self.AX_LIN])
            ax_ang = self.deadzone_filter(msg.axes[self.AX_ANG])

            twist.linear.x  = ax_ang * self.max_linear  * scale   # axes[0] (horizontal) → avance, invertido
            twist.angular.z = ax_lin * self.max_angular * scale   # axes[1] (vertical)   → giro, invertido

            twist.linear.x  = max(-self.max_linear,  min(self.max_linear,  twist.linear.x))
            twist.angular.z = max(-self.max_angular, min(self.max_angular, twist.angular.z))

        self.cmd_pub.publish(twist)

        # --- 2) Detectar Select / Start (cambio de modo) ---
        if len(msg.buttons) > max(self.BTN_SELECT, self.BTN_START):
            btn_select = msg.buttons[self.BTN_SELECT]
            btn_start  = msg.buttons[self.BTN_START]

            if self.detectar_flanco(btn_select, self.prev_btn_select):
                m = String()
                m.data = "TELEOP"
                self.mode_pub.publish(m)
                self.get_logger().info('Modo → TELEOP')

            if self.detectar_flanco(btn_start, self.prev_btn_start):
                m = String()
                m.data = "AUTONOMO"
                self.mode_pub.publish(m)
                self.get_logger().info('Modo → AUTONOMO')

            self.prev_btn_select = btn_select
            self.prev_btn_start  = btn_start

        # --- 3) Detectar X / Circulo / Cuadrado (rutina) ---
        if len(msg.buttons) > max(self.BTN_X, self.BTN_CIRCULO, self.BTN_CUADRADO):
            btn_x        = msg.buttons[self.BTN_X]
            btn_circulo  = msg.buttons[self.BTN_CIRCULO]
            btn_cuadrado = msg.buttons[self.BTN_CUADRADO]

            if self.detectar_flanco(btn_x, self.prev_btn_x):
                r = String()
                r.data = "AUTO"
                self.rutina_pub.publish(r)
                self.get_logger().info('Rutina → AUTO (alterna)')

            if self.detectar_flanco(btn_circulo, self.prev_btn_circulo):
                r = String()
                r.data = "CIRCULO"
                self.rutina_pub.publish(r)
                self.get_logger().info('Rutina → CIRCULO')

            if self.detectar_flanco(btn_cuadrado, self.prev_btn_cuadrado):
                r = String()
                r.data = "ZIGZAG"
                self.rutina_pub.publish(r)
                self.get_logger().info('Rutina → ZIGZAG')

            self.prev_btn_x        = btn_x
            self.prev_btn_circulo  = btn_circulo
            self.prev_btn_cuadrado = btn_cuadrado


def main(args=None):
    rclpy.init(args=args)
    node = TeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()