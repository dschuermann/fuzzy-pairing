
"""Reed-Solomon error correction library

Reed-Solomon coding adds efficient, tunable redundancy to transmitted
or stored data.  This Python extension module provides a simple Python
interface to Phil Karn's fast Reed-Solomon library.  Since the library
itself is small, it is compiled into the extension.
"""

classifiers = """\
Development Status :: 3 - Alpha
Intended Audience :: Developers
License :: OSI Approved :: GNU General Public License (GPL)
Programming Language :: Python
Topic :: Communications :: File Sharing
Topic :: System :: Archiving :: Backup
Topic :: Software Development :: Libraries :: Python Modules
Operating System :: Unix
"""

# If you're using GCC, before running setup.py, set compiler
# optimization flags in the environment.  -O2 doubles the speed
# and processor-specific optimization can add another 20%.
# For GCC with Athlon XP:
#   CFLAGS='-O2 -march=athlon-xp -Wall'; export CFLAGS
# For GCC with other chips:
#   CFLAGS='-O2 -march=i686 -Wall'; export CFLAGS

import os
from distutils.core import setup, Extension

lib = os.path.join('librs', '')

e = Extension(
    'reedsolomon',
    sources=[
    'reedsolomon.c',
    lib + 'encode_rs.c',
    lib + 'encode_rs_int.c',
    lib + 'encode_rs_8.c',
    lib + 'encode_rs_ccsds.c',
    lib + 'decode_rs.c',
    lib + 'decode_rs_int.c',
    lib + 'decode_rs_8.c',
    lib + 'decode_rs_ccsds.c',
    lib + 'init_rs.c',
    lib + 'init_rs_int.c',
    lib + 'ccsds_tab.c',
    lib + 'ccsds_tal.c',
    ],
    include_dirs=[lib],
    )

doclines = __doc__.split("\n")

setup (
    name="reedsolomon",
    version='0.1',
    maintainer="Shane Hathaway",
    maintainer_email="shane@hathawaymix.org",
    url="http://hathawaymix.org/Software/ReedSolomon",
    license="http://www.gnu.org/copyleft/gpl.html",
    platforms=["any"],
    description=doclines[0],
    classifiers=filter(None, classifiers.split("\n")),
    long_description = "\n".join(doclines[2:]),
    ext_modules=[e],
    )
