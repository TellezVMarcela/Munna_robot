#!/usr/bin/env python3
"""
Nodo de control autónomo para robot minisumo.
Estrategia: buscar oponente con sensores IR frontales y de borde (cliff).
             Atacar en línea recta cuando detecta oponente.
             Girar para buscar si no hay oponente.
             Retroceder si está en el borde del dohyo.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32MultiArray, String
from geometry_msgs.msg import Twist
import math
import time


class AutonomousController(Node):
    """
    Controlador autónomo para competencia de minisumo.

    Sensores esperados:
      - /sensors/opponent   : Float32MultiArray [izq, centro, der]  (distancia en metros)
      - /sensors/edge       : Float32MultiArray [izq_frente, der_frente, izq_atras, der_atras]
                              (True/1.0 = borde detectado)
    Comandos de salida:
      - /cmd_vel            : Twist (velocidades lineales y angulares)
    """

    # ─── Umbrales (ajustar según el hardware) ───────────────────────────────
    OPPONENT_DETECT_DIST  = 0.30   # m – distancia para considerar que ve oponente
    EDGE_THRESHOLD        = 0.5    # valor mayor a éste indica borde

    # ─── Velocidades ────────────────────────────────────────────────────────
    ATTACK_LINEAR         = 0.5    # m/s  hacia adelante al atacar
    SEARCH_ANGULAR        = 1.2    # rad/s al girar buscando
    REVERSE_LINEAR        = -0.35  # m/s  al retroceder del borde
    REVERSE_DURATION      = 0.4    # s    tiempo retrocediendo
    DODGE_DURATION        = 0.3    # s    tiempo girando tras retroceder

    def __init__(self):
        super().__init__('autonomous_controller')

        # ── Parámetros configurables ─────────────────────────────────────────
        self.declare_parameter('attack_speed',   self.ATTACK_LINEAR)
        self.declare_parameter('search_speed',   self.SEARCH_ANGULAR)
        self.declare_parameter('reverse_speed',  abs(self.REVERSE_LINEAR))
        self.declare_parameter('detect_dist',    self.OPPONENT_DETECT_DIST)

        self.attack_speed  = self.get_parameter('attack_speed').value
        self.search_speed  = self.get_parameter('search_speed').value
        self.reverse_speed = self.get_parameter('reverse_speed').value
        self.detect_dist   = self.get_parameter('detect_dist').value

        # ── Estado interno ────────────────────────────────────────────────────
        self.opponent_data  = [999.0, 999.0, 999.0]  # izq, centro, der
        self.edge_data      = [0.0, 0.0, 0.0, 0.0]   # FL, FR, BL, BR
        self.state          = 'SEARCH'
        self.state_timer    = 0.0
        self.search_dir     = 1.0  # +1 gira izquierda, -1 gira derecha

        # ── Publicadores y suscriptores ───────────────────────────────────────
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.state_pub = self.create_publisher(String, '/autonomous/state', 10)

        self.create_subscription(
            Float32MultiArray, '/sensors/opponent', self._opponent_cb, 10)
        self.create_subscription(
            Float32MultiArray, '/sensors/edge', self._edge_cb, 10)

        # ── Temporizador de control a 20 Hz ──────────────────────────────────
        self.dt = 0.05
        self.create_timer(self.dt, self._control_loop)

        self.get_logger().info('✅  Nodo autónomo iniciado – estado: SEARCH')

    # ────────────────────────────── Callbacks ────────────────────────────────

    def _opponent_cb(self, msg: Float32MultiArray):
        if len(msg.data) >= 3:
            self.opponent_data = list(msg.data[:3])

    def _edge_cb(self, msg: Float32MultiArray):
        if len(msg.data) >= 4:
            self.edge_data = list(msg.data[:4])

    # ──────────────────────────── Lógica principal ───────────────────────────

    def _control_loop(self):
        twist = Twist()
        edge_front = (self.edge_data[0] > self.EDGE_THRESHOLD or
                      self.edge_data[1] > self.EDGE_THRESHOLD)
        edge_back  = (self.edge_data[2] > self.EDGE_THRESHOLD or
                      self.edge_data[3] > self.EDGE_THRESHOLD)

        opp_left   = self.opponent_data[0]
        opp_center = self.opponent_data[1]
        opp_right  = self.opponent_data[2]
        sees_opp   = min(opp_left, opp_center, opp_right) < self.detect_dist

        # ── Máquina de estados ────────────────────────────────────────────────
        if self.state == 'REVERSE':
            # Retroceder del borde
            self.state_timer -= self.dt
            twist.linear.x = -self.reverse_speed
            if self.state_timer <= 0:
                self.state = 'DODGE'
                self.state_timer = self.DODGE_DURATION
                # Girar hacia el lado contrario al borde detectado
                if self.edge_data[0] > self.EDGE_THRESHOLD:
                    self.search_dir = -1.0  # gira derecha
                else:
                    self.search_dir = 1.0

        elif self.state == 'DODGE':
            # Girar para alejarse del borde
            self.state_timer -= self.dt
            twist.angular.z = self.search_dir * self.search_speed
            if self.state_timer <= 0:
                self.state = 'SEARCH'

        elif edge_front:
            # Prioridad máxima: salirse del borde
            self.get_logger().warn('⚠️  Borde frontal – retrocediendo')
            self.state = 'REVERSE'
            self.state_timer = self.REVERSE_DURATION

        elif edge_back:
            # Borde trasero: avanzar
            twist.linear.x = self.attack_speed * 0.5
            self.state = 'SEARCH'

        elif self.state == 'ATTACK':
            if not sees_opp:
                self.state = 'SEARCH'
            else:
                # Dirigir hacia el oponente
                if opp_center < self.detect_dist:
                    twist.linear.x = self.attack_speed
                elif opp_left < opp_right:
                    twist.linear.x  = self.attack_speed * 0.6
                    twist.angular.z = self.search_speed * 0.5   # gira izquierda
                else:
                    twist.linear.x  = self.attack_speed * 0.6
                    twist.angular.z = -self.search_speed * 0.5  # gira derecha

        elif self.state == 'SEARCH':
            if sees_opp:
                self.state = 'ATTACK'
            else:
                # Girar en espiral para buscar oponente
                twist.angular.z = self.search_dir * self.search_speed
                twist.linear.x  = 0.05  # ligero avance para variar posición

        # ── Publicar ──────────────────────────────────────────────────────────
        self.cmd_pub.publish(twist)
        state_msg = String()
        state_msg.data = self.state
        self.state_pub.publish(state_msg)


def main(args=None):
    rclpy.init(args=args)
    node = AutonomousController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        stop = Twist()
        node.cmd_pub.publish(stop)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
