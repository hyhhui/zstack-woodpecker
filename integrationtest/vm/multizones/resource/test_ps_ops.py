'''

Test primary storage detach, delete and add operations in single test.

@author: Youyk
'''

import zstackwoodpecker.test_util as test_util
import zstackwoodpecker.test_state as test_state
import zstackwoodpecker.test_lib as test_lib
import zstackwoodpecker.header.vm as vm_header
import zstackwoodpecker.header.volume as vol_header
import zstackwoodpecker.operations.resource_operations as res_ops
import zstackwoodpecker.operations.export_operations as exp_ops
import zstackwoodpecker.operations.tag_operations as tag_ops
import zstackwoodpecker.operations.primarystorage_operations as ps_ops
import time
import os

_config_ = {
        'timeout' : 1200,
        'noparallel' : True
        }

test_stub = test_lib.lib_get_test_stub()
test_obj_dict = test_state.TestStateDict()
tag = None
ps_uuid = None
cluster_uuid = None
ps_inv = None

def recover_ps():
    global ps_inv
    ps_config = test_util.PrimaryStorageOption()

    ps_config.set_name(ps_inv.name)
    ps_config.set_description(ps_inv.description)
    ps_config.set_zone_uuid(ps_inv.zoneUuid)
    ps_config.set_type(ps_inv.type)
    ps_config.set_url(ps_inv.url)

    #avoid of ps is already created successfully. 
    cond = res_ops.gen_query_conditions('zoneUuid', '=', ps_inv.zoneUuid)
    cond = res_ops.gen_query_conditions('url', '=', ps_inv.url, cond)
    curr_ps = res_ops.query_resource(res_ops.PRIMARY_STORAGE, cond)
    if curr_ps:
        ps = curr_ps[0]
    else:
        ps = ps_ops.create_nfs_primary_storage(ps_config)

    for cluster_uuid in ps_inv.attachedClusterUuids:
        ps_ops.attach_primary_storage(ps.uuid, cluster_uuid)

def test():
    global ps_inv
    global ps_uuid
    global cluster_uuid
    global tag
    curr_deploy_conf = exp_ops.export_zstack_deployment_config(test_lib.deploy_config)

    vm_creation_option = test_util.VmOption()
    image_name = os.environ.get('imageName_s')
    image_uuid = test_lib.lib_get_image_by_name(image_name).uuid
    #pick up primary storage 1 and set system tag for instance offering.
    ps_name1 = os.environ.get('nfsPrimaryStorageName1')
    ps_inv = res_ops.get_resource(res_ops.PRIMARY_STORAGE, name = ps_name1)[0]
    ps_uuid = ps_inv.uuid

    conditions = res_ops.gen_query_conditions('type', '=', 'UserVm')
    instance_offering_uuid = res_ops.query_resource(res_ops.INSTANCE_OFFERING, \
            conditions)[0].uuid
    vm_creation_option.set_image_uuid(image_uuid)
    vm_creation_option.set_instance_offering_uuid(instance_offering_uuid)
    vm_creation_option.set_name('multizones_vm_ps_ops')

    tag = tag_ops.create_system_tag('InstanceOfferingVO', \
            instance_offering_uuid, \
            'primaryStorage::allocator::uuid::%s' % ps_uuid)

    l3_name = os.environ.get('l3VlanNetworkName1')
    l3 = res_ops.get_resource(res_ops.L3_NETWORK, name = l3_name)[0]
    vm_creation_option.set_l3_uuids([l3.uuid])

    vm1 = test_lib.lib_create_vm(vm_creation_option)
    test_obj_dict.add_vm(vm1)

    cluster_uuid = vm1.get_vm().clusterUuid

    test_util.test_dsc("Detach Primary Storage")
    ps_ops.detach_primary_storage(ps_uuid, cluster_uuid)

    test_obj_dict.mv_vm(vm1, vm_header.RUNNING, vm_header.STOPPED)
    vm1.update()
    vm1.set_state(vm_header.STOPPED)

    vm1.check()

    vm1.start()

    vm2 = test_lib.lib_create_vm(vm_creation_option)
    test_obj_dict.add_vm(vm2)
    
    test_util.test_dsc("Delete Primary Storage")
    tag_ops.delete_tag(tag.uuid)
    ps_ops.delete_primary_storage(ps_inv.uuid)

    test_obj_dict.mv_vm(vm1, vm_header.RUNNING, vm_header.DESTROYED)
    vm1.set_state(vm_header.DESTROYED)
    vm1.check()

    test_obj_dict.mv_vm(vm2, vm_header.RUNNING, vm_header.DESTROYED)
    vm2.set_state(vm_header.DESTROYED)
    vm2.check()

    try:
        vm3 = test_lib.lib_create_vm(vm_creation_option)
    except:
        test_util.test_logger('Catch expected vm creation exception, since primary storage has been deleted. ')
    else:
        test_util.test_fail('Fail: Primary Storage has been deleted. But vm is still created with it.')

    recover_ps()
    test_util.test_dsc("Attach Primary Storage")

    test_lib.lib_robot_cleanup(test_obj_dict)
    test_util.test_pass('Test primary storage operations Success')

#Will be called only if exception happens in test().
def error_cleanup():
    global tag
    global ps_uuid
    global cluster_uuid
    try:
        ps_ops.attach_primary_storage(ps_uuid, cluster_uuid)
    except:
        recover_ps()

    try:
        tag_ops.delete_tag(tag.uuid)
    except:
        pass

    test_lib.lib_error_cleanup(test_obj_dict)
