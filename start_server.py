import argparse
import codecs
import http.server
import os
import re
import socketserver
import sys
from configparser import NoOptionError, NoSectionError, RawConfigParser
from shutil import copytree, rmtree
from threading import Thread
from urllib.parse import urlparse, parse_qs

from run_geolocation_engine import calc_dev_locations

SEC_HTML_VARIABLES  = 'HTML Variables'   # Section for general configurations
GOOGLE_API_KEY      = 'GOOGLE_API_KEY'   # Google API Key used for Google Maps


class Handler(http.server.SimpleHTTPRequestHandler):

    # Override the do_GET function
    def do_GET(self):
        print('requestline', self.requestline)
        print('path', self.path)
        req = urlparse(self.path)

        if req.path == '/geolocate':
            req_query = parse_qs(req.query)
            if 'eui' in req_query:
                eui = parse_qs(req.query)['eui'][0].strip()
                print('EUI: ' + eui)
                match = re.match('[0-9A-Fa-f]{16}', eui)
                if match:
                    print('Match!')
                    self._geolocate_dev(eui=eui)
                    self._set_headers(200)
                    msg = '{"msg": "Calculating geolocation for device ' + eui + '"}'
                    self.wfile.write(msg.encode())
                else:
                    self.send_error(404, explain='{"msg": "Invalid eui"}')
            else:
                self.send_error(404, explain='{"msg": "Missing param: eui"}')

        else:
            super(Handler, self).do_GET()

    def _set_headers(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    @staticmethod
    def _geolocate_dev(eui):
        print('Starting new thread...')
        thread1 = Thread(target=calc_dev_locations, kwargs={'db_file': '../jan_18_data.db', 'device_eui': eui})
        thread1.start()
        print('Geolocating EUI: ' + eui)


##########################################################################
# Replace all variables in files
#
###########################################################################
def deploy(build_dir, config):
    """
    Loads the config file and check that it contains the required fields
    :param build_dir: Build directory
    :param config: App configuration
    """

    if os.path.exists(build_dir):
        rmtree(build_dir)

    copytree('webapp', build_dir)

    replacements = dict()
    replace_vars = config.items(SEC_HTML_VARIABLES)
    for key_val in replace_vars:
        replacements[str.upper(key_val[0])] = key_val[1]

    for dir_path, dir_names, file_names in os.walk(build_dir):
        for file_name in [f for f in file_names if f.endswith('.html')]:
            lines = list()
            file_loc = os.path.join(dir_path, file_name)
            with codecs.open(file_loc, 'r', encoding='utf-8') as in_file:
                for line in in_file:
                    for src, target in replacements.items():
                        line = line.replace('%' + src + '%', target)
                    lines.append(line)

            with codecs.open(file_loc, 'w', encoding='utf-8') as out_file:
                for line in lines:
                    out_file.write(line)


##########################################################################
# Get and validate config file
#
###########################################################################
def get_config_file(config_file_name):
    """
    Loads the config file and check that it contains the required fields
    :param config_file_name: Name of the config file
    :return: The config file if valid
    """

    config = RawConfigParser()

    valid_file = False
    try:
        config.read(config_file_name)
        valid_file = True
    except Exception as e:
        print('Exception: ' + str(e))
        print('Unable to read config file: ' + config_file_name)
        config = None

    if valid_file:
        try:
            if not config.get(SEC_HTML_VARIABLES, GOOGLE_API_KEY, fallback=None):
                print('Missing ' + GOOGLE_API_KEY + ' value in config')
                config = None
        except NoSectionError or NoOptionError:
            print('Invalid config file: ' + config_file_name)
            config = None

    return config


###############################################################################
# parseArgs
#    -Parse arguments and provide help, port, etc
###############################################################################
def parse_args():
    desc = "Start server to view geolocation data on a map."

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=desc)

    parser.add_argument('-b', '--build', action='store_true', default=True,
                        help="Build the app")

    parser.add_argument('-p', '--port', default=8000,
                        help="Server port")

    return parser.parse_args()


###############################################################################
# main()
#
###############################################################################
def main():
    args = parse_args()
    config = get_config_file(config_file_name='app.cfg')

    if config:
        # Build and start
        build_dir = 'build'
        deploy(build_dir=build_dir, config=config)

        web_dir = os.path.join(os.path.dirname(__file__), build_dir)
        os.chdir(web_dir)

        port = int(args.port)
        httpd = socketserver.TCPServer(('', port), Handler)

        print("Serving at port:", port)
        httpd.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
