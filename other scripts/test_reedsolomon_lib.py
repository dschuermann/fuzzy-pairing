# -*- coding: utf-8 -*-
"""Test for the library reedsolomon-0.1

    :platform: Linux
    :synopsis: Test for the library reedsolomon-0.1

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""

from reedsolomon import Codec

# using Codec
# its also possible to use IntegerCodec
# to operate on integer-arrays instead of strings
c = Codec(7, 5)

# encoding of string
encoded = c.encode('abcde')
print str(encoded)

# normal recovery without errors
d1 = c.decode('abcde\x94m')
print d1

# recovery with one error Z
d2 = c.decode('aZcde\x94m')
print d2