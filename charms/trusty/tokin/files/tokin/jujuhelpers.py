#pylint: disable=r0201,c0111,c0325,c0103
#
""" Handles communication to Juju """

from os.path import expanduser
from subprocess import check_output, STDOUT, CalledProcessError, PIPE, Popen
from time import sleep
import yaml
import json


class JujuEnvironment(object):
    """ handles an existing Juju environment """
    def __init__(self, _name):
        if _name:
            self.name = _name
            self.switch_env(self.name)
        else:
            self.name = self.current_env()


    def get_machine_id(self, fqdn):
        """ gets machine id from machine fqdn """
        import re
        machine_regex = re.compile('^ +"([0-9]+)":$')
        dns_regex = re.compile('^ +dns-name: +' + fqdn + '$')
        #TODO: Use status property
        cmd = Popen('juju status', shell=True, stdout=PIPE)
        for line in cmd.stdout:
            mid = machine_regex.match(line)
            dns = dns_regex.match(line)
            if mid != None:
                current_machine = mid.group(1)
            elif dns != None:
                return current_machine
        print "machine not found"


    def get_ip(self, name):
        """ gets ip from service name """
        status = self.status


    @property
    def machines(self):
        """ Return machines"""
        return self.status['machines'].keys()


    @property
    def services(self):
        """ Returns services"""
        return self.status['services'].keys()


    @property
    def status(self):
        """ Return dictionary with output of juju status """
        try:
            output = check_output(["juju", "status", "--format=json"],
                                  stderr=STDOUT)
            return json.loads(output)
        except CalledProcessError as ex:
            if 'missing namespace, config not prepared' in ex.output:
                print("Environment doesn't exist")
                return None
            print(ex.output)
            raise


    def config_of(self, servicename):
        """ Return dictionary with output of juju get <servicename>"""
        try:
            output = check_output(["juju", "get", "--format=yaml", servicename],
                                  stderr=STDOUT)
            return yaml.load(output)
        except CalledProcessError as ex:
            if 'ERROR service "{}" not found'.format(servicename) in ex.output:
                print("Service doesn't exist")
                return None
            print(ex.output)
            raise


    def get_services(self, startstring, key, value):
        services = {}
        status = self.status
        for service in status['services'].keys():
            if service.startswith(startstring):
                config = self.config_of(service)
                if config['settings'][key]['value'] == value:
                    services[service] = status['services'][service]
        return services



    @property
    def juju_password(self):
        """ Gets the default password from the Juju environment"""
        file_path = expanduser('~/.juju/environments/%s.jenv' % self.name)
        stream = open(file_path, "r")
        doc = yaml.load(stream)
        password = doc.get('password')
        return password


    @property
    def bootstrap_user(self):
        """ Gets the bootstrap user from the Juju environment"""
        file_path = expanduser('~/.juju/environments/%s.jenv' % self.name)
        stream = open(file_path, "r")
        doc = yaml.load(stream)
        password = doc.get('bootstrap-config').get('bootstrap-user')
        return password


    def add_machines(self, machines):
        """ Add all machines received from provider to Juju environment"""
        print "adding machines to juju"
        processes = set()
        for machinefqdn in machines:
            print '\tAdding %s' % machinefqdn
            processes.add(Popen([
                'juju', 'add-machine',
                'ssh:{}@{}'.format(self.bootstrap_user, machinefqdn)
            ]))
        for proc in processes:
            if proc.poll() is None:
                proc.wait()
            if proc.poll() > 0:
                raise Exception('error while adding machines')


    def deploy_gui(self): # pylint: disable=R0201
        """ Deploys juju-gui to node 0 """
        try:
            # TODO: We don't need to wait for this to finish
            check_output(['juju', 'deploy', 'juju-gui', '--to', '0'],
                         stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def deploy_lxc_networking(self):
        self.deploy("local:dhcp-server", "dhcp-server", to='0')
        self.deploy("local:lxc-networking", "lxc-networking", to='1')
        for machine in self.machines:
            if machine != '1' and machine != '0':
                self.add_unit('lxc-networking', to=machine)


    def deploy(self, charm, name, config_path=None, to=None): #pylint: disable=c0103
        """ Deploy <charm> as <name> with config in <config_path> """
        c_action = ['juju', 'deploy']
        c_charm = [charm, name]
        c_config = []
        c_to = []
        if config_path:
            c_config = ['--config', config_path]
        if to:
            c_to = ['--to', to]
        command = c_action + c_charm + c_config + c_to
        try:
            check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def add_unit(self, name, to=None): #pylint: disable=c0103
        """ Add unit to existing Charm"""
        c_action = ['juju', 'add-unit', name]
        c_to = []
        if to:
            c_to = ['--to', to]
        command = c_action + c_to
        try:
            check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def deploy_bundle(self, bundle_path):
        """ Deploy Juju bundle """
        c_action = ['juju', 'deployer']
        c_bundle = ['-c', bundle_path]
        command = c_action + c_bundle
        try:
            check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def action_do(self, unit, action, **kwargs):
        c_action = ['juju', 'action', 'do', str(unit), str(action)]
        c_params = []
        for key, value in kwargs.iteritems():
            c_params.append("{}={}".format(key, value))
        command = c_action + c_params
        try:
            print str(command)
            return check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def destroy_service(self, name):
        """ Deploy <charm> as <name> with config in <config_path> """
        c_action = ['juju', 'destroy']
        c_charm = [name]
        c_force = ['--force']
        command = c_action + c_charm + c_force
        try:
            check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def add_relation(self, charm1, charm2):
        """ add relation between two charms """
        c_action = ['juju', 'add-relation']
        c_relations = [charm1, charm2]
        command = c_action + c_relations
        try:
            check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def charm_exists(self, name):
        return name in self.status['services']


    @staticmethod
    def switch_env(name):
        """switch to environment with given name"""
        try:
            check_output(['juju', 'switch', str(name)], stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    @staticmethod
    def env_exists(name):
        """Checks if Juju env with given name exists."""
        try:
            envs = check_output(['juju', 'switch', '--list'],
                                stderr=STDOUT).split()
        except CalledProcessError as ex:
            print ex.output
            raise
        return name in envs


    @staticmethod
    def current_env():
        """ Returns the current active Juju environment """
        try:
            return check_output(['juju', 'switch'], stderr=STDOUT).rstrip()
        except CalledProcessError as ex:
            print ex.output
            raise


    @staticmethod
    def create(name, bootstrap_host, juju_config, machines):
        """Creates Juju environment, add all available machines,
        deploy juju_gui"""
        JujuEnvironment._create_env(name, bootstrap_host, juju_config)
        # Wait 5 seconds before adding machines because python
        # is too fast for juju
        sleep(5)
        environment = JujuEnvironment(name)
        sleep(5)
        environment.add_machines(machines)
        environment.deploy_gui()


    @staticmethod
    def _create_env(name, bootstrap_host, juju_config):
        """ Add new Juju environment with name = name
        and bootstrap this environment """
        print "adding juju environment %s" % name
        juju_config['bootstrap-host'] = bootstrap_host
        # get original environments config
        with open(expanduser("~/.juju/environments.yaml"), 'r') as config_file:
            config = yaml.load(config_file)
        if config['environments'] == None:
            config['environments'] = dict()
        # add new environment
        config['environments'][name] = juju_config
        # write new environments config
        with open(expanduser("~/.juju/environments.yaml"), 'w') as config_file:
            config_file.write(yaml.dump(config, default_flow_style=False))
        # Bootstrap new environmnent
        try:
            check_output(['juju', 'switch', name], stderr=STDOUT)
            print "bootstrapping juju environment"
            sleep(5) # otherwise we get a weird error
            check_output(['juju', 'bootstrap'], stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise
