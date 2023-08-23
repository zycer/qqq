#!/usr/bin/env python3

import sys

from qcaudit.main import main

try:
    sys.exit(main())
except KeyboardInterrupt:
    pass
