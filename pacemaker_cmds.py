import utils
import time
import re


class Host(object):

    def modify_hostname(self, hostname):
        cmd = f'hostnamectl set-hostname {hostname}'
        utils.exec_cmd(cmd)

    def modify_hostsfile(self, ip, hostname):
        cmd = f"sed -i 's/{ip}.*/{ip}\t{hostname}/g' /etc/hosts"
        utils.exec_cmd(cmd)

    def get_hostname(self):
        return utils.exec_cmd('hostname')


class Pacemaker(object):
    def modify_cluster_name(self, cluster_name):
        cmd = f"crm config property cluster-name={cluster_name}"
        utils.exec_cmd(cmd)

    def modify_policy(self, status='stop'):
        cmd = f"crm config property no-quorum-policy={status}"
        utils.exec_cmd(cmd)

    def modify_stonith_enabled(self):
        cmd = "crm config property stonith-enabled=false"
        utils.exec_cmd(cmd)

    def modify_stickiness(self):
        cmd = "crm config rsc_defaults resource-stickiness=1000"
        utils.exec_cmd(cmd)

    def check_crm_conf(self):
        cmd = 'crm config show | cat'
        data = utils.exec_cmd(cmd)
        data_property = re.search('property cib-bootstrap-options:\s([\s\S]*)', data).group(1)
        # re_cluster_name = re.findall('cluster-name=(\S*)', data_property)
        re_stonith_enabled = re.findall('stonith-enabled=(\S*)', data_property)
        re_policy = re.findall('no-quorum-policy=(\S*)', data_property)
        re_resource_stickiness = re.findall('resource-stickiness=(\d*)', data)

        # 不进行cluster_name 的判断
        # if not re_cluster_name or re_cluster_name[0] != cluster_name:
        #     return

        if not re_stonith_enabled or re_stonith_enabled[0] != 'false':
            return

        if not re_policy or re_policy[0] not in ['ignore', 'stop']:
            return

        if not re_resource_stickiness or re_resource_stickiness[0] != '1000':
            return

        return True


class HAController(object):
    stencil = """primitive p_drbd_linstordb ocf:linbit:drbd \
            params drbd_resource=linstordb \
            op monitor interval=29 role=Master \
            op monitor interval=30 role=Slave \
            op start interval=0 timeout=240s \
            op stop interval=0 timeout=100s
    primitive p_fs_linstordb Filesystem \
            params device="/dev/drbd/by-res/linstordb/0" directory="/var/lib/linstor" fstype=ext4 \
            op start interval=0 timeout=60s \
            op stop interval=0 timeout=100s \
            op monitor interval=20s timeout=40s
    primitive p_linstor-controller systemd:linstor-controller \
            op start interval=0 timeout=100s \
            op stop interval=0 timeout=100s \
            op monitor interval=30s timeout=100s
    group g_linstor p_fs_linstordb p_linstor-controller
    ms ms_drbd_linstordb p_drbd_linstordb \
            meta master-max=1 master-node-max=1 clone-max=3 clone-node-max=1 notify=true
    colocation c_linstor_with_drbd inf: g_linstor ms_drbd_linstordb:Master
    order o_drbd_before_linstor inf: ms_drbd_linstordb:promote g_linstor:start"""

    def linstor_is_conn(self):
        cmd_result = utils.exec_cmd('linstor n l')
        if not 'Connection refused' in cmd_result:
            return True

    def is_active_controller(self):
        cmd_result = utils.exec_cmd("systemctl status linstor-controller | cat")
        status = re.findall('Active:\s(\w*)\s', cmd_result)
        if status and status[0] == 'active':
            return True

    def stop_controller(self):
        cmd = f"systemctl stop linstor-controller"
        utils.exec_cmd(cmd)

    def backup_linstor(self, backup_path):
        """
        E.g: backup_path = 'home/samba' 文件夹
        """
        if 'No such file or directory' in utils.exec_cmd(f"ls {backup_path}"):
            utils.exec_cmd(f'mkdir -p {backup_path}')
        if not backup_path.endswith('/'):
            backup_path += '/'
        cmd = f"rsync -avp /var/lib/linstor {backup_path}"
        if not bool(utils.exec_cmd(f'[ -d {backup_path} ] && echo True')):
            utils.exec_cmd(f"mkdir -p {backup_path}")
        utils.exec_cmd(cmd)

    def move_database(self, backup_path):
        if backup_path.endswith('/'):
            backup_path = backup_path[:-1]

        cmd_mkfs = "mkfs.ext4 /dev/drbd/by-res/linstordb/0"
        cmd_rm = "rm -rf /var/lib/linstor/*"
        cmd_mount = "mount /dev/drbd/by-res/linstordb/0 /var/lib/linstor"
        cmd_rsync = f"rsync -avp {backup_path}/linstor/ /var/lib/linstor/"

        utils.exec_cmd(cmd_mkfs)
        utils.exec_cmd(cmd_rm)
        utils.exec_cmd(cmd_mount)
        utils.exec_cmd(cmd_rsync)

    def add_linstordb_to_pacemaker(self, clone_max):
        self.stencil = self.stencil.replace(f'clone-max=3', f'clone-max={clone_max}')
        utils.exec_cmd(f"echo -e '{self.stencil}' > crm_lincontrl_config")
        cmd = "crm config load update crm_lincontrl_config"
        utils.exec_cmd(cmd)

    def check_linstor_controller(self, list_node):
        data = utils.exec_cmd('crm st | cat')
        p_fs_linstordb = re.findall('p_fs_linstordb\s*\(ocf::heartbeat:Filesystem\):\s*(.*)', data)
        p_linstor_controller = re.findall('p_linstor-controller\s*\(systemd:linstor-controller\):\s*(.*)', data)
        masters = re.findall('Masters:\s\[\s(\w*)\s]', data)
        slaves = re.findall('Slaves:\s\[\s(.*)\s]', data)

        if not p_fs_linstordb or 'Started' not in p_fs_linstordb[0]:
            return
        if not p_linstor_controller or 'Started' not in p_linstor_controller[0]:
            return
        if not masters and len(masters) != 1:
            return
        if not slaves:
            return

        slaves = slaves[0].split(' ')
        all_node = []
        all_node.extend(masters)
        all_node.extend(slaves)
        if set(all_node) != set(list_node):
            return
        return True

    def check_satellite_settings(self):
        # 配置文件检查
        satellite_conf = "/etc/systemd/system/multi-user.target.wants/linstor-satellite.service"
        conf_data = utils.exec_cmd(f"cat {satellite_conf}")
        if not "Environment=LS_KEEP_RES=linstordb" in conf_data:
            return False

        # symbolic link 检查
        cmd_result = utils.exec_cmd("file /etc/systemd/system/multi-user.target.wants/linstor-satellite.service")
        if not "symbolic link to" in cmd_result:
            return False
        return True

    def check_status(self, name):
        cmd = f'systemctl is-enabled {name}'
        result = utils.exec_cmd(cmd)
        if 'No such file or directory' in result:
            return
        if name == "rtslib-fb-targetctl":
            if 'disabled' in result:
                return 'disabled'
            else:
                return 'enabled'
        return result


