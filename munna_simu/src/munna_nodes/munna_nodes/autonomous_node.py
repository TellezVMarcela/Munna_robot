#!/usr/bin/env python3
"""
MUNNA — Nodo Autónomo con esquive ultrasónico (versión SIMULACIÓN Gazebo)

Diferencia con la versión del robot real:
  - En el robot, los 3 ultrasónicos se publicaban juntos en /sensors/ultrasonic
    como Float32MultiArray [front, izq, der] en cm desde la ESP32.
  - En Gazebo, cada sensor 'ray' publica su propio sensor_msgs/Range en metros.
    Aquí suscribimos los 3 topics y convertimos a cm para no tocar la lógica
    del esquive (que sigue usando UMBRAL_ESQUIVE_CM).

Rutinas disponibles:
  - ZIGZAG  (botón Cuadrado del PS3)
  - CIRCULO (botón Círculo del PS3)
  - AUTO    (botón X del PS3) → alterna entre ZIGZAG y CIRCULO

Esquive:
  Cualquier rutina pausa si detecta un obstáculo a menos de 15 cm.
  Retrocede 0.5 s, gira hacia el lado libre, y reanuda la rutina.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from sensor_msgs.msg import LaserScan
from rclpy.qos import qos_profile_sensor_data

class AutonomousNode(Node):

    # ----------------- Estados internos -----------------
    EST_AVANCE = "AVANCE"
    EST_GIRO   = "GIRO"
    EST_PAUSA  = "PAUSA"
    EST_CICLO  = "CICLO"

    # ----------------- Parámetros de ZIGZAG -----------------
    T_AVANCE_S  = 0.5
    T_GIRO_S    = 5.0
    T_PAUSA_S   = 0.5
    V_AVANCE    = 0.15
    V_GIRO      = 1.5

    # ----------------- Parámetros de CIRCULO -----------------
    V_CIRCULO_LIN = 0.02
    V_CIRCULO_ANG = 2.0

    # ----------------- Parámetros de AUTO -----------------
    T_AUTO_ZIGZAG_S  = 15.0
    T_AUTO_CIRCULO_S = 15.0

    # ----------------- Parámetros de ESQUIVE -----------------
    UMBRAL_ESQUIVE_CM   = 15.0
    T_RETROCESO_S       = 0.5
    T_GIRO_ESQUIVE_S    = 0.5
    V_RETROCESO         = 0.1
    V_GIRO_ESQUIVE      = 0.1

    # Fases del esquive
    ESQ_INACTIVO  = "INACTIVO"
    ESQ_RETROCESO = "RETROCESO"
    ESQ_GIRO      = "GIRO"

    def __init__(self):
        super().__init__('munna_autonomous')

        self.activo = False
        self.rutina = None
        self.estado_rutina = None
        self.t_estado_inicio = self.get_clock().now()
        self.contador_lados = 0

        self.auto_subrutina = "ZIGZAG"
        self.t_auto_inicio = self.get_clock().now()

        self.esquive_fase = self.ESQ_INACTIVO
        self.t_esquive_inicio = self.get_clock().now()
        self.giro_esquive_dir = 1

        # Distancias en cm (inicializadas a 999 = libre, hasta que llegue dato real)
        self.dist_front = 999.0
        self.dist_izq   = 999.0
        self.dist_der   = 999.0

        self.cmd_pub = self.create_publisher(Twist, '/autonomous/cmd_vel', 10)

        self.create_subscription(String, '/munna/mode', self.mode_cb, 10)
        self.create_subscription(String, '/rutina',     self.rutina_cb, 10)

        # 3 sensores Range desde Gazebo (publicados en metros)
        self.create_subscription(LaserScan, '/sensors/front', self.front_cb, qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/sensors/izq',   self.izq_cb,   qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/sensors/der',   self.der_cb,   qos_profile_sensor_data)

        self.create_timer(0.05, self.ciclo_control)

        self.get_logger().info('Nodo Autonomo (SIM) iniciado.')
        self.get_logger().info('  Rutinas disponibles: ZIGZAG, CIRCULO, AUTO')
        self.get_logger().info(f'  Esquive activo: < {self.UMBRAL_ESQUIVE_CM} cm')
        self.get_logger().info('  Esperando /munna/mode = "AUTONOMO"')

    # ---------------------------------------------------------------------
    # CALLBACKS
    # ---------------------------------------------------------------------
    def mode_cb(self, msg: String):
        nuevo_modo = msg.data.strip().upper()
        if nuevo_modo == "AUTONOMO" and not self.activo:
            self.activo = True
            self.rutina = None
            self.estado_rutina = None
            self.esquive_fase = self.ESQ_INACTIVO
            self.get_logger().info(
                '>> Activado en modo AUTONOMO · IDLE '
                '(esperando boton de rutina del PS3)'
            )
            self.cmd_pub.publish(Twist())

        elif nuevo_modo == "TELEOP" and self.activo:
            self.activo = False
            self.rutina = None
            self.estado_rutina = None
            self.esquive_fase = self.ESQ_INACTIVO
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
            self.get_logger().info(f'Rutina preseleccionada: {self.rutina}')
            return

        if nueva_rutina != self.rutina:
            self.rutina = nueva_rutina
            self.reset_rutina()
            self.esquive_fase = self.ESQ_INACTIVO
            self.get_logger().info(f'>> Rutina: {self.rutina}')

    # --- Sensores (m → cm) ----------------------------------------------
    # --- Callbacks de sensores (LaserScan → cm, tomamos el rayo más cercano) ---
    def front_cb(self, msg: LaserScan):
        rangos_validos = [r for r in msg.ranges if msg.range_min <= r <= msg.range_max]
        if rangos_validos:
            self.dist_front = min(rangos_validos) * 100.0
        else:
            self.dist_front = 999.0   # Sin obstáculo a la vista

    def izq_cb(self, msg: LaserScan):
        rangos_validos = [r for r in msg.ranges if msg.range_min <= r <= msg.range_max]
        if rangos_validos:
            self.dist_izq = min(rangos_validos) * 100.0
        else:
            self.dist_izq = 999.0

    def der_cb(self, msg: LaserScan):
        rangos_validos = [r for r in msg.ranges if msg.range_min <= r <= msg.range_max]
        if rangos_validos:
            self.dist_der = min(rangos_validos) * 100.0
        else:
            self.dist_der = 999.0

    # ---------------------------------------------------------------------
    # UTILIDADES
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

    def tiempo_en_esquive(self):
        ahora = self.get_clock().now()
        return (ahora - self.t_esquive_inicio).nanoseconds * 1e-9

    def cambiar_estado(self, nuevo):
        self.estado_rutina = nuevo
        self.t_estado_inicio = self.get_clock().now()

    # ---------------------------------------------------------------------
    # DETECCIÓN DE OBSTÁCULOS
    # ---------------------------------------------------------------------
    def obstaculo_cerca(self) -> bool:
        u = self.UMBRAL_ESQUIVE_CM
        return (self.dist_front < u) or (self.dist_izq < u) or (self.dist_der < u)

    def decidir_direccion_giro(self) -> int:
        u = self.UMBRAL_ESQUIVE_CM
        izq_cerca = self.dist_izq < u
        der_cerca = self.dist_der < u

        if izq_cerca and not der_cerca:
            return +1
        if der_cerca and not izq_cerca:
            return -1
        if self.dist_izq > self.dist_der:
            return -1
        else:
            return +1

    # ---------------------------------------------------------------------
    # CICLO PRINCIPAL DE CONTROL
    # ---------------------------------------------------------------------
    def ciclo_control(self):
        if not self.activo:
            return

        if self.rutina is None:
            self.cmd_pub.publish(Twist())
            return

        if self.esquive_fase != self.ESQ_INACTIVO:
            twist = self.ejecutar_esquive()
            self.cmd_pub.publish(twist)
            return

        if self.obstaculo_cerca():
            self.iniciar_esquive()
            twist = self.ejecutar_esquive()
            self.cmd_pub.publish(twist)
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
    # ESQUIVE
    # ---------------------------------------------------------------------
    def iniciar_esquive(self):
        """Activa el esquive: retrocede y siempre gira a la derecha."""
        self.giro_esquive_dir = +1   # Siempre derecha
        self.esquive_fase = self.ESQ_RETROCESO
        self.t_esquive_inicio = self.get_clock().now()
        self.get_logger().info(
            f'  Esquive: obstaculo detectado (F={self.dist_front:.0f} '
            f'I={self.dist_izq:.0f} D={self.dist_der:.0f}) → '
            f'retroceder + girar DERECHA'
        )

    def ejecutar_esquive(self) -> Twist:
        twist = Twist()
        dt = self.tiempo_en_esquive()

        if self.esquive_fase == self.ESQ_RETROCESO:
            twist.linear.x  = -self.V_RETROCESO
            twist.angular.z = 0.0
            if dt >= self.T_RETROCESO_S:
                self.esquive_fase = self.ESQ_GIRO
                self.t_esquive_inicio = self.get_clock().now()

        elif self.esquive_fase == self.ESQ_GIRO:
            twist.linear.x  = 0.0
            twist.angular.z = self.V_GIRO_ESQUIVE * self.giro_esquive_dir
            if dt >= self.T_GIRO_ESQUIVE_S:
                self.esquive_fase = self.ESQ_INACTIVO
                self.get_logger().info('  Esquive: completado, retomando rutina')

        return twist

    # ---------------------------------------------------------------------
    # RUTINA: ZIGZAG
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
    # RUTINA: CIRCULO
    # ---------------------------------------------------------------------
    def ejecutar_circulo(self) -> Twist:
        twist = Twist()
        twist.linear.x  = self.V_CIRCULO_LIN
        twist.angular.z = self.V_CIRCULO_ANG
        return twist

    # ---------------------------------------------------------------------
    # RUTINA: AUTO (alterna ZIGZAG ↔ CIRCULO)
    # ---------------------------------------------------------------------
    def ejecutar_auto(self) -> Twist:
        ahora = self.get_clock().now()
        dt_auto = (ahora - self.t_auto_inicio).nanoseconds * 1e-9

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
