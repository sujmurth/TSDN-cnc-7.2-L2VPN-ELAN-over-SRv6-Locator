# -*- mode: python; python-indent: 4 -*-
import logging
import ncs
from ncs import maagic

from . import utils as Utils
from .flat_L2vpn_services import FlatL2vpnServices
from cisco_tsdn_core_fp_common import ietf_L2vpn_nm_const as constants
from cisco_tsdn_core_fp_common.status_codes.flat_L2vpn_status_codes import StatusCodes
from cisco_tsdn_core_fp_common.status_codes.flat_L2vpn_cfp_base_exception import (
    UserErrorException, ServiceException,
    DeviceConfigException, CustomTemplateException
)
from cisco_tsdn_core_fp_common import utils as TsdnUtils
from core_fp_common import instrumentation


class FlatL2vpnValidator(object):
    def __init__(self, log):
        self.log = log

    def cb_validate(self, tctx, kp, newval):
        return TsdnUtils.validate_service(self, Utils.remote_site_validation_callpoint, tctx, kp)


class FlatL2vpnCallBack(FlatL2vpnServices):
    @ncs.application.Service.pre_modification
    @instrumentation.instrument_service(logging.INFO, Utils.remote_site_servicepoint)
    def cb_pre_modification(self, tctx, op, kp, root, proplist):
        return self.l2vpn_pre_modification(constants.REMOTE_SITE, tctx, op, kp, root, proplist)

    @ncs.application.Service.post_modification
    @instrumentation.instrument_service(logging.INFO, Utils.remote_site_servicepoint)
    def cb_post_modification(self, tctx, op, kp, root, proplist):
        opaque = dict(proplist)
        self.cleanup_parent_rp(op, opaque, root)


class FlatL2vpnSelfCallBack(ncs.application.NanoService):

    """
    NanoService callback handler for flat-L2vpn service remote-site
    """

    @ncs.application.NanoService.create
    @instrumentation.instrument_nano(logging.INFO, Utils.remote_site_servicepoint)
    def cb_nano_create(self, tctx, root, service, plan, component, state, opaque, comp_vars):
        opaque_dict = dict(opaque)
        if opaque_dict.get("VALIDATION_ERROR") != "":
            return list(opaque_dict.items())

        try:
            new_opaque = None
            if state == "cisco-flat-L2vpn-fp-remote-site-nano-services:config-apply":
                new_opaque = self._create_config_apply(tctx, root, service, plan,
                                                       component, state, opaque, comp_vars)
            elif state == "ncs:ready":
                new_opaque = self._create_ready(tctx, root, service, plan,
                                                component, state, opaque, comp_vars)
            if new_opaque is None:
                return opaque

            return new_opaque

        except Exception as e:
            self.log.exception(e)
            opaque_dict["VALIDATION_ERROR"] = str(e)
            return list(opaque_dict.items())

    def _create_config_apply(self, tctx, root, service, plan, component, state, opaque, comp_vars):
        if service.service_type == "p2p":
            site = service.flat_L2vpn_p2p.remote_site
        else:
            site = service.flat_L2vpn_evpn_vpws.remote_site
            # Configure parent rr route policy service with local route policy
            Utils.config_parent_route_policy_service(self, site)

        try:
            router = Utils.get_device_impl_default_class(
                self, root, service, site.pe,
                root.cisco_flat_L2vpn_fp_internal_common__cfp_configurations
                .dynamic_device_mapping
            )
        except UserErrorException:
            raise
        except Exception as e:
            raise ServiceException(
                self.log, StatusCodes.DYNAMIC_CLASS_NOT_FOUND, str(e)
            ).set_context(
                "Dynamic Device Mapping", "Error retrieving Dynamic Device class"
            ).add_state(
                "Device", site.pe
            ).add_state(
                "Service", service.name
            ).finish()

        try:
            try:
                router.conf_l2vpn(site, False)
            except AttributeError as e:
                raise UserErrorException(
                    self.log, StatusCodes.DYNAMIC_METHOD_NOT_FOUND, str(e)
                ).set_context(
                    "Dynamic Method Error",
                    "conf_l2vpn method is missing from multi-vendor python class",
                ).add_state(
                    "Remote Site", site.pe
                ).add_state(
                    "Service", service.name
                ).finish()

            try:
                template_name = router.get_interface_shutdown_template()
                if template_name:
                    shutdown_service = root.\
                        core_fp_delete_tag_service__core_fp_delete_shutdown_service.\
                        create(site.pe, site.if_type, site.if_id)
                    shutdown_service.template_name = template_name
            except AttributeError as e:
                raise UserErrorException(
                    self.log, StatusCodes.DYNAMIC_METHOD_NOT_FOUND, str(e)
                ).set_context(
                    "Dynamic Method Error", "get_interface_shutdown_template method \
                    is missing from multi-vendor python class",
                ).add_state(
                    "Remote Site", site.pe
                ).add_state(
                    "Service", service.name
                ).finish()

        except UserErrorException:
            raise
        except Exception as e:
            raise DeviceConfigException(
                self.log, StatusCodes.CONFIG_FAILURE, str(e)
            ).set_context(
                "Configuration Error", "Could not apply service config on remote site"
            ).add_state(
                "Remote Site", site.pe
            ).add_state(
                "Service", service.name
            ).finish()

        # Apply custom-template from global level
        if service.custom_template:
            TsdnUtils.apply_custom_template(self, root, service, service.pe,
                                            StatusCodes.CUSTOM_TEMPLATE_ERROR,
                                            CustomTemplateException)

        # Apply custom-template at site level
        if site.custom_template:
            TsdnUtils.apply_custom_template(self, root, site, site.pe,
                                            StatusCodes.CUSTOM_TEMPLATE_ERROR,
                                            CustomTemplateException)

        return opaque

    def _create_ready(self, _tctx, root, service, plan, component, state, opaque, comp_vars):

        trans = maagic.get_trans(root)
        trans_params = trans.get_params()

        state_node = plan.component[component].state[state]
        opaque = dict(opaque)
        # Check if device transaction state is invalidated and no-networking is not used,
        # if so abort transaction
        if "true" == opaque.get("DEVICE_TRANS_INVALIDATED") and not trans_params.is_no_networking():
            raise DeviceConfigException(
                self.log, StatusCodes.DEVICE_INVALIDATED_ERROR
            ).set_context(
                "Device Error", "Device Transaction for service is invalidated"
            ).add_state(
                "Service", service.name
            ).add_state(
                "Device", service.pe
            ).finish()

        # Update timestamp for CQ service updates (with no device change) to re-deploy NB service to
        # mark plan reached
        TsdnUtils.update_state_when_timestamp(self, component, state_node, "from internal plan")

        return list(opaque.items())
