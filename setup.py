from distutils.core import setup
setup(name='LabJackPython',
      version='7-20-2010',
      description='The LabJack python module.',
      url='http://www.labjack.com',
      author='The LabJack crew',
      package_dir = {'': 'src'},
      py_modules=['LabJackPython', 'Modbus', 'u3', 'u6', 'ue9', 'u12', 'skymote']
      )
