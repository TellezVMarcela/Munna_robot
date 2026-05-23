#!/usr/bin/env python3
"""
Munna – Nodo autónomo
=====================
GRAFCET N2:
  E0 Idle      → sin obstáculo → ejecuta rutina activa
  E1 Cuadrado  → avanza lado → gira 90° → repite 4 veces
  E2 Círculo   → giro continuo hasta completar 360°
  E3 Esquivar  → IR detecta obstáculo → gira → regresa a rutina

Selección de rutina (desde /rutina topic o botones PS4):
  'auto'     → alterna cuadrado/círculo cada T segundos
  'cuadrado' → fija cuadrado
  'circulo'  → fija círculo

Tópicos:
  SUB  /sensors/ir   Float32MultiArray [izq, der]
  SUB  /rutina       String  ('auto' | 'cuadrado' | 'circulo')
  PUB  /autonomous/cmd_vel  Twist
"""

import rclpy, math, time
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray, String


class MunnaAutonomo(Node):

    # ── Parámetros ajustables ─────────────────────────────────
    LADO_M        = 0.5    # m  – lado del cuadrado
    VEL_LIN       = 0.2    # m/s
    VEL_ANG       = 0.8    # rad/s
    T_LADO        = None   # se calcula: LADO_M / VEL_LIN
    T_GIRO_90     = None   # se calcula: (π/2) / VEL_ANG
    T_GIRO_360    = None   # se calcula: (2π)  / VEL_ANG
    T_AUTO        = 10.0   # s entre cambios de rutina en modo AUTO
    T_ESQUIVAR    = 0.5    # s girando al esquivar
    IR_THRESH     = 0.5    # umbral detección IR

    def __init__(self):
        super().__init__('munna_autonomo')

        # Parámetros ROS2 (ajustables sin recompilar)
        self.declare_parameter('lado_m',     self.LADO_M)
        self.declare_parameter('vel_lin',    self.VEL_LIN)
        self.declare_parameter('vel_ang',    self.VEL_ANG)
        self.declare_parameter('t_auto',     self.T_AUTO)
        self.declare_parameter('t_esquivar', self.T_ESQUIVAR)

        self.lado    = self.get_parameter('lado_m').value
        self.v_lin   = self.get_parameter('vel_lin').value
        self.v_ang   = self.get_parameter('vel_ang').value
        self.t_auto  = self.get_parameter('t_auto').value
        self.t_esq   = self.get_parameter('t_esquivar').value

        # Tiempos calculados
        self.T_LADO     = self.lado / self.v_lin
        self.T_GIRO_90  = (math.pi / 2) / self.v_ang
        self.T_GIRO_360 = (2 * math.pi) / self.v_ang

        # Estado GRAFCET
        self.estado      = 'IDLE'
        self.rutina      = 'auto'       # 'auto' | 'cuadrado' | 'circulo'
        self.rutina_act  = 'cuadrado'   # rutina activa en modo AUTO
        self.fase        = 0            # fase dentro de la rutina
        self.t_fase      = time.time()  # timestamp inicio fase
        self.t_rutina    = time.time()  # timestamp para alternar en AUTO
        self.estado_prev = 'IDLE'       # estado antes de esquivar
        self.ir          = [0.0, 0.0]

        # Pub / Sub
        self.pub = self.create_publisher(Twist, '/autonomous/cmd_vel', 10)
        self.create_subscription(Float32MultiArray, '/sensors/ir',  self._ir_cb,     10)
        self.create_subscription(String,            '/rutina',       self._rutina_cb, 10)

        self.create_timer(0.05, self._loop)  # 20 Hz
        self.get_logger().info('✅ Munna autónomo iniciado')

    # ── Callbacks ─────────────────────────────────────────────
    def _ir_cb(self, msg):
        if len(msg.data) >= 2:
            self.ir = list(msg.data[:2])

    def _rutina_cb(self, msg):
        self.rutina = msg.data.lower().strip()
        self.get_logger().info(f'Rutina: {self.rutina}')
        self._reset_rutina()

    # ── Loop principal (GRAFCET) ───────────────────────────────
    def _loop(self):
        twist = Twist()
        obstaculo = any(v > self.IR_THRESH for v in self.ir)

        # ── E3: ESQUIVAR (prioridad máxima) ───────────────────
        if self.estado == 'ESQUIVAR':
            twist.angular.z = self.v_ang
            if time.time() - self.t_fase >= self.t_esq:
                self.estado = self.estado_prev  # regresa a rutina
                self._reset_fase()
            self.pub.publish(twist)
            return

        # Detectar obstáculo desde cualquier estado
        if obstaculo:
            self.estado_prev = self.estado
            self.estado      = 'ESQUIVAR'
            self.t_fase      = time.time()
            self.pub.publish(twist)
            return

        # ── Selección de rutina activa ─────────────────────────
        if self.rutina == 'auto':
            if time.time() - self.t_rutina >= self.t_auto:
                self.t_rutina   = time.time()
                self.rutina_act = 'circulo' if self.rutina_act == 'cuadrado' else 'cuadrado'
                self.get_logger().info(f'AUTO → cambia a {self.rutina_act}')
                self._reset_fase()
            rutina = self.rutina_act
        else:
            rutina = self.rutina

        # ── E1: CUADRADO ──────────────────────────────────────
        if rutina == 'cuadrado':
            self.estado = 'CUADRADO'
            twist = self._rutina_cuadrado()

        # ── E2: CÍRCULO ───────────────────────────────────────
        elif rutina == 'circulo':
            self.estado = 'CIRCULO'
            twist = self._rutina_circulo()

        self.pub.publish(twist)

    # ── Rutina cuadrado ───────────────────────────────────────
    # fase 0,2,4,6 → avanzar lado
    # fase 1,3,5,7 → girar 90°
    # fase 8       → completó cuadrado → reinicia
    def _rutina_cuadrado(self):
        twist  = Twist()
        elapsed = time.time() - self.t_fase

        if self.fase % 2 == 0:          # avanzar
            twist.linear.x = self.v_lin
            if elapsed >= self.T_LADO:
                self._next_fase()
        else:                            # girar 90°
            twist.angular.z = self.v_ang
            if elapsed >= self.T_GIRO_90:
                self._next_fase()
                if self.fase >= 8:      # completó 4 lados
                    self._reset_fase()

        return twist

    # ── Rutina círculo ────────────────────────────────────────
    # Avanza con giro constante hasta completar 360°, luego reinicia
    def _rutina_circulo(self):
        twist = Twist()
        twist.linear.x  = self.v_lin
        twist.angular.z = self.v_ang

        if time.time() - self.t_fase >= self.T_GIRO_360:
            self._reset_fase()

        return twist

    # ── Helpers ───────────────────────────────────────────────
    def _next_fase(self):
        self.fase  += 1
        self.t_fase = time.time()

    def _reset_fase(self):
        self.fase   = 0
        self.t_fase = time.time()

    def _reset_rutina(self):
        self._reset_fase()
        self.t_rutina = time.time()


def main(args=None):
    rclpy.init(args=args)
    node = MunnaAutonomo()
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
