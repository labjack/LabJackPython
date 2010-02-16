from distutils.core import setup
setup(name='LabJackPython',
      version='0.8.1',
      description='The LabJack python module.',
      url='http://www.labjack.com',
      author='The LabJack crew',
      py_modules=['LabJackPython', 'Modbus', 'u3', 'u6', 'ue9', 'u12', 'bridge']
      )
