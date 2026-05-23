from setuptools import setup
import os
from glob import glob

package_name = 'munna_robot'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jorge Gonzalez',
    maintainer_email='jorge_ern.gonzalez@uao.edu.co',
    description='Robot Munna ROS2',
    license='MIT',
    entry_points={
        'console_scripts': [
            'munna_autonomo=munna_robot.munna_autonomo:main',
            'munna_teleop=munna_robot.munna_teleop:main',
            'munna_mode_manager=munna_robot.munna_mode_manager:main',
        ],
    },
)
