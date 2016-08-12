import os
import random
import shutil
import sys
import socket

import flask
from flask import request

# Configuration information:
GConf_MenuSeparator = '\n'

GConf_PortraitWidth = 300
GConf_PortraitHeight = 300

GConf_ThankYouDelaySeconds = 10
GConf_SessionPasswordLen = 7
GConf_TempDirLoc = 'static/tmp/'
GConf_QuitHeader = 'quit'


class TCandidate:
    def __init__(self, id_, name, rel_photo_loc):
        """
        Creates a new instance of the Candidate Class
        :param id_: The candidate's ID
        :param name: The name of the candidate
        :param rel_photo_loc: The physical path to the image file.
        :param http_src: The HTTP path to be provided:
        """
        self.m_ID = id_
        self.m_Name = name

        self.m_PhotoLoc = rel_photo_loc
        self.m_HTTPSrc = '/'.join(rel_photo_loc.split('/')[1:])

        self.m_NumVotes = 0

    @property
    def name(self):
        return self.m_Name

    @property
    def img_src(self):
        return flask.url_for('static', filename=self.m_HTTPSrc)

    @property
    def vote_link(self):
        return '/vote_for/{0}'.format(self.m_ID)

    @property
    def num_votes(self):
        return self.m_NumVotes

    def add_vote(self):
        self.m_NumVotes += 1


GAddress = None
GPort = None
GElectionName = None
GCandidates = []
GApp = None
GSessionPassword = None

# GVoters = []      # -> Superfluous!


