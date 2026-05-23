#!/usr/bin/env python3
"""
MUNNA — Nodo Autónomo (rutinas predefinidas)

Rutinas disponibles:
  - ZIGZAG  (botón Cuadrado del PS3)
  - CIRCULO (botón Círculo del PS3)
  - AUTO    (botón X del PS3) → alterna entre ZIGZAG y CIRCULO

Suscribe:
  /munna/mode          (String) — "TELEOP" o "AUTONOMO"
  /rutina              (String) — "ZIGZAG", "CIRCULO", "AUTO"
  /sensors/ultrasonic  (Float32MultiArray) — para futuro esquive

Publica:
  /autonomous/cmd_vel  (Twist)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String, Float32MultiArray


class AutonomousNode(Node):

    # ----------------- Estados internos -----------------
    EST_AVANCE = "AVANCE"
    EST_GIRO   = "GIRO"
    EST_PAUSA  = "PAUSA"
    EST_CICLO  = "CICLO"

    # ----------------- Parámetros de ZIGZAG -----------------
    T_AVANCE_S  = 2.0
    T_GIRO_S    = 1.3
    T_PAUSA_S   = 0.8
    V_AVANCE    = 0.13
    V_GIRO      = 0.8

    # ----------------- Parámetros de CIRCULO -----------------
    V_CIRCULO_LIN = 0.14
    V_CIRCULO_ANG = 1.0

    # ----------------- Parámetros de AUTO -----------------
    T_AUTO_ZIGZAG_S  = 15.0
    T_AUTO_CIRCULO_S = 15.0

    def __init__(self):
        super().__init__('munna_autonomous')

        self.activo = False
        self.rutina = None
        self.estado_rutina = None
        self.t_estado_inicio = self.get_clock().now()
        self.contador_lados = 0

        # Estado de AUTO
        self.auto_subrutina = "ZIGZAG"
        self.t_auto_inicio = self.get_clock().now()

        # Distancias (para futuro esquive)
        self.dist_front = 999.0
        self.dist_izq   = 999.0
        self.dist_der   = 999.0

        self.cmd_pub = self.create_publisher(Twist, '/autonomous/cmd_vel', 10)
        self.create_subscription(String, '/munna/mode', self.mode_cb, 10)
        self.create_subscription(String, '/rutina',     self.rutina_cb, 10)
        self.create_subscription(Float32MultiArray, '/sensors/ultrasonic',
                                 self.sensors_cb, 10)
        self.create_timer(0.05, self.ciclo_control)

        self.get_logger().info('Nodo Autonomo iniciado.')
        self.get_logger().info('  Rutinas disponibles: ZIGZAG, CIRCULO, AUTO')
        self.get_logger().info('  Esperando /munna/mode = "AUTONOMO" y rutina del PS3')

    # ---------------------------------------------------------------------
    def mode_cb(self, msg: String):
        nuevo_modo = msg.data.strip().upper()
        if nuevo_modo == "AUTONOMO" and not self.activo:
            self.activo = True
            self.rutina = None
            self.estado_rutina = None
            self.get_logger().info(
                '>> Activado en modo AUTONOMO · IDLE '
                '(esperando boton de rutina del PS3)'
            )
            self.cmd_pub.publish(Twist())

        elif nuevo_modo == "TELEOP" and self.activo:
            self.activo = False
            self.rutina = None
            self.estado_rutina = None
            self.get_logger().info('>> Desactivado (modo TELEOP)')
            self.cmd_pub.publish(Twist())

    def rutina_cb(self, msg: String):
        nueva_rutina = msg.data.strip().upper()

        if nueva_rutina not in ("ZIGZAG", "CIRCULO", "AUTO"):
            self.get_logger().warn(
                f'Rutina "{msg.data}" no disponible. Opciones: ZIGZAG, CIRCULO, AUTO'
            )
            return

        if not self.activo:
            self.rutina = nueva_rutina
            self.get_logger().info(
                f'Rutina preseleccionada: {self.rutina} '
                f'(se ejecutara al entrar en modo AUTONOMO)'
            )
            return

        if nueva_rutina != self.rutina:
            self.rutina = nueva_rutina
            self.reset_rutina()
            self.get_logger().info(f'>> Rutina: {self.rutina}')

    def sensors_cb(self, msg: Float32MultiArray):
        if len(msg.data) >= 3:
            self.dist_front = msg.data[0]
            self.dist_izq   = msg.data[1]
            self.dist_der   = msg.data[2]

    # ---------------------------------------------------------------------
    def reset_rutina(self):
        if self.rutina == "ZIGZAG":
            self.estado_rutina = self.EST_AVANCE
            self.contador_lados = 0
        elif self.rutina == "CIRCULO":
            self.estado_rutina = self.EST_CICLO
        elif self.rutina == "AUTO":
            self.auto_subrutina = "ZIGZAG"
            self.estado_rutina = self.EST_AVANCE
            self.contador_lados = 0
            self.t_auto_inicio = self.get_clock().now()
        else:
            self.estado_rutina = None
        self.t_estado_inicio = self.get_clock().now()

    def tiempo_en_estado(self):
        ahora = self.get_clock().now()
        return (ahora - self.t_estado_inicio).nanoseconds * 1e-9

    def cambiar_estado(self, nuevo):
        self.estado_rutina = nuevo
        self.t_estado_inicio = self.get_clock().now()

    # ---------------------------------------------------------------------
    def ciclo_control(self):
        if not self.activo:
            return

        if self.rutina is None:
            self.cmd_pub.publish(Twist())
            return

        if self.rutina == "ZIGZAG":
            twist = self.ejecutar_zigzag()
        elif self.rutina == "CIRCULO":
            twist = self.ejecutar_circulo()
        elif self.rutina == "AUTO":
            twist = self.ejecutar_auto()
        else:
            twist = Twist()

        self.cmd_pub.publish(twist)

    # ---------------------------------------------------------------------
    def ejecutar_zigzag(self) -> Twist:
        twist = Twist()
        dt = self.tiempo_en_estado()

        if self.estado_rutina == self.EST_AVANCE:
            twist.linear.x  = self.V_AVANCE
            twist.angular.z = 0.0
            if dt >= self.T_AVANCE_S:
                self.cambiar_estado(self.EST_GIRO)
                self.get_logger().info(
                    f'  Zigzag: segmento {self.contador_lados+1} completo'
                )

        elif self.estado_rutina == self.EST_GIRO:
            twist.linear.x  = 0.0
            twist.angular.z = self.V_GIRO
            if dt >= self.T_GIRO_S:
                self.contador_lados += 1
                if self.contador_lados >= 4:
                    self.cambiar_estado(self.EST_PAUSA)
                    self.get_logger().info('  Zigzag: ciclo completo, pausa breve')
                else:
                    self.cambiar_estado(self.EST_AVANCE)

        elif self.estado_rutina == self.EST_PAUSA:
            twist.linear.x  = 0.0
            twist.angular.z = 0.0
            if dt >= self.T_PAUSA_S:
                self.contador_lados = 0
                self.cambiar_estado(self.EST_AVANCE)
                self.get_logger().info('  Zigzag: reiniciando ciclo')

        return twist

    # ---------------------------------------------------------------------
    def ejecutar_circulo(self) -> Twist:
        twist = Twist()
        twist.linear.x  = self.V_CIRCULO_LIN
        twist.angular.z = self.V_CIRCULO_ANG
        return twist

    # ---------------------------------------------------------------------
    def ejecutar_auto(self) -> Twist:
        """
        Alterna automáticamente entre ZIGZAG y CIRCULO cada cierto tiempo.
        """
        ahora = self.get_clock().now()
        dt_auto = (ahora - self.t_auto_inicio).nanoseconds * 1e-9

        # Cambio automático de subrutina
        if self.auto_subrutina == "ZIGZAG" and dt_auto >= self.T_AUTO_ZIGZAG_S:
            self.auto_subrutina = "CIRCULO"
            self.estado_rutina = self.EST_CICLO
            self.t_auto_inicio = ahora
            self.t_estado_inicio = ahora
            self.get_logger().info('  AUTO: cambio a CIRCULO')

        elif self.auto_subrutina == "CIRCULO" and dt_auto >= self.T_AUTO_CIRCULO_S:
            self.auto_subrutina = "ZIGZAG"
            self.estado_rutina = self.EST_AVANCE
            self.contador_lados = 0
            self.t_auto_inicio = ahora
            self.t_estado_inicio = ahora
            self.get_logger().info('  AUTO: cambio a ZIGZAG')

        # Ejecutar la subrutina activa
        if self.auto_subrutina == "ZIGZAG":
            return self.ejecutar_zigzag()
        else:
            return self.ejecutar_circulo()


def main(args=None):
    rclpy.init(args=args)
    node = AutonomousNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()