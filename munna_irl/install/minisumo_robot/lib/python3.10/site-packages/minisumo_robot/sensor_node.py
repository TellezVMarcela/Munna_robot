#!/usr/bin/env python3
"""
Nodo de sensores para minisumo.
Lee sensores infrarrojos de oponente y de borde (cliff) desde ESP32/Arduino.

Protocolo serial de entrada (del MCU):
  "OPP:<izq>,<centro>,<der> EDGE:<FL>,<FR>,<BL>,<BR>\n"
  Ejemplo: "OPP:0.45,0.12,0.80 EDGE:0,0,0,0\n"

Publicación:
  /sensors/opponent  Float32MultiArray  [izq, centro, der]  metros
  /sensors/edge      Float32MultiArray  [FL, FR, BL, BR]    0=ok, 1=borde
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
import serial
import time
import re


# Valores simulados cuando no hay puerto serial disponible
_SIM_OPP   = [1.0, 1.0, 1.0]
_SIM_EDGE  = [0.0, 0.0, 0.0, 0.0]


class SensorNode(Node):

    def __init__(self):
        super().__init__('sensor_node')

        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate',   115200)
        self.declare_parameter('sim_mode',    False)

        self.port     = self.get_parameter('serial_port').value
        self.baud     = self.get_parameter('baud_rate').value
        self.sim_mode = self.get_parameter('sim_mode').value

        # ── Publicadores ──────────────────────────────────────────────────────
        self.opp_pub  = self.create_publisher(Float32MultiArray, '/sensors/opponent', 10)
        self.edge_pub = self.create_publisher(Float32MultiArray, '/sensors/edge',     10)

        # ── Serial ────────────────────────────────────────────────────────────
        self.ser = None
        if not self.sim_mode:
            self._open_serial()

        self.create_timer(0.05, self._read_sensors)  # 20 Hz
        self.get_logger().info(
            '✅  Sensor node iniciado' +
            (' [MODO SIMULADO]' if self.sim_mode or not self.ser else ''))

    def _open_serial(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.05)
        except serial.SerialException as e:
            self.get_logger().warn(f'Serial no disponible: {e} – usando simulación')

    def _read_sensors(self):
        if self.ser and self.ser.is_open:
            self._read_from_serial()
        else:
            self._publish_simulated()

    def _read_from_serial(self):
        try:
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                return
            opp, edge = self._parse_line(line)
            if opp is not None:
                self._publish(opp, edge)
        except Exception as e:
            self.get_logger().debug(f'Error leyendo serial: {e}')

    @staticmethod
    def _parse_line(line: str):
        """
        Parsea "OPP:0.45,0.12,0.80 EDGE:0,0,0,0"
        Retorna (opp_list, edge_list) o (None, None) si falla.
        """
        opp_match  = re.search(r'OPP:([\d.,]+)', line)
        edge_match = re.search(r'EDGE:([\d.,]+)', line)
        if not opp_match or not edge_match:
            return None, None
        try:
            opp  = [float(x) for x in opp_match.group(1).split(',')]
            edge = [float(x) for x in edge_match.group(1).split(',')]
            if len(opp) >= 3 and len(edge) >= 4:
                return opp[:3], edge[:4]
        except ValueError:
            pass
        return None, None

    def _publish_simulated(self):
        """Publica datos simulados (sin oponente, sin borde)."""
        self._publish(_SIM_OPP, _SIM_EDGE)

    def _publish(self, opp, edge):
        opp_msg       = Float32MultiArray()
        opp_msg.data  = opp
        edge_msg      = Float32MultiArray()
        edge_msg.data = edge
        self.opp_pub.publish(opp_msg)
        self.edge_pub.publish(edge_msg)

    def destroy_node(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SensorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
