from setuptools import find_packages, setup

package_name = 'learning_tf2'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='fairytale',
    maintainer_email='fairytale@todo.todo',
    description='Learning TF2 tutorial package',
    license='Apache License 2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'turtle_tf2_listener = learning_tf2.turtle_tf2_listener:main',
            'turtle_tf2_broadcaster = learning_tf2.turtle_tf2_broadcaster:main',
        ],
    },
)
