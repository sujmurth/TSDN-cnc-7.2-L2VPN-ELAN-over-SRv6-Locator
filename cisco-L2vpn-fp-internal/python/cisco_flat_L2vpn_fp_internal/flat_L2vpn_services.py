import _ncs
import ncs

from abc import abstractmethod
from cisco_tsdn_core_fp_common import ietf_L2vpn_nm_const as constants
from cisco_tsdn_core_fp_common.status_codes.flat_L2vpn_status_codes import StatusCodes
from cisco_tsdn_core_fp_common.status_codes.flat_L2vpn_cfp_base_exception import (
    UserErrorException
)
from cisco_tsdn_core_fp_common.diff_iterate_wrapper import DiffIterateWrapper
from . import utils as Utils


class FlatL2vpnServices(ncs.application.Service):

    @abstractmethod
    def cb_pre_modification(self, tctx, op, kp, root, proplist):
        pass

    @abstractmethod
    def cb_post_modification(self, tctx, op, kp, root, proplist):
        pass

    def l2vpn_pre_modification(self, site_type, tctx, op, kp, root, proplist):
        opaque = dict(proplist)
        opaque["VALIDATION_ERROR"] = ""
        try:
            # If op is create, validate status code mapping is loaded
            status_code_cfp = root.cfp_common_status_codes__status_codes.core_function_pack
            if op == _ncs.dp.NCS_SERVICE_CREATE and not status_code_cfp.exists("L2VPN"):
                raise UserErrorException(
                    self.log, StatusCodes.STATUS_CODE_NOT_LOADED
                ).set_context(
                    "Status Code", "Missing L2VPN status code mapping"
                ).add_state(
                    "Keypath", str(kp)
                ).finish()

            localhost = "127.0.0.1"  # NOSONAR
            # if operation is create or update, check interfaces on device & validate
            if (op == _ncs.dp.NCS_SERVICE_CREATE) or (op == _ncs.dp.NCS_SERVICE_UPDATE):
                service = ncs.maagic.get_node(root, kp)
                site = self._get_site(site_type, service)

                self.log.info(f"Pre-Mod for service: {service.name} , operation: {op}")

                l2vpn_validation_enabled = root.\
                    cisco_flat_L2vpn_fp_internal_common__cfp_configurations.\
                    l2vpn_validation_enabled

                opaque["DEVICE_TRANS_INVALIDATED"] = "false"
                if op == _ncs.dp.NCS_SERVICE_UPDATE:
                    device_modified = self.diff_iterate(service).device_modified

                    if not device_modified:
                        # Check if device invalidated
                        if ("INVALIDATED" == root.ncs__devices.device[site.pe].state
                                .last_transaction_id):
                            opaque["DEVICE_TRANS_INVALIDATED"] = "true"
                else:
                    device_modified = True

                self.log.info(f"Pre-Mod for {site_type} device is modified: {device_modified}")
                self.log.info(f"L2VPN {site_type} pre_mod internal Opaque: {opaque}")

                if service.service_type == "evpn-vpws" or service.service_type == "evpn-multipoint":
                    # Update or generate new entry for l2vpn-rr-parent-route-policy Service
                    # Get attach-point
                    if (site.sr_te.exists() and site.sr_te.odn.exists()):
                        parent_rr_route_policy = site.sr_te.odn.attach_point.parent_rr_route_policy

                        if parent_rr_route_policy:
                            # Get device impl class
                            device = site.pe
                            device_impl_list = root.\
                                cisco_flat_L2vpn_fp_internal_common__cfp_configurations.\
                                dynamic_device_mapping

                            device_impl_class = Utils.\
                                get_device_impl_default_class(
                                    self,
                                    root,
                                    service,
                                    device,
                                    device_impl_list
                                )
                            # Create/Update l2vpn-rr-parent-route-policy
                            Utils.create_parent_route_policy_service(
                                self,
                                str(parent_rr_route_policy),
                                root,
                                device,
                                device_impl_class
                            )

                            # Store l2vpn-rr-parent-route-policy key in proplist for use in post-mod
                            opaque["PARENT_RP_KEY"] = f"{str(parent_rr_route_policy)} {device}"

                if device_modified and l2vpn_validation_enabled:
                    if (root.devices.device[site.pe].address != localhost
                            and site.if_type != "Loopback"):
                        router = Utils.get_device_impl_default_class(
                            self, root, service, site.pe,
                            root.cisco_flat_L2vpn_fp_internal_common__cfp_configurations
                            .dynamic_device_mapping
                        )
                        service_interface = str(site.if_type) + str(site.if_id)
                        try:
                            if not router.check_if_interface_exists(root, site, str(site.if_type),
                                                                    str(site.if_id)):
                                user_error_exception = UserErrorException(
                                    self.log, StatusCodes.INTERFACE_NOT_FOUND
                                ).set_context(
                                    "Interface Validation",
                                    f"Provided interface not present on {site_type}",
                                ).add_state(
                                    "Service", service.name
                                )

                                if site_type == constants.SITE:
                                    user_error_exception = user_error_exception.add_state(
                                        "Site", service.site_name
                                    )

                                user_error_exception = user_error_exception.add_state(
                                    "Interface", service_interface
                                ).add_state(
                                    "Device", site.pe
                                )

                                raise user_error_exception.finish()
                        except AttributeError as e:
                            user_error_exception = UserErrorException(
                                self.log, StatusCodes.DYNAMIC_METHOD_NOT_FOUND, str(e)
                            ).set_context(
                                "Dynamic Method Error",
                                "check_if_interface_exists method is missing "
                                "from multi-vendor python class",
                            ).add_state(
                                "Service", service.name
                            )

                            if site_type == constants.SITE:
                                user_error_exception = user_error_exception.add_state(
                                    "Site", service.site_name
                                )
                            elif site_type == constants.LOCAL_SITE:
                                user_error_exception = user_error_exception.add_state(
                                    "Local Site", service.pe
                                )
                            elif site_type == constants.REMOTE_SITE:
                                user_error_exception = user_error_exception.add_state(
                                    "Remote Site", service.pe
                                )
                            else:
                                raise AttributeError(f"Unable to identify site-type = {site_type}")

                            raise user_error_exception.finish()

        except Exception as e:
            self.log.exception(e)
            opaque["VALIDATION_ERROR"] = str(e)

        return list(opaque.items())

    def _get_site(self, site_type, service):
        service_type = service.service_type

        if service_type == constants.P2P:
            return self._get_site_internal(
                site_type,
                service.flat_L2vpn_p2p
            )
        elif service_type == constants.EVPN_VPWS:
            return self._get_site_internal(
                site_type,
                service.flat_L2vpn_evpn_vpws
            )
        elif service_type == constants.EVPN_MULTIPOINT:
            return self._get_site_internal(
                site_type,
                service.flat_L2vpn_evpn_multipoint,
                service.site_name
            )
        else:
            raise AttributeError(f"Unable to identify service-type = {service_type}")

    def _get_site_internal(self, site_type, service_with_type, site_name=None):
        if site_type == constants.LOCAL_SITE:
            return service_with_type.local_site
        elif site_type == constants.REMOTE_SITE:
            return service_with_type.remote_site
        elif site_type == constants.SITE:
            return service_with_type.site[site_name]
        else:
            raise AttributeError(f"Unable to identify site-type = {site_type}")

    def diff_iterate(self, service) -> DiffIterateWrapper:
        # Possible service._paths:
        # {service._path} = /flat-L2vpn-internal-site-service{name site-name}
        # {service._path} = /flat-L2vpn-internal-local-site-service{name pe}
        # {service._path} = /flat-L2vpn-internal-remote-site-service{name pe}

        # Device is modified if the followings paths are updated:
        # {service._path}/custom-template
        # {service._path}/flat-L2vpn-p2p
        # {service._path}/flat-L2vpn-evpn-vpws
        # {service._path}/flat-L2vpn-evpn-multipoint

        # Ignore service-assurance
        # {service._path}/service-assurance

        def diter(self, keypath, op, oldv, newv):
            if len(keypath) < 3:
                return ncs.ITER_RECURSE

            kp_3 = str(keypath[-3])

            if kp_3 == "custom-template" \
                or kp_3 == "flat-L2vpn-p2p" \
                or kp_3 == "flat-L2vpn-evpn-vpws" \
                    or kp_3 == "flat-L2vpn-evpn-multipoint":
                self.device_modified = True

                return ncs.ITER_STOP

            return ncs.ITER_CONTINUE

        diff_iter = DiffIterateWrapper(diter, device_modified=False)

        th = ncs.maagic.get_trans(service)
        th.keypath_diff_iterate(diff_iter, 0, service._path)

        return diff_iter

    def cleanup_parent_rp(self, op, opaque, root):
        # If op is DELETE or UPDATE, cleanup l2vpn-rr-parent-route-policy if there are no more
        # references
        if op == _ncs.dp.NCS_SERVICE_DELETE or op == _ncs.dp.NCS_SERVICE_UPDATE:
            # Grab Parent RP key from opaque
            parent_rp_key = opaque.get("PARENT_RP_KEY", "")
            if parent_rp_key:
                # Define path
                parent_rp_kp = f"/l2vpn-rr-parent-route-policy{{{parent_rp_key}}}"
                th = ncs.maagic.get_trans(root)
                try:
                    # Cleanup Parent RP Entry if there are no more local-route-policies defined
                    if th.exists(parent_rp_kp):
                        # Check if parent rp service has any local route policies defined
                        parent_rp_node = ncs.maagic.get_node(th, parent_rp_kp)
                        if len(parent_rp_node.local_route_policy) == 0:
                            self.log.info("Parent RP has no local-route-policy definitions, "
                                          "cleaning up")
                            # Delete parent route policy
                            th.delete(parent_rp_kp)
                except Exception as e:
                    # TODO : Raise alarm when cleanup fails, Python API does not support user alarms
                    self.log.exception(e)
