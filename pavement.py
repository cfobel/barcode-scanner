import platform
import sys

from paver.easy import task, needs, path, sh, cmdopts, options
from paver.setuputils import setup, install_distutils_tasks
from distutils.extension import Extension
from distutils.dep_util import newer

sys.path.insert(0, path('.').abspath())
import version

install_requires = ['matplotlib>=1.5.0', 'numpy', 'pygst-utils>=0.3.post4',
                    'zbar']

# Platform-specific package requirements.
if platform.system() == 'Windows':
    install_requires += ['opencv-python', 'pygtk2-win', 'pycairo-gtk2-win',
                         'pygst-0.10-win']
else:
    try:
        import gtk
    except ImportError:
        print >> sys.err, ('Please install Python bindings for Gtk 2 using '
                           'your systems package manager.')
    try:
        import cv2
    except ImportError:
        print >> sys.err, ('Please install OpenCV Python bindings using your '
                           'systems package manager.')
    try:
        import gst
    except ImportError:
        print >> sys.err, ('Please install GStreamer Python bindings using '
                           'your systems package manager.')

setup(name='barcode-scanner',
      version=version.getVersion(),
      description='Barcode scanner based on GStreamer, zbar, and gtk.',
      keywords='gtk, zbar, gstreamer',
      author='Christian Fobel and Michael D. M. Dryden',
      author_email='christian@fobel.net and mdryden@chem.utoronto.ca',
      url='https://github.com/wheeler-microfluidics/barcode-scanner',
      license='GPL',
      packages=['barcode_scanner', ],
      install_requires=install_requires,
      # Install data listed in `MANIFEST.in`
      include_package_data=True)


@task
@needs('generate_setup', 'minilib', 'setuptools.command.sdist')
def sdist():
    """Overrides sdist to make sure that our setup.py is generated."""
    pass
