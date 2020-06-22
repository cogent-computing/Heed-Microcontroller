import os
import json
import pysftp
import unittest


class Enactor:

    def __init__(self, dev_info, sftp_location, sftp_port, sftp_username, sftp_password, sftp_key_location,
                 sftp_directory):
        self.dev_info = dev_info
        self.cnopts = pysftp.CnOpts()
        self.cnopts.hostkeys = None
        self.change_threshold = 0.05
        self.sftp_location = sftp_location
        self.sftp_port = sftp_port
        self.sftp_username = sftp_username
        self.sftp_password = sftp_password
        self.sftp_key_location = sftp_key_location
        self.sftp_directory = sftp_directory

    def stop(self):
        pass

    def enact_light_plan(self, dev, BL_Quota, NL_Quota):
        # print("Enacting: ", dev, " BL: ", BL_Quota, " NL: ", NL_Quota)

        quota_skeleton = [
            {
                "name": "LED Night Light",
                "conditional": "True",
                "level_range_lo": 0,
                "quota_total": NL_Quota,
                "level_range_hi": 10,
                "remote_quota_name": "LED NL",
                "unit": 8
            },
            {
                "name": "LED Bright Light",
                "conditional": "True",
                "level_range_lo": 0,
                "quota_total": BL_Quota,
                "level_range_hi": 190,
                "remote_quota_name": "LED BL",
                "unit": 8
            }
        ]

        # Check whether there is any major change to the tariff/plan
        prev_plan = self.retreive_previous_plan(dev)

        #Write New Plan Locally

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath("__file__")))
        f_name = os.path.join(os.path.join(os.path.join(base_dir, "deployment"), "plans"), dev + ".json")

        with open(f_name, 'w+') as outfile:
            json.dump(quota_skeleton, outfile)

        key_path = os.path.join(os.path.dirname(base_dir),self.sftp_key_location)

        with pysftp.Connection(self.sftp_location, port=self.sftp_port, username=self.sftp_username,
                               password=self.sftp_password,
                               private_key=key_path, cnopts=self.cnopts) as sftp:
            with sftp.cd(self.sftp_directory):
                sftp.put(f_name)


        #print("Diff: ", self.check_diff_light(prev_plan, BL_Quota, NL_Quota))

        if self.check_diff_light(prev_plan, BL_Quota, NL_Quota) >= self.change_threshold:
            # Enact on website
            self.make_changes_on_site(dev)
            return True
        return False

    def enact_socket_plan(self, dev, AC_total):
        # print("Enacting: ", dev, " AC ", AC_total)

        quota_skeleton = [
            {
                "name": "Energy",
                "conditional": "True",
                "level_range_lo": 1,
                "quota_total": AC_total,
                "level_range_hi": 50000,
                "remote_quota_name": "AC Day Energy",
                "unit": 5
            }
        ]

        # Check whether there is any major change to the tariff/plan
        prev_plan = self.retreive_previous_plan(dev)#

        # Enact New Plan

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath("__file__")))
        f_name = os.path.join(os.path.join(os.path.join(base_dir, "deployment"), "plans"), dev + ".json")

        with open(f_name, 'w+') as outfile:
            json.dump(quota_skeleton, outfile)

        key_path = os.path.join(base_dir, self.sftp_key_location)

        with pysftp.Connection(self.sftp_location, port=self.sftp_port, username=self.sftp_username,
                               password=self.sftp_password,
                               private_key=key_path, cnopts=self.cnopts) as sftp:
            with sftp.cd(self.sftp_directory):
                sftp.put(f_name)

        #print("Diff: ",self.check_diff_socket(prev_plan, AC_total))
        if self.check_diff_socket(prev_plan, AC_total) >= self.change_threshold:
            # Enact on website
            self.make_changes_on_site(dev)
            return True
        return False

    def retreive_previous_plan(self, dev):
        # print("Retreiving previous plan for dev",dev)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath("__file__")))
        f_name = os.path.join(os.path.join(os.path.join(base_dir, "deployment"), "plans"), dev + ".json")

        key_path = os.path.join(base_dir, self.sftp_key_location)

        with pysftp.Connection(self.sftp_location, port=self.sftp_port, username=self.sftp_username,
                               password=self.sftp_password,
                               private_key=key_path, cnopts=self.cnopts) as sftp:
            with sftp.cd(self.sftp_directory):
                try:
                    sftp.get(dev + ".json", f_name)
                except IOError:
                    print('Previous File not There')
                    return None

        with open(f_name, 'r') as infile:
            data = json.load(infile)
            BL = 0
            NL = 0
            if len(data) == 2:
                if data[0]["remote_quota_name"] == "LED NL":
                    NL = data[0]["quota_total"]
                    BL = data[1]["quota_total"]
                elif data[0]["remote_quota_name"] == "LED BL":
                    BL = data[0]["quota_total"]
                    NL = data[1]["quota_total"]
                else:
                    raise ValueError("loaded Json doesn't have LED NL or LED BL")
                return BL, NL
            elif len(data) == 1:
                return data[0]["quota_total"]
            else:
                raise ValueError("loaded Json not in the right Format")

    def check_diff_light(self, prev_plan, BL_Quota, NL_Quota):
        # print("Checking Difference - Lights",prev_plan, BL_Quota, NL_Quota)
        if prev_plan is None:
            return 1.0
        if prev_plan[0] == BL_Quota and prev_plan[1] == NL_Quota:
            return 0.0
        elif BL_Quota == 0 or NL_Quota == 0 or prev_plan[0] == 0 or prev_plan[1] == 0:
            # Values not the same but one of them has either gone from being a 0 to higher number or other way around
            return 1.0
        else:
            # generic case, they've changed, how much will determine whether to send it back or nor
            # No Values should be 0 here
            diff = 0.0;
            diff += abs(prev_plan[0] - BL_Quota) / (prev_plan[0] + BL_Quota) * 2.0 * 0.5  #Normal form weighted by 0.5
            diff += abs(prev_plan[1] - NL_Quota) / (prev_plan[1] + NL_Quota) * 2.0 * 0.5
            return diff

    def check_diff_socket(self, prev_plan, AC_total):
        # print("Checking Difference - Sockets",prev_plan, AC_total)
        if prev_plan is None:
            return 1.0
        if prev_plan == AC_total:
            return 0.0
        elif AC_total == 0 or prev_plan == 0:
            # Values not the same but one of them has either gone from being a 0 to higher number or other way around
            return 1.0
        else:
            # generic case, they've changed, how much will determine whether to send it back or nor
            # No Values should be 0 here
            diff = abs(prev_plan - AC_total) / (prev_plan + AC_total) * 2.0
            return diff

    def make_changes_on_site(self, dev):
        print("Making Changes on Website for: ", dev)
