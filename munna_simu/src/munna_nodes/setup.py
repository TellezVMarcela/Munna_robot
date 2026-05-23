from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'munna_nodes'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='fairytale',
    maintainer_email='fairytale@todo.todo',
    description='Nodos de control de Munna para simulacion en Gazebo (teleop, autonomo, mode_manager)',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'teleop_node     = munna_nodes.teleop_node:main',
            'mode_manager    = munna_nodes.mode_manager:main',
            'autonomous_node = munna_nodes.autonomous_node:main',
        ],
    },
)
