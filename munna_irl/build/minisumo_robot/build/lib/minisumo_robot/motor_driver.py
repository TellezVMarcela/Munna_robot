#!/usr/bin/env python3
"""
Nodo driver de motores – traduce Twist a PWM para el puente H.
Interfaz serial con ESP32 / Arduino.

Protocolo serial (texto plano):
  Envío al MCU: "L<pwm_izq> R<pwm_der>\n"
  Ejemplo:       "L200 R200\n"   → ambos motores adelante al 78%
                 "L-150 R150\n"  → giro sobre el eje

PWM rango: -255 a 255
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import serial
import serial.tools.list_ports


class MotorDriver(Node):

    def __init__(self):
        super().__init__('motor_driver')

        # ── Parámetros ────────────────────────────────────────────────────────
        self.declare_parameter('serial_port',   '/dev/ttyUSB0')
        self.declare_parameter('baud_rate',     115200)
        self.declare_parameter('wheel_base',    0.10)   # m – ancho entre ruedas
        self.declare_parameter('max_pwm',       255)
        self.declare_parameter('min_pwm',       60)     # PWM mínimo para mover motores
        self.declare_parameter('invert_left',   False)
        self.declare_parameter('invert_right',  False)
        self.declare_parameter('cmd_timeout',   0.5)    # s – apagar si no llegan cmds

        self.port        = self.get_parameter('serial_port').value
        self.baud        = self.get_parameter('baud_rate').value
        self.wheel_base  = self.get_parameter('wheel_base').value
        self.max_pwm     = self.get_parameter('max_pwm').value
        self.min_pwm     = self.get_parameter('min_pwm').value
        self.inv_l       = self.get_parameter('invert_left').value
        self.inv_r       = self.get_parameter('invert_right').value
        self.cmd_timeout = self.get_parameter('cmd_timeout').value

        # ── Serial ────────────────────────────────────────────────────────────
        self.ser = None
        self._open_serial()

        # ── Suscriptor y temporizador watchdog ────────────────────────────────
        self.create_subscription(Twist, '/cmd_vel', self._cmd_cb, 10)
        self._last_cmd_time = self.get_clock().now()
        self.create_timer(0.1, self._watchdog)

        self.get_logger().info(f'✅  Motor driver iniciado – puerto: {self.port}')

    # ─────────────────────────── Serial ──────────────────────────────────────

    def _open_serial(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            self.get_logger().info(f'Puerto serial abierto: {self.port}')
        except serial.SerialException as e:
            self.get_logger().warn(
                f'No se pudo abrir {self.port}: {e}\n'
                f'Puertos disponibles: {[p.device for p in serial.tools.list_ports.comports()]}\n'
                f'Corriendo en modo simulado (sin serial).')

    def _send(self, left_pwm: int, right_pwm: int):
        """Enviar comando al ESP32/Arduino."""
        if self.inv_l:
            left_pwm  = -left_pwm
        if self.inv_r:
            right_pwm = -right_pwm

        # Clamp
        left_pwm  = max(-self.max_pwm, min(self.max_pwm, left_pwm))
        right_pwm = max(-self.max_pwm, min(self.max_pwm, right_pwm))

        cmd = f'L{left_pwm} R{right_pwm}\n'
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(cmd.encode())
            except serial.SerialException as e:
                self.get_logger().error(f'Error serial: {e}')
        else:
            self.get_logger().debug(f'[SIM] {cmd.strip()}')

    # ──────────────────────────── Conversión ──────────────────────────────────

    def _twist_to_pwm(self, twist: Twist):
        """
        Convierte velocidades lineal/angular a PWM por motor.
        Modelo diferencial:
          v_left  = linear - angular * wheel_base/2
          v_right = linear + angular * wheel_base/2
        """
        v_lin = twist.linear.x
        v_ang = twist.angular.z

        v_left  = v_lin - v_ang * (self.wheel_base / 2.0)
        v_right = v_lin + v_ang * (self.wheel_base / 2.0)

        # Normalizar respecto al máximo físico esperado (0.5 m/s → 255 PWM)
        scale   = self.max_pwm / 0.5
        pwm_l   = int(v_left  * scale)
        pwm_r   = int(v_right * scale)

        # Aplicar PWM mínimo si hay movimiento
        def apply_min(pwm):
            if 0 < abs(pwm) < self.min_pwm:
                return self.min_pwm * (1 if pwm > 0 else -1)
            return pwm

        return apply_min(pwm_l), apply_min(pwm_r)

    # ─────────────────────────── Callbacks ───────────────────────────────────

    def _cmd_cb(self, msg: Twist):
        self._last_cmd_time = self.get_clock().now()
        pwm_l, pwm_r = self._twist_to_pwm(msg)
        self._send(pwm_l, pwm_r)

    def _watchdog(self):
        """Detener motores si no llegan comandos en cmd_timeout segundos."""
        elapsed = (self.get_clock().now() - self._last_cmd_time).nanoseconds * 1e-9
        if elapsed > self.cmd_timeout:
            self._send(0, 0)

    def destroy_node(self):
        self._send(0, 0)
        if self.ser and self.ser.is_open:
            self.ser.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MotorDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
