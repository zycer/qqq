#!/usr/bin/env python3

import sys

from qcaudit_cd6h.main import main

try:
    sys.exit(main())
except KeyboardInterrupt:
    pass