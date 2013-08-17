#!/usr/bin/env python2

import sys
import os
import socket
import threading
import traceback

import paramiko


paramiko.util.log_to_file(os.path.expanduser('~/honeyfeast_server.log'))

host_key = paramiko.RSAKey.from_private_key(open('feast.key'))

def log(msg):
    print msg
    with open(os.path.expanduser('~/honeyfeastlog.txt'), 'a+') as logfile:
        logfile.write(msg + '\n')

class Server (paramiko.ServerInterface):
    def __init__(self):
        self.username = 'root'
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        self.username = username
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        self.username = username
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        self.username = username
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth,
                                  pixelheight, modes):
        return True

num_loc_warnings = 0

def process_command(command):
    args = command.split(' ')
    if args[0] == 'ls':
        return """84000.txt~
names.txt
Documents
Downloads
Music
Videos
"""
    elif args[0] == 'cd':
        return '/'.join(args[1:])
    elif args[0] == 'uname':
        return 'Linux waffle x86_64 SMP'
    elif args[0] == 'exit':
        global num_loc_warnings
        num_loc_warnings += 1
        if num_loc_warnings > 1:
            return 'Location acquired. Say "please" to exit.'
        return 'Still acquiring your location... Please wait.'
    elif args[0] == 'please':
        return 'Until next time!'
    else:
        return 'Unknown command'

def run_ssh_server(client):
    t = paramiko.Transport(client)
    try:
        t.load_server_moduli()
    except:
        print '(Failed to load moduli -- gex will be unsupported.)'
        raise
    t.add_server_key(host_key)
    server = Server()
    try:
        t.start_server(server=server)
    except paramiko.SSHException, x:
        print '*** SSH negotiation failed.'
        sys.exit(1)

    # wait for auth
    chan = t.accept(20)
    if chan is None:
        print '*** No channel.'
        sys.exit(1)
    log('Authenticated!')

    server.event.wait(10)
    if not server.event.isSet():
        print '*** Client never asked for a shell.'
        sys.exit(1)

    chan.send('\r\n\r\nNSA.gov :: Any unauthorized access PROHIBITED\r\n')
    chan.send('This Linux machine has been modified by the US Government\r\n')
    chan.send('to prevent unauthorized access.\r\n')
    chan.send('Location tracking has been activated.\r\n\r\n')
    f = chan.makefile('rU')
    while True:
        chan.send('(%s@waffle) # ' % server.username)
        command = ''
        while True:
            c = f.read(1)
            if c == '\r' or c == '\n':
                break
            chan.send(c)
            command += c
        response = process_command(command)
        log(server.username + " says: " + command)
        log(  " we responded:")
        log(response)
        chan.send('\r\n' +
                  response.replace('\n', '\r\n') +
                  '\r\n')
        if command.startswith('please'):
            break

    chan.close()

    return t

if __name__ == "__main__":
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 2222))
    except Exception, e:
        print "*** Bind failed: " + str(e)
        traceback.print_exc()
        sys.exit(1)

    try:
        sock.listen(100)
        print 'Listening for connection...'
        client, addr = sock.accept()
    except Exception, e:
        print '*** Listen/accept failed: ' + str(e)
        traceback.print_exc()
        sys.exit(1)

    log('Connection from %s %d' % (addr[0], addr[1]))

    try:
        t = run_ssh_server(client)
    except Exception, e:
        print '*** Caught exception ' + str(e.__class__) + ': ' + str(e)
        traceback.print_exc()
        try:
            t.close()
        except:
            pass
        sys.exit(1)

    sys.exit(0)
    
