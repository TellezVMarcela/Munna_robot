# Munna 🐾

**Plataforma robótica móvil de operación dual para la estimulación física y cognitiva de pequeños animales sociales (gatos y hurones).**

Munna es un robot móvil de bajo costo y código abierto diseñado como herramienta de enriquecimiento ambiental doméstico. Combina teleoperación con joystick PS3 y rutinas autónomas reactivas dentro de un entorno delimitado, buscando mitigar el sedentarismo y la habituación característicos de los juguetes interactivos convencionales.

---

## ✨ Características

- **Operación dual** — modo MANUAL (joystick PS3) y modo AUTO con tres rutinas: `zigzag`, `círculo` y `AUTO` (alternancia automática).
- **Evasión reactiva** — maniobra de cuatro fases ante obstáculos detectados por los tres sensores ultrasónicos.
- **Arquitectura ROS 2 + micro-ROS** — capa de aplicación en PC, firmware embebido en ESP32, comunicación inalámbrica por Wi-Fi (UDP).
- **Doble configuración** — software funcionalmente equivalente para el prototipo físico y para simulación en Gazebo Classic.

---

## 🔧 Hardware

| Componente | Descripción |
|---|---|
| Microcontrolador | ESP32 |
| Driver de motores | TB6612FNG |
| Motores | 2× motorreductor N20 6 V 300 RPM |
| Sensores | 3× HC-SR04 (frontal, izquierdo +30°, derecho −30°) |
| Batería | 2× 18650 Li-ion (2S, 7,4 V nominal) |
| Gestión de batería | BMS HX-2S-D20 |
| Regulador | Buck DC-DC MP1584 (5 V) |
| Chasis | Impresión 3D en PETG |

---

## 🧠 Software

| Componente | Tecnología |
|---|---|
| Sistema operativo | Ubuntu 22.04 |
| Middleware | ROS 2 Humble |
| Firmware embebido | micro-ROS sobre Arduino-ESP32 |
| Simulación | Gazebo Classic + RViz 2 |
| Lectura del joystick | Paquete `joy` de ROS 2 |

### Nodos principales

- `teleop_node` — traduce eventos del joystick a `/cmd_vel`.
- `autonomous_node` — genera trayectorias geométricas y maneja la lógica de evasión.
- `mode_manager` — arbitra qué productor controla `/cmd_vel` (MANUAL/AUTO).
- Nodo embebido en ESP32 — suscribe a `/cmd_vel`, publica lecturas filtradas de los HC-SR04.

---

## 🚀 Uso rápido

### Robot físico

```bash
# 1. Iniciar el agente micro-ROS
ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888

# 2. Encender el ESP32 con su firmware cargado

# 3. Lanzar los nodos del PC
ros2 launch munna_bringup munna_teleop.launch.py
```

### Simulación

```bash
#Rviz2
ros2 launch munna_bringup display.launch.py

#Gazebo
ros2 launch munna_bringup munna_full.launch.py 
```

---

## 📄 Cita

Si utilizas este trabajo, por favor cítalo como:

> Tellez Villegas, M. (2026). *Munna: Desarrollo de una plataforma robótica móvil de operación dual para la estimulación física y cognitiva de pequeños animales sociales (gatos y hurones)*.

---

## 📜 Licencia

Este proyecto se distribuye bajo la Licencia **Creative Commons Atribución-NoComercial-CompartirIgual 4.0 Internacional (CC BY-NC-SA 4.0)**.

---

## 👤 Autor

**Marcela Tellez Villegas**
Programa de Ingeniería Mecatrónica — Universidad Autónoma de Occidente (Cali, Colombia)
📧 marcela.tellez@uao.edu.co
