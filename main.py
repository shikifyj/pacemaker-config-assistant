import utils


class PacemakerConsole(object):
    def __init__(self):
        self.config = utils.ConfFile().read_yaml()

    def modify_cluster_name(self):
        name = self.config["cluster"]
        print(name)


if __name__ == '__main__':
    PacemakerConsole().modify_cluster_name()
