#!/usr/bin/env python3

import math
import rclpy
from rclpy.node import Node

from geometry_msgs.msg import TransformStamped
from turtlesim.msg import Pose
import tf2_ros


class TurtleTF2Broadcaster(Node):

    def __init__(self):
        super().__init__('turtles_tf2_broadcaster')

        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # Suscripción a turtle1
        self.subscription1 = self.create_subscription(
            Pose,
            '/turtle1/pose',
            lambda msg: self.handle_turtle_pose(msg, 'turtle1'),
            10)

        # Suscripción a turtle2
        self.subscription2 = self.create_subscription(
            Pose,
            '/turtle2/pose',
            lambda msg: self.handle_turtle_pose(msg, 'turtle2'),
            10)

    def handle_turtle_pose(self, msg, turtle_name):

        t = TransformStamped()

        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'world'
        t.child_frame_id = turtle_name

        t.transform.translation.x = msg.x
        t.transform.translation.y = msg.y
        t.transform.translation.z = 0.0

        q = self.quaternion_from_euler(0, 0, msg.theta)
        t.transform.rotation.x = q[0]
        t.transform.rotation.y = q[1]
        t.transform.rotation.z = q[2]
        t.transform.rotation.w = q[3]

        self.tf_broadcaster.sendTransform(t)

    def quaternion_from_euler(self, roll, pitch, yaw):
        qx = math.sin(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) - \
             math.cos(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        qy = math.cos(roll/2) * math.sin(pitch/2) * math.cos(yaw/2) + \
             math.sin(roll/2) * math.cos(pitch/2) * math.sin(yaw/2)
        qz = math.cos(roll/2) * math.cos(pitch/2) * math.sin(yaw/2) - \
             math.sin(roll/2) * math.sin(pitch/2) * math.cos(yaw/2)
        qw = math.cos(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) + \
             math.sin(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        return [qx, qy, qz, qw]


def main(args=None):
    rclpy.init(args=args)
    node = TurtleTF2Broadcaster()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()