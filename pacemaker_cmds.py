import utils
import re


class Host(object):
    @staticmethod
    def modify_hostname(hostname):
        cmd = f'hostnamectl set-hostname {hostname}'
        utils.exec_cmd(cmd)

    @staticmethod
    def modify_hostsfile(ip, hostname):
        cmd = f"sed -i 's/{ip}.*/{ip}\t{hostname}/g' /etc/hosts"
        utils.exec_cmd(cmd)

    @staticmethod
    def get_hostname():
        return utils.exec_cmd('hostname')


class Pacemaker(object):
    @staticmethod
    def modify_cluster_name(cluster_name):
        cmd = f"crm config property cluster-name={cluster_name}"
        utils.exec_cmd(cmd)

    @staticmethod
    def modify_policy(status='stop'):
        cmd = f"crm config property no-quorum-policy={status}"
        utils.exec_cmd(cmd)

    @staticmethod
    def modify_stonith_enabled():
        cmd = "crm config property stonith-enabled=false"
        utils.exec_cmd(cmd)

    @staticmethod
    def modify_stickiness():
        cmd = "crm config rsc_defaults resource-stickiness=1000"
        utils.exec_cmd(cmd)

    @staticmethod
    def modify_corosync():
        cmd = "crm config property cluster-infrastructure=corosync"
        utils.exec_cmd(cmd)

    @staticmethod
    def check_crm_conf():
        cmd = 'crm config show | cat'
        data = utils.exec_cmd(cmd)
        data_property = re.search('property cib-bootstrap-options:\s([\s\S]*)', data).group(1)
        re_stonith_enabled = re.findall('stonith-enabled=(\S*)', data_property)
        re_policy = re.findall('no-quorum-policy=(\S*)', data_property)
        re_resource_stickiness = re.findall('resource-stickiness=(\d*)', data)
        if not re_stonith_enabled or re_stonith_enabled[0] != 'false':
            return False

        if not re_policy or re_policy[0] not in ['ignore', 'stop']:
            return False

        if not re_resource_stickiness or re_resource_stickiness[0] != '1000':
            return False

        return True


class HAController(object):
    # @staticmethod
    # def linstor_is_conn():
    #     cmd_result = utils.exec_cmd('linstor n l')
    #     if not 'Connection refused' in cmd_result:
    #         return True

    @staticmethod
    def is_active_controller():
        cmd_result = utils.exec_cmd("systemctl status linstor-controller | cat")
        status = re.findall('Active:\s(\w*)\s', cmd_result)
        if status and status[0] == 'active':
            return True

    @staticmethod
    def stop_controller():
        cmd = f"systemctl stop linstor-controller"
        utils.exec_cmd(cmd)

    @staticmethod
    def backup_linstor(backup_path):
        if 'No such file or directory' in utils.exec_cmd(f"ls {backup_path}"):
            utils.exec_cmd(f'mkdir -p {backup_path}')
        if not backup_path.endswith('/'):
            backup_path += '/'
        cmd = f"rsync -avp /var/lib/linstor {backup_path}"
        if not bool(utils.exec_cmd(f'[ -d {backup_path} ] && echo True')):
            utils.exec_cmd(f"mkdir -p {backup_path}")
        utils.exec_cmd(cmd)

    @staticmethod
    def move_database(backup_path):
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

    @staticmethod
    def create_linstor_ha(clone_max, ip):
        cmds = [
            f"crm conf primitive p_drbd_linstordb ocf:linbit:drbd \
            params drbd_resource=linstordb \
            op monitor interval=29 role=Master \
            op monitor interval=30 role=Slave \
            op start interval=0 timeout=240s \
            op stop interval=0 timeout=100s",

            f'crm conf primitive p_fs_linstordb Filesystem \
            params device="/dev/drbd/by-res/linstordb/0" directory="/var/lib/linstor" fstype=ext4 \
            op start interval=0 timeout=60s \
            op stop interval=0 timeout=100s \
            op monitor interval=20s timeout=40s',

            f"crm conf primitive p_linstor-controller systemd:linstor-controller \
            op start interval=0 timeout=100s \
            op stop interval=0 timeout=100s \
            op monitor interval=30s timeout=100s",

            f"crm conf primitive vip_ctl IPaddr2 \
            params ip={ip} cidr_netmask=24 \
            op monitor interval=10 timeout=20 \
            meta target-role=Started",

            f"crm conf group g_linstor p_fs_linstordb p_linstor-controller \
            meta target-role=Started",

            f"crm conf ms ms_drbd_linstordb p_drbd_linstordb \
            meta master-max=1 master-node-max=1 clone-max={clone_max} clone-node-max=1 notify=true target-role=Started",

            "crm conf colocation c_linstor_with_drbd inf: g_linstor ms_drbd_linstordb:Master",

            "crm conf colocation c_vip_with_drbd inf: vip_ctl ms_drbd_linstordb:Master",

            "crm conf order o_drbd_before_linstor inf: ms_drbd_linstordb:promote g_linstor:start"
        ]

        for cmd in cmds:
            result = utils.exec_cmd(cmd)
            if result is not None and 'error' in result.lower():
                raise Exception(f'Error executing command: {cmd}')

    @staticmethod
    def vim_conf(ip):
        path = "/etc/linstor/linstor-client.conf"
        cmd = f"sed -i '/^controllers=/ s/$/,{ip}/' {path}"
        utils.exec_cmd(cmd)


