
from setuptools import find_packages, setup
from glob import glob

package_name = 'munna_teleop'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='marcela',
    maintainer_email='[email protected]',
    description='Teleop de Munna con PS3',
    license='Apache-2.0',
    entry_points={
    'console_scripts': [
        'teleop_node = munna_teleop.teleop_node:main',
        'mode_manager = munna_teleop.mode_manager:main',
        'autonomous_node = munna_teleop.autonomous_node:main',
    ],
},
)
