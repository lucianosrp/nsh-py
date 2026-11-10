"""`python -m nsh.reload app.py`: run an app and redraw it on every save.

The same as `nsh.run(..., reload=True)`, without changing the app. See
`nsh._reload` for how it works.
"""

import sys

from nsh._reload import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