class DRBD(object):
    @staticmethod
    def configure_drbd(res_name, node_name, clone_max):
        cmd = f"""crm conf primitive p_drbd_{res_name} ocf:linbit:drbd \
                params drbd_resource={res_name} \
                op monitor interval=29 role=Master \
                op monitor interval=30 role=Slave
        crm conf ms ms_drbd_{res_name} p_drbd_{res_name} \
                meta master-max=1 master-node-max=1 clone-max={clone_max} clone-node-max=1 notify=true 
                target-role=Stopped"""
        utils.exec_cmd(cmd)

        for name in node_name:
            cmd = f"crm conf location DRBD_{res_name}_{name} ms_drbd_{res_name} -inf: {name}"
            utils.exec_cmd(cmd)


class Target(object):
    @staticmethod
    def create_target(group_number, ip_list, node_diskless, node_name_list):
        if len(ip_list) == 1:
            cmds = [f"crm conf primitive vip_prtblk_on{group_number} portblock \
                                params ip={ip_list[0]} portno=3260 protocol=tcp action=block \
                                op start timeout=20 interval=0 \
                                op stop timeout=20 interval=0 \
                                op monitor timeout=20 interval=20",

                    f"crm conf primitive vip {group_number} IPaddr2 \
                                params ip = {ip_list[1]} cidr_netmask = 24 \
                                op monitor interval = 10 timeout = 20",

                    f'crm conf primitive target{group_number} iSCSITarget \
                               params iqn="iqn.2023-07.com.example:target{group_number}" implementation=lio-t '
                    f'portals={ip_list[0]}:3260 \
                               op start timeout=50 interval=0 \
                               op stop timeout=40 interval=0 \
                               op monitor interval=15 timeout=40',

                    f"crm conf group gvip{group_number} vip_prtblk_on{group_number} vip{group_number} target{group_number} \
                               meta target-role=Started",

                    f"crm conf primitive vip_prtblk_off{group_number} portblock \
                               params ip={ip_list[0]} portno=3260 protocol=tcp action=unblock \
                               op start timeout=20 interval=0 \
                               op stop timeout=20 interval=0 \
                               op monitor timeout=20 interval=20 \
                               meta target-role=Stopped",

                    f"crm conf location lo_gvip<group_number>_<node_diskless> gvip<group_number> -100: <node_diskless>",

                    f"crm conf colocation co_prtblkoff<group_number> inf: vip_prtblk_off<group_number> gvip<group_number>"
                    ]
            for cmd in cmds:
                result = utils.exec_cmd(cmd)
                if result is not None and 'error' in result.lower():
                    raise Exception(f'Error executing command: {cmd}')
            for i in range(len(node_name_list)):
                cmd = f"crm conf location lo_gvip{group_number}_{node_name_list[i]} gvip{group_number} -inf: {node_name_list[i]}"
                result = utils.exec_cmd(cmd)
                if result is not None and 'error' in result.lower():
                    raise Exception(f'Error executing command: {cmd}')
