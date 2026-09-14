#!/usr/bin/env python3
"""Loop until a free-tier Oracle ARM instance is granted, then stop.

Runs from the laptop (clean residential IP). Uses ~/.oci/config for auth.
Started once at logon by a Windows scheduled task; loops forever on its own.
"""
import time
import datetime
import pathlib
import oci

TENANCY = "ocid1.tenancy.oc1..aaaaaaaa3mtrn6tvsmwk77iimdn2ke2pslexvx6xbhj7vnjwtoxylqehvi5a"
AD = "wdGy:AP-HYDERABAD-1-AD-1"
SUBNET = "ocid1.subnet.oc1.ap-hyderabad-1.aaaaaaaacek3cl36vknbljpxdm7xeyuexaxaj5x453g7wqcnxfr73nvjbmrq"
SSH_KEY = (
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCr26fzO8Lgy8Ruorsj5jx8eQ/LL/BgdxYnFxdY2C4uyqYHyShYjnhX"
    "YLmV+eHa7zp0AzN1FaMjcJRkysIAqYBW6ooE2R+5SPF2SWUiSV6fRJ0KR5xHrYEDeaYyfOLZwVQS8zxCKBUms7m86MlU"
    "BdGUUr6hjc47u1oOHDXQL+hG4mwrDnq77my1NOTcKsxopMD8KLOS94kCOMFQAjNM+n1cMCw0ekY9sgIHRZRykMTpWhEy"
    "Q6QueDFKeNBk9FEWLV7SNmKueAf+9bGIgfx5UE7xTHProtZ7OmL0eyccd75xC1Gz2OXI5NKhhKQXXpTTGbfrNmjch4fE"
    "nakJ7zWgUe0V ssh-key-2026-09-07"
)
SIZES = [(1, 6)]   # OCPU, GB — smallest shape only: best odds of fitting fragmented capacity
GAP = 90                              # seconds between attempts (proven safe rate)
RATE_LIMIT_SLEEP = 200                # extra wait after a 429

LOG = pathlib.Path.home() / "oci_hunt.log"
DONE = pathlib.Path.home() / "oci_hunt_DONE.txt"


def log(msg):
    line = "%s  %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def setup():
    cfg = oci.config.from_file()
    compute = oci.core.ComputeClient(cfg)
    for inst in oci.pagination.list_call_get_all_results(compute.list_instances, TENANCY).data:
        if "A1.Flex" in (inst.shape or "") and inst.lifecycle_state in ("RUNNING", "PROVISIONING", "STARTING"):
            log("already have %s (%s) — done" % (inst.shape, inst.lifecycle_state))
            DONE.write_text(inst.id)
            return None, None
    img = compute.list_images(
        TENANCY, operating_system="Canonical Ubuntu",
        operating_system_version="24.04", shape="VM.Standard.A1.Flex",
        sort_by="TIMECREATED", sort_order="DESC",
    ).data[0].id
    log("image: %s" % img)
    return compute, img


def attempt(compute, img, ocpus, mem):
    details = oci.core.models.LaunchInstanceDetails(
        compartment_id=TENANCY,
        availability_domain=AD,
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=ocpus, memory_in_gbs=mem),
        source_details=oci.core.models.InstanceSourceViaImageDetails(image_id=img),
        create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=SUBNET, assign_public_ip=True),
        metadata={"ssh_authorized_keys": SSH_KEY},
        display_name="free-%dc-%dg" % (ocpus, mem),
    )
    resp = compute.launch_instance(details, retry_strategy=oci.retry.NoneRetryStrategy())
    return resp.data.id


def main():
    if DONE.exists():
        log("DONE flag present — exiting")
        return

    compute = img = None
    while compute is None:
        try:
            compute, img = setup()
            if compute is None:   # already have an instance
                return
        except Exception as e:            # noqa: BLE001 - stay alive through any setup hiccup
            log("setup failed, retry in 60s: %r" % e)
            time.sleep(60)

    i = 0
    while True:
        ocpus, mem = SIZES[i % len(SIZES)]
        i += 1
        try:
            iid = attempt(compute, img, ocpus, mem)
            log("=========  GOT IT: %d OCPU / %d GB  =========" % (ocpus, mem))
            log("instance: %s" % iid)
            DONE.write_text(iid)
            return
        except oci.exceptions.ServiceError as e:
            code, msg = (e.code or ""), (e.message or "")
            if "capacity" in msg.lower():
                log("no capacity   %dc/%dg" % (ocpus, mem))
            elif e.status == 429 or code == "TooManyRequests":
                log("rate limited  %dc/%dg — sleeping %ds" % (ocpus, mem, RATE_LIMIT_SLEEP))
                time.sleep(RATE_LIMIT_SLEEP)
            elif code in ("LimitExceeded", "QuotaExceeded"):
                log("LIMIT: %s — stopping" % msg)
                DONE.write_text("limit: %s" % msg)
                return
            else:
                log("error %s %s: %s" % (e.status, code, msg))
        except Exception as e:            # noqa: BLE001
            log("unexpected: %r" % e)
        time.sleep(GAP)


if __name__ == "__main__":
    main()
