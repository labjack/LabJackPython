import sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.version_info[:2] < (2, 6):
    msg = ("LabJackPython requires Python 2.6 or later. "
           "You are using version %s.  Please "
           "install using a supported version." % sys.version)
    sys.stderr.write(msg)
    sys.exit(1)

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: MacOS :: MacOS X',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Topic :: Software Development',
    'Topic :: Software Development :: Embedded Systems',
    'Topic :: System :: Hardware'
    ]

setup(name='LabJackPython',
      version='5-26-2015',
      description='The LabJack Python modules for the LabJack U3, U6, UE9 and U12.',
      license='MIT X11',
      url='http://labjack.com/support/labjackpython',
      author='LabJack Corporation',
      author_email='support@labjack.com',
      maintainer='LabJack Corporation',
      maintainer_email='support@labjack.com',
      classifiers=CLASSIFIERS,
      package_dir = {'': 'src'},
      py_modules=['LabJackPython', 'Modbus', 'u3', 'u6', 'ue9', 'u12']
      )
