from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'minisumo_robot'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='Jorge González & Marcela Téllez',
    maintainer_email='jorge_ern.gonzalez@uao.edu.co',
    description='Robot minisumo ROS2 – autónomo y teleoperado',
    license='MIT',
    entry_points={
        'console_scripts': [
            'autonomous_node=minisumo_robot.autonomous_node:main',
            'teleop_node=minisumo_robot.teleop_node:main',
            'mode_manager=minisumo_robot.mode_manager:main',
            'motor_driver=minisumo_robot.motor_driver:main',
            'sensor_node=minisumo_robot.sensor_node:main',
        ],
    },
)
