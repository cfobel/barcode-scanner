import sys

from paver.easy import task, needs, path, sh, cmdopts, options
from paver.setuputils import setup, install_distutils_tasks
from distutils.extension import Extension
from distutils.dep_util import newer

sys.path.insert(0, path('.').abspath())
import version

setup(name='barcode-scanner',
      version=version.getVersion(),
      description='Barcode scanner based on GStreamer, zbar, and gtk.',
      keywords='gtk, zbar, gstreamer',
      author='Christian Fobel and Michael D. M. Dryden',
      author_email='christian@fobel.net and mdryden@chem.utoronto.ca',
      url='https://github.com/wheeler-microfluidics/barcode-scanner',
      license='GPL',
      packages=['barcode_scanner', ],
      install_requires=[],
      # Install data listed in `MANIFEST.in`
      include_package_data=True)


@task
@needs('generate_setup', 'minilib', 'setuptools.command.sdist')
def sdist():
    """Overrides sdist to make sure that our setup.py is generated."""
    pass
