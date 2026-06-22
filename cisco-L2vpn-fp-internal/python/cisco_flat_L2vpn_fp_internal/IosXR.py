import ncs
import time
from cisco_tsdn_core_fp_common.utils import is_netsim_device
from cisco_tsdn_core_fp_common.status_codes.flat_L2vpn_status_codes import StatusCodes
from cisco_tsdn_core_fp_common.status_codes.flat_L2vpn_cfp_base_exception import \
    UserErrorException
from cisco_tsdn_core_fp_common import ietf_L2vpn_nm_const as l2const
from cisco_tsdn_core_fp_common import constants as const


class IosXR:
    def conf_l2vpn(self, site, local):
        self.log.info(f"Configuring Flat L2VPN/SR on IOSXR for service {site.pe}")
        if ((self.service.service_type == "evpn-vpws"
             or self.service.service_type == "evpn-multipoint")
                and site.sr_te.exists()
                and site.sr_te.type == "odn"):
            for rp in site.sr_te.odn.route_policy:
                odn_route_policy_name = rp.route_policy_name
                # retrieve ODN route-policy
                odn_route_policy_value = self.generate_route_policy(rp)
                self.log.debug(f"L2NM ODN RP on {site.pe}: {odn_route_policy_value}")
                routing_policy_vars = ncs.template.Variables()
                routing_policy_vars.add("ROUTE_POLICY_NAME", odn_route_policy_name)
                routing_policy_vars.add("ROUTE_POLICY_VALUE", odn_route_policy_value)
                routing_policy_vars.add("SVC_TYPE", self.service.service_type)
                routing_policy_template = ncs.template.Template(site)
                template = "cisco-flat-L2vpn-fp-cli-routing-policy-template"
                # template only being applied to "evpn-vpws" or "evpn-multipoint"
                routing_policy_template.apply(template, routing_policy_vars)

        policy_name = ""
        # Get the SR-Policy-Name
        if self.service.service_type == "evpn-multipoint":
            pass  # Currently only supports sr-te/odn
        elif site.sr_te.preferred_path:
            policy_name = site.sr_te.preferred_path.policy
            policy_key = (policy_name, site.pe)
            try:
                # Form the policy name
                policy_node = self.root.cisco_sr_te_cfp_internal__sr_te.\
                    cisco_sr_te_cfp_sr_policies_internal__policies.policy
                if policy_key in policy_node:
                    policy_service = policy_node[policy_key]
                    if policy_service.srv6.exists():
                        err_msg = ("L2VPN association with SRv6 via SR policy is not "
                                   + "supported for this release.")
                        raise UserErrorException(self.log, StatusCodes.SRV6_NOT_SUPPORTED) \
                            .set_context("Not supported ", err_msg) \
                            .add_state("Device", str(site.pe)) \
                            .add_state("Service", str(self.service.name)) \
                            .add_state("Policy", str(policy_name)) \
                            .finish()
                    if policy_service.custom_policy_name:
                        policy_name = policy_service.custom_policy_name
                    else:
                        policy_name = ("srte_c_" + str(policy_service.color)
                                       + "_ep_" + str(policy_service.tail_end))
            except UserErrorException:
                raise
            except Exception as e:
                self.log.exception(e)
                policy_name = site.sr_te.preferred_path.policy

        l2vpn_vars = ncs.template.Variables()
        l2vpn_vars.add("LOCAL_NODE", "true" if local is True else "false")
        l2vpn_vars.add("SR_POLICY_NAME", policy_name)
        l2vpn_template = ncs.template.Template(site)
        template = "cisco-flat-L2vpn-fp-cli-p2p-template"
        if self.service.service_type == "evpn-vpws":
            template = "cisco-flat-L2vpn-fp-cli-evpn-vpws-template"
        elif self.service.service_type == "evpn-multipoint":
            template = "cisco-flat-L2vpn-fp-cli-evpn-multipoint-template"
        l2vpn_template.apply(template, l2vpn_vars)

    def generate_route_policy(self, route_policy):
        rp_statements = route_policy.statements.statement
        route_policy_value = self.conf_odn_route_policy(rp_statements)
        return route_policy_value

    def conf_odn_route_policy(self, policy_statements):
        FINAL_RP_VALUE = ""  # final RP value sent to the parent function
        for statement in policy_statements:
            # append chars to begin this new stmnt
            FINAL_RP_VALUE = self.begin_new_stmnt(FINAL_RP_VALUE)
            APPEND_ENDIF = False
            APPEND_PASS = False
            # Match RD Conditions
            if statement.conditions.match_rd_set:
                rd_set = statement.conditions.match_rd_set
                rd_list = ', '.join(rd_set.rd.as_list())
                if rd_list != "":
                    FINAL_RP_VALUE += const.RP_CLI_IF_CLAUSE_CHARS\
                        + "rd in (" + rd_list + ")"\
                        + const.RP_CLI_THEN_CLAUSE_CHARS\
                        + const.RP_CLI_IF_THEN_CLAUSE_SPACES
                    # set append endif to true
                    APPEND_ENDIF = True
            # Match Etag Conditions
            if statement.conditions.match_etag_set:
                etag_set = statement.conditions.match_etag_set
                etag_list = ', '.join(etag_set.etag.as_list())
                if etag_list != "":
                    FINAL_RP_VALUE += const.RP_CLI_IF_CLAUSE_CHARS\
                        + "etag in (" + etag_list + ")"\
                        + const.RP_CLI_THEN_CLAUSE_CHARS\
                        + const.RP_CLI_IF_THEN_CLAUSE_SPACES
                    # set append endif to true
                    APPEND_ENDIF = True
            # Match route-type conditions
            elif statement.conditions.match_evpn_route_type_set:
                BUILD_EVPN_CLAUSE = ""
                evpn_rt_set = statement.conditions.match_evpn_route_type_set
                for evpn_rt in evpn_rt_set.evpn_route_type:
                    # check IF vs OR clause
                    if BUILD_EVPN_CLAUSE == "":
                        BUILD_EVPN_CLAUSE += const.RP_CLI_IF_CLAUSE_CHARS
                    else:
                        BUILD_EVPN_CLAUSE += l2const.RP_CLI_OR_CLAUSE_CHARS
                    # append the evpn value
                    BUILD_EVPN_CLAUSE += l2const.RP_CLI_EVPN_RT_CLAUSE_CHARS\
                        + l2const.RP_CLI_IS_CLAUSE_CHARS\
                        + str(evpn_rt)
                if BUILD_EVPN_CLAUSE != "":
                    FINAL_RP_VALUE += BUILD_EVPN_CLAUSE\
                        + const.RP_CLI_THEN_CLAUSE_CHARS\
                        + const.RP_CLI_IF_THEN_CLAUSE_SPACES
                    # set append endif to true
                    APPEND_ENDIF = True

            # Manual Match - used internally only by IETF NSS and is not user configurable
            elif statement.conditions.match_manual is not None:
                FINAL_RP_VALUE += const.RP_CLI_IF_CLAUSE_CHARS\
                    + f"{statement.conditions.match_manual}"\
                    + const.RP_CLI_THEN_CLAUSE_CHARS\
                    + const.RP_CLI_IF_THEN_CLAUSE_SPACES
                APPEND_ENDIF = True
                APPEND_PASS = True

            # set-extcommunity tag will always be configured
            color_tag = statement.actions.bgp_actions.set_ext_community.tag_value
            if color_tag is not None:
                FINAL_RP_VALUE += const.RP_CLI_SET_CLAUSE_CHARS\
                    + f"extcommunity color COLOR_{color_tag}"\
                    + const.RP_CLI_END_STMNT
                if APPEND_ENDIF:
                    FINAL_RP_VALUE += const.RP_CLI_ENDIF_CLAUSE_CHARS\
                        + const.RP_CLI_END_STMNT
                if APPEND_PASS:
                    FINAL_RP_VALUE = self.begin_new_stmnt(FINAL_RP_VALUE)\
                        + "pass" + const.RP_CLI_END_STMNT

        return FINAL_RP_VALUE

    def begin_new_stmnt(self, FINAL_RP_VALUE):
        # in CLI we always begin policy with 2 spaces
        FINAL_RP_VALUE += const.RP_CLI_BEGIN_STMNT
        return FINAL_RP_VALUE

    def conf_l2vpn_rp(self, rr_parent_route_policy):
        self.log.info("Configuring Route Policy on IOSXR for service "
                      f"{rr_parent_route_policy.name} on {rr_parent_route_policy.device}")
        # Build parent route policy blob by applying local route policy names
        parent_rp_blob = ""
        # Iterate over all local route policies
        for local_route_policy in rr_parent_route_policy.local_route_policy:
            # Apply local route policy name in parent route policy blob
            parent_rp_blob += const.RP_CLI_BEGIN_STMNT\
                + f"apply {local_route_policy}"\
                + const.RP_CLI_END_STMNT
        # Append original parent route policy definition
        if rr_parent_route_policy.original_rr_route_policy:
            parent_rp_blob += str(rr_parent_route_policy.original_rr_route_policy)
        # Configure parent route policy
        rp_vars = ncs.template.Variables()
        rp_vars.add("POLICY_BLOB", parent_rp_blob)
        rp_template = ncs.template.Template(rr_parent_route_policy)
        rp_template.apply("cisco-flat-L2vpn-fp-parent-route-policy-iosxr-cli", rp_vars)

    def validate_parent_policy_exists(self, root, device, parent_policy):
        device = root.devices.device[device]
        # Check if parent_policy exists on device
        if parent_policy in device.config.route_policy:
            return True
        return False

    def get_original_policy(self, root, device, parent_policy):
        # Return route policy value
        return root.devices.device[device].config.route_policy[parent_policy].value

    def check_if_interface_exists(self, root, site, service_interface_name, service_interface_id):
        service_interface = service_interface_name + service_interface_id
        self.log.info(f"Checking {service_interface} on IOSXR device {site.pe}")

        device_interface = root.devices.device[site.pe].config.cisco_ios_xr__interface
        device_interfaces = getattr(device_interface,
                                    service_interface_name.replace("-", "_"), None)

        if device_interfaces:
            for interface in device_interfaces:
                if service_interface == service_interface_name + str(interface.id):
                    return True

        # CSCvt12530 - In case interface is no shut on the device, it won't show up
        # on running-config. We need a live-status check.
        admin_status = root.devices.device[site.pe].live_status.if__interfaces_state.\
            interface[service_interface].admin_status

        if admin_status is None:
            return False
        else:
            return True

    def get_interface_shutdown_template(self):
        return "cisco-flat-L2vpn-fp-no-shutdown-iosxr-cli"

    def l2vpn_self_test(self, root, service, device, xc_group, xc_name):
        self.log.info(f"Running L2vpn self test on IOSXR device {device}")
        # If netsim return success
        if is_netsim_device(self, root, device):
            return ("success", "netsim")
        else:
            # ping vrf src -> dest
            self_test_command = ("show l2vpn xconnect group " + xc_group
                                 + " xc-name " + xc_name + " detail")

            # Execute self test
            action = root.devices.device[device].live_status.cisco_ios_xr_stats__exec.any
            input = action.get_input()
            input.args.create(self_test_command)
            return self.run_self_test(action, input, service, device)

    def run_self_test(self, action, input, service, device):
        max_retries = 2
        for retry in range(max_retries):
            try:
                output = action(input)
                self.log.info(f"L2vpn Self Test result: {output.result}")

                find = "EVPN: neighbor"
                if service.service_type == "p2p":
                    find = "PW: neighbor"
                output_data = ""
                for item in output.result.split("\n"):
                    if find in item:
                        output_data = item.strip()
                        break
                self.log.info(f"L2vpn Self Test result data: {output_data}")

                if "state is up" in output_data:
                    return ("success", "success")
                if "state is down" in output_data:
                    return ("failed", "state is down")
                else:
                    return ("failed", f"Unexpected result: {output.result}")
            except Exception as e:
                if "Connection reset in new state" in str(e) and retry == (max_retries - 1):
                    self.log.info("Connection reset on device, "
                                  f"reached max-retries for: {service.name}")
                    return (
                        "failed", "Device ssh session being used by another transaction. "
                        + "Retry self-test with following command: "
                        + "'request flat-L2vpn " + service.name + " action self-test'",
                    )
                elif "Connection reset in new state" in str(e):
                    self.log.info("Connection reset on device, will "
                                  f"retry self test for: {service.name}")
                else:
                    self.log.exception(e)
                    return ("failed", str(e))
            time.sleep(30)
            self.log.info(f"Retrying self test for: {service.name}")

    def __init__(self, log, root, service):
        self.log = log
        self.root = root
        self.service = service
