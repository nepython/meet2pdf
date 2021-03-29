import logging
import sys

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/home/hardik/meet2pdf/')

from main import app as application
application.secret_key = 'dx2d2wd@*@(dxnxq!(!ndnvw@#n9*#(w@*@ndx*@ncqa'
