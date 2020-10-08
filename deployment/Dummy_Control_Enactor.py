
class Enactor:

    def __init__(self, dev_info, sftp_location, sftp_port, sftp_username, sftp_password, sftp_key_location,
                 sftp_directory):
        pass

    def stop(self):
        pass

    def enact_light_plan(self, dev, BL_Quota, NL_Quota):
        return True

    def enact_socket_plan(self, dev, AC_total):
       return True

    def retreive_previous_plan_AC(self, dev):
        return None

    def retreive_previous_plan_DC(self, dev):
        return None

    def check_diff_light(self, prev_plan, BL_Quota, NL_Quota):
        return 1.0

    def check_diff_socket(self, prev_plan, AC_total):
        return 1.0
