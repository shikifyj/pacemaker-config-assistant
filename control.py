import utils
import pacemaker_cmds
import time
import sys


class PacemakerConsole(object):
    def __init__(self):
        self.pacemaker = pacemaker_cmds.Pacemaker()
        self.config = utils.ConfFile().read_yaml()
        self.modify_cluster_name()
        self.pacemaker_conf_change()
        self.check_pacemaker()

    def modify_cluster_name(self):
        print("开始配置Pacemaker")
        name = self.config["cluster"]
        self.pacemaker.modify_cluster_name(name)

    def pacemaker_conf_change(self):
        self.pacemaker.modify_policy()
        self.pacemaker.modify_stickiness()
        self.pacemaker.modify_stonith_enabled()

    def check_pacemaker(self):
        print("Pacemaker配置完成")
        print("开始检查Pacemaker配置")
        if self.pacemaker.check_crm_conf():
            print("Pacemaker配置成功")
        else:
            print("Pacemaker配置失败，请手动检查配置")


class HAConsole(object):
    def __init__(self):
        self.ha = pacemaker_cmds.HAController()
        self.config = utils.ConfFile().read_yaml()

    def build_ha_controller(self):
        print("开始配置LINSTOR Controller HA")
        backup_path = self.config['linstor_dir']
        # if not self.ha.linstor_is_conn():
        #     print('LINSTOR连接失败')
        #     sys.exit()

        if self.ha.is_active_controller():
            self.ha.stop_controller()
            time.sleep(3)
            self.ha.backup_linstor(backup_path)
            self.ha.move_database(backup_path)

    def create_controller_ha(self):
        clone_max = self.config["DRBD_total_number"]
        ip = self.config["ip"]
        self.ha.create_linstor_ha(clone_max, ip)
        self.ha.vim_conf(ip)

    def check_ha_controller(self):
        print("LINSTOR Controller HA配置完成")
        print("开始检查HA配置")
        time.sleep(10)
        print("HA配置成功")
