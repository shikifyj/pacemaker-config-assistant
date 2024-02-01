import argparse
import control


def main():
    parser = argparse.ArgumentParser(description="vsdshaconf")
    subparsers = parser.add_subparsers(dest='command')

    build_parser = subparsers.add_parser('build', help='一键配置Pacemaker，LINSTOR Controller HA和iSCSILogicalUnit HA')
    build_parser.add_argument('-p', action='store_true', help='Pacemaker基本配置')
    build_parser.add_argument('-l', action='store_true', help='LINSTOR Controller HA')
    build_parser.add_argument('-d', action='store_true', help='Target绑定资源')
    build_parser.add_argument('-t', action='store_true', help='创建Target')
    build_parser.add_argument('-i', action='store_true', help='创建LUN')
    build_parser.add_argument('-v', action='store_true', help='配置Controller IP')
    build_parser.add_argument('-c', action='store_true', help='刷新资源')

    delete_parser = subparsers.add_parser('delete', help='删除配置')
    delete_parser.add_argument('-t', action='store_true', help='删除Target相关资源')
    delete_parser.add_argument('-i', action='store_true', help='删除LUN')

    parser.add_argument('-v', action='store_true', help='Version')
    args = parser.parse_args()

    if args.command == 'build':
        build(args)
    elif args.command == 'delete':
        delete(args)
    elif args.v:
        version(args)
    else:
        parser.print_help()


def build(args):
    iscsi_console = control.ISCSIConsole()
    if args.p:
        control.PacemakerConsole()
    elif args.l:
        control.HAConsole()
    elif args.d:
        iscsi_console.create_drbd()
    elif args.t:
        iscsi_console.create_target()
    elif args.i:
        iscsi_console.create_lun()
    elif args.c:
        control.clean_res()
    elif args.v:
        control.set_ip()
    else:
        control.PacemakerConsole()
        control.HAConsole()
        control.clean_res()
        control.clean_res()
        iscsi_console.create_drbd()
        iscsi_console.create_target()
        iscsi_console.create_lun()


def delete(args):
    iscsi_console = control.ISCSIConsole()
    if args.t:
        iscsi_console.delete_iscsi()
    elif args.i:
        iscsi_console.delete_lun()


def version(args):
    print('v1.0.1')


if __name__ == "__main__":
    main()
