import utils
import pacemaker_cmds
import time
import sys


class PacemakerConsole(object):
    def __init__(self):
        self.pacemaker = pacemaker_cmds.Pacemaker()
        self.config = utils.ConfFile().read_yaml()

    def modify_cluster_name(self):
        name = self.config["cluster"]
        self.pacemaker.modify_cluster_name(name)

    def pacemaker_conf_change(self):
        self.pacemaker.modify_policy()
        self.pacemaker.modify_stickiness()
        self.pacemaker.modify_stonith_enabled()


class HAConsole(object):
    def __init__(self):
        self.ha = pacemaker_cmds.HAController()
        self.config = utils.ConfFile().read_yaml()

    def build_ha_controller(self):
        backup_path = self.config['linstor_dir']
        if not self.ha.linstor_is_conn():
            print('LINSTOR connection refused')
            sys.exit()

        if self.ha.is_active_controller():
            self.ha.stop_controller()
            time.sleep(3)
            self.ha.backup_linstor(backup_path)
            self.ha.move_database(backup_path)

    def check_ha_controller(self, timeout=120):

        node_list = []
        host = pacemaker_cmds.Host()
        hostname = host.get_hostname()
        node_list.append(hostname)

        t_beginning = time.time()

        while True:
            if self.ha.check_linstor_controller(node_list):
                break
            seconds_passed = time.time() - t_beginning
            if timeout and seconds_passed > timeout:
                print("Linstor controller status error")
                return False
            time.sleep(2)

        if self.ha.check_status("linstor-satellite") != 'enabled':
            print('LINSTOR Satellite Service is not "enabled".')
            return False
        if not self.ha.check_satellite_settings():
            print("File linstor-satellite.service modification failed")
            return False

        return True