class DRBD(object):
    cmds = """primitive p_drbd_<resource_name> ocf:linbit:drbd \
        params drbd_resource=<resource_name> \
        op monitor interval=29 role=Master \
        op monitor interval=30 role=Slave
ms ms_drbd_<resource_name> p_drbd_<resource_name> \
        meta master-max=1 master-node-max=1 clone-max=<DRBD_total_number> clone-node-max=1 notify=true target-role=Stopped
location DRBD_<resource_name>_<node_name> ms_drbd_<resource_name> -inf: <node_name>"""

    def configure_drbd(self, res_name, node_name):
        for i in len(res_name):
            self.cmds = self.cmds.replace("<resource_name>", res_name[i])
            self.cmds = self.cmds.replace("<DRBD_total_number>", len(res_name))
            self.cmds = self.cmds.replace("<node_name>", node_name)
            utils.exec_cmd(f"echo -e '{self.cmds}' > crm_drbd_config{i}")
            cmd = f"crm config load update crm_drbd_config{i}"
            utils.exec_cmd(cmd)


class Target(object):
    cmds = """"primitive vip_prtblk_on<group_number> portblock \
        params ip=<ip> portno=3260 protocol=tcp action=block \
        op start timeout=20 interval=0 \
        op stop timeout=20 interval=0 \
        op monitor timeout=20 interval=20
primitive vip<group_number> IPaddr2 \
        params ip=<ip> cidr_netmask=24 \
        op monitor interval=10 timeout=20
primitive target<group_number> iSCSITarget \
        params iqn="iqn.2023-07.com.example:target<group_number>" implementation=lio-t portals=<ip>:3260 \
        op start timeout=50 interval=0 \
        op stop timeout=40 interval=0 \
        op monitor interval=15 timeout=40
group gvip<group_number> vip_prtblk_on<group_number> vip<group_number> target<group_number> \
        meta target-role=Started

primitive vip_prtblk_off<group_number> portblock \
        params ip=<ip> portno=3260 protocol=tcp action=unblock \
        op start timeout=20 interval=0 \
        op stop timeout=20 interval=0 \
        op monitor timeout=20 interval=20 \
        meta target-role=Stopped
        
location lo_gvip<group_number>_<node_name> gvip<group_number> -inf: <node_name>
colocation co_prtblkoff<group_number> inf: vip_prtblk_off<group_number> gvip<group_number>
    """

    def configure_target(self, group_number, vip, node_name):
        
