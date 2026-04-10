import mimetypes
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

import sys
from streamlit.web import cli

if __name__ == '__main__':
    sys.argv = ["streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8505"]
    sys.exit(cli.main())