def util_get_empty_port(host_name):
    sock = socket.socket()
    sock.bind((host_name, 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def ux_get_str_input(prompt):
    return str(input(prompt)).strip()


def ux_get_int_input(prompt, min_v=None, max_v=None):
    if min_v is not None:
        assert type(min_v) in (int, )
    if max_v is not None:
        assert type(max_v) in (int, )

    choice = None
    valid = False

    while not valid:
        choice = ux_get_str_input(prompt)

        try:
            choice = int(choice)
        except ValueError:
            print('Not a valid integer! Please try again!')
            continue

        if min_v is not None:
            if choice < min_v:
                print('This number is less than the permitted minimum, {0}! Please try again!'.format(min_v))
                valid = False
                continue
            else:
                valid = True
        else:
            valid = True

        if valid and max_v is not None:
            if choice > max_v:
                print('This number is greater than the permitted maximum, {0}! Please try again!'.format(max_v))
                valid = False
                continue
            else:
                valid = True
        else:
            valid = True

    return choice


def init_fs():
    # Creating the temporary directory in static (static/tmp):
    if os.path.isdir(GConf_TempDirLoc):
        # Deleting the directory if it already exists:
        shutil.rmtree(GConf_TempDirLoc)

    os.makedirs(GConf_TempDirLoc)


def init_election():
    global GElectionName
    GElectionName = ux_get_str_input('Please enter the name of the election: ')

    global GConf_MenuSeparator
    print(GConf_MenuSeparator)


def init_candidates():
    num_candidates = ux_get_int_input('Please enter the number of candidates participating: ')

    for i_c in range(num_candidates):
        c_id = i_c + 1      # c_id is the ID of the candidate
        print('\nCandidate {0}'.format(c_id))

        # Getting the name of the candidate:
        name = ux_get_str_input('Please enter the candidate\'s name: ')

        # Getting the candidate's photo's location from the user:
        src_photo_loc = None
        valid_photo_loc = False
        while not valid_photo_loc:
            src_photo_loc = ux_get_str_input('Please enter the file path of the candidate\'s photo:\n'
                                             'For example: "C:\\Users\\Student\\Documents\\Candidate{id}.jpg"\n'
                                             'For example: "resources\\Candidate{id}.jpg": '.format(id=c_id))

            src_photo_loc = os.path.abspath(src_photo_loc)

            valid_photo_loc = os.path.isfile(src_photo_loc)

            if valid_photo_loc:
                print('Found a photo at "{0}"'.format(src_photo_loc))
                choice = ux_get_str_input('Is this the photo you were looking for? [Y/n] ')
                if choice[0].lower() == 'n':
                    print('Okay! Try again!')
                    valid_photo_loc = False
                else:
                    valid_photo_loc = True

            else:
                print('Couldn\'t find the file at "{0}"!'.format(src_photo_loc))
                print('Hint: Did you mention the correct file extension? (.jpg, .jpeg, .png, etc)')
                choice = ux_get_str_input('Try again? [Y/n] ')
                if choice[0].lower() == 'n':
                    print('Okay! Quitting!')
                    exit(-1)
                else:
                    print('Trying again!')

        # Copying the image-file into the temporary directory in the static directory:
        image_base_name = os.path.basename(src_photo_loc)
        op_photo_loc = os.path.join(GConf_TempDirLoc, image_base_name)

        shutil.copy(src_photo_loc, op_photo_loc)

        # Creating the candidate:
        global GCandidates
        GCandidates.append(TCandidate(c_id, name, op_photo_loc))

    global GConf_MenuSeparator
    print(GConf_MenuSeparator)


def init_voters():
    print('It\'s time for the voters!')

    valid = False
    while not valid:
        fp = ux_get_str_input('Please enter the file-path to a text file containing one voter-name on each row: ')
        fp = os.path.abspath(fp)

        if os.path.isfile(fp):
            with open(fp, 'r') as f:
                voters = f.read().split('\n')
                print('Found a file at "{0}"'.format(fp))
                print('According to this file, these are the voters:')

                for i, v in enumerate(voters):
                    print('{sl_no}) {name}'.format(sl_no=i + 1, name=v))

            choice = ux_get_str_input('Does this look right? [Y/n] ')

            if choice[0].lower() == 'n':
                print('Okay! Trying again!')
            else:
                print('Okay! Continuing!')

    global GConf_MenuSeparator
    print(GConf_MenuSeparator)


def init_g_app():
    global GApp
    global GElectionName
    global GAddress
    global GPort
    global GSessionPassword

    GAddress = ux_get_str_input('Please enter the host-name on which to host the server (Example: "127.0.0.2") ')
    # GAddress = '127.0.0.1'  # DEBUG

    GPort = util_get_empty_port(GAddress)
    GApp = flask.Flask(GElectionName)

    # Generating the session password and notifying the user:
    GSessionPassword = str(random.randint(int('1' + '0' * (GConf_SessionPasswordLen - 1)),
                                          int('9' * GConf_SessionPasswordLen)))
    print('IMPORTANT')
    print('Your session password is: "{0}"'.format(GSessionPassword))
    print('In order to conclude the election, you (the election official) must visit:')
    print('http://{address}:{port}/{quit_header}/{password}'.format(address=GAddress,
                                                                    port=GPort,
                                                                    quit_header=GConf_QuitHeader,
                                                                    password=GSessionPassword))

    def set_routing_procedures(g_app):
        @g_app.route('/')
        def index():
            return flask.render_template('index.html',
                                         election_name=GElectionName)

        @g_app.route('/vote')
        def vote():
            return flask.render_template('vote.html',
                                         candidates=GCandidates,
                                         portrait_width=GConf_PortraitWidth,
                                         portrait_height=GConf_PortraitHeight)

        @g_app.route('/thank-you')
        def thank_you():
            global GConf_ThankYouDelaySeconds
            return flask.render_template('thank-you.html',
                                         delay=GConf_ThankYouDelaySeconds,
                                         redirect_loc='/')

        @g_app.route('/vote_for/<candidate_id>')
        def vote_for(candidate_id):
            global GCandidates

            i_candidate = int(candidate_id) - 1
            GCandidates[i_candidate].add_vote()

            return flask.redirect('/thank-you')

        @g_app.route('/{quit_header}/{password}'.format(quit_header=GConf_QuitHeader, password=GSessionPassword))
        def quit_server():
            shut_down_procedure = request.environ.get('werkzeug.server.shutdown')
            shut_down_procedure()

            global GCandidates
            max_num_votes = -1
            i_current_winner = None

            for i, c in enumerate(GCandidates):
                if c.num_votes > max_num_votes:
                    max_num_votes = c.num_votes
                    i_current_winner = i
                elif c.num_votes == max_num_votes:
                    i_current_winner = None

            if i_current_winner is None:
                verdict = 'It\'s a tie!'
            else:
                verdict = '{candidate_name} has won, with {num_votes} votes!'.format(
                    candidate_name=GCandidates[i_current_winner].name,
                    num_votes=GCandidates[i_current_winner].num_votes)

            return flask.render_template('shut-down.html',
                                         candidates=GCandidates,
                                         verdict=verdict)

    set_routing_procedures(GApp)


def de_init_fs():
    # Clearing the temporary directory:
    if os.path.isdir(GConf_TempDirLoc):
        shutil.rmtree(GConf_TempDirLoc)


def run(*args):
    init_fs()

    init_election()
    init_candidates()

    # ALL DEBUG:
    # global GElectionName
    # global GCandidates
    # global GAddress
    # global GApp
    #
    # GElectionName = 'Test Election'
    # GCandidates = [
    #     TCandidate(1, 'Nikhil TI', 'tmp/nti.jpg'),
    #     TCandidate(2, 'Melvin Mathews', 'tmp/mm.jpg')
    # ]
    #
    # # END DEBUG

    # init_voters()     # -> Superfluous!

    # Initializing the app:
    init_g_app()

    # Running:
    print('Okay! We\'re firing up the server... Please wait.')
    print('Clients should connect to:')
    print('http://{address}:{port_num}/'.format(address=GAddress,
                                                port_num=GPort))
    global GAddress
    GApp.run(GAddress, port=GPort)
    # GApp.run(GAddress, port=GPort, debug=True)    # DEBUG

    de_init_fs()


if __name__ == '__main__':
    run(*sys.argv)
