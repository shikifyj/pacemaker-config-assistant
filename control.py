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
        self.build_ha_controller()
        self.create_controller_ha()
        self.check_ha_controller()

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


class ISCSIConsole(object):
    def __init__(self):
        self.target = pacemaker_cmds.Target()
        self.drbd = pacemaker_cmds.DRBD()
        self.iscsi = pacemaker_cmds.ISCSI()
        self.config = utils.ConfFile().read_yaml()

    def create_target(self):
        print("开始创建Target")
        iscsi_list = self.config['iscsi']
        for iscsi in iscsi_list:
            group_number = iscsi['group_number']
            ip_list = iscsi['ip']
            node_diskless = iscsi['node_diskless']
            node_name_list = iscsi['node_away']
            result = self.target.create_target(group_number, ip_list, node_diskless, node_name_list)
            if len(result) == 0:
                print('Target创建成功')
            else:
                print('Target创建失败，请手动检查配置')
                print(f'Error: {result}')

    def create_drbd(self):
        print('开始绑定资源')
        iscsi_list = self.config['iscsi']
        for iscsi in iscsi_list:
            res_name = iscsi['resource_name']
            node_name = iscsi['node_away']
            clone_max = iscsi['DRBD_total_number']
            result = self.drbd.configure_drbd(res_name, node_name, clone_max)
            if len(result) == 0:
                print('资源绑定成功')
            else:
                print('资源绑定失败，请手动检查配置')
                print(f'Error: {result}')

    def create_lun(self):
        print('开始创建LUN')
        iscsi_list = self.config['iscsi']
        for iscsi in iscsi_list:
            resource_name = iscsi['resource_name']
            ip_list = iscsi['ip']
            drbd_device = iscsi['DRBD_device']
            group_number = iscsi['group_number']
            initiator = iscsi['initiatorN']
            lun_number = iscsi['lun_number']
            emulate_tpu = iscsi['emulate_tpu']
            result = self.iscsi.create_iscsi(resource_name, ip_list, drbd_device, group_number, initiator,
                                             lun_number, emulate_tpu)
            if len(result) == 0:
                print('LUN创建成功')
            else:
                print('LUN创建失败，请手动检查配置')
                print(f'Error: {result}')

    def delete_iscsi(self):
        print('开始删除Target')
        iscsi_list = self.config['iscsi']
        for iscsi in iscsi_list:
            group_number = iscsi['group_number']
            self.target.delete_target(group_number)
            print('Target删除成功')

    def delete_lun(self):
        print('开始删除LUN')
        iscsi_list = self.config['iscsi']
        for iscsi in iscsi_list:
            resource_name = iscsi['resource_name']
            self.iscsi.delete_iscsi(resource_name)
            print('LUN删除成功')
