'''
zstack vm test class

@author: Youyk
'''
import zstackwoodpecker.header.vm as vm_header
import zstackwoodpecker.operations.vm_operations as vm_ops
import zstackwoodpecker.operations.net_operations as net_ops
import zstackwoodpecker.test_util as test_util
import zstackwoodpecker.test_lib as test_lib

class ZstackTestVm(vm_header.TestVm):
    def __init__(self):
        self.vm_creation_option = test_util.VmOption()
        super(ZstackTestVm, self).__init__()

    def __hash__(self):
        return hash(self.vm.uuid)

    def __eq__(self, other):
        return self.vm.uuid == other.vm.uuid

    def create(self):
        self.vm = vm_ops.create_vm(self.vm_creation_option)
        super(ZstackTestVm, self).create()

    def destroy(self):
        vm_ops.destroy_vm(self.vm.uuid)
        super(ZstackTestVm, self).destroy()

    def start(self):
        self.vm = vm_ops.start_vm(self.vm.uuid)
        super(ZstackTestVm, self).start()

    def stop(self):
        self.vm = vm_ops.stop_vm(self.vm.uuid)
        super(ZstackTestVm, self).stop()

    def reboot(self):
        self.vm = vm_ops.reboot_vm(self.vm.uuid)
        super(ZstackTestVm, self).reboot()

    def migrate(self, host_uuid):
        self.vm = vm_ops.migrate_vm(self.vm.uuid, host_uuid)
        super(ZstackTestVm, self).migrate(host_uuid)

    def check(self):
        import zstackwoodpecker.zstack_test.checker_factory as checker_factory
        checker = checker_factory.CheckerFactory().create_checker(self)
        checker.check()
        super(ZstackTestVm, self).check()

    def set_creation_option(self, vm_creation_option):
        self.vm_creation_option = vm_creation_option

    def get_creation_option(self):
        return self.vm_creation_option

    def update(self):
        '''
        If vm's status was changed by none vm operations, it needs to call
        vm.update() to update vm's infromation. 

        The none vm operations: host.maintain() host.delete(), zone.delete()
        cluster.delete()
        '''
        super(ZstackTestVm, self).update()
        if self.get_state != vm_header.DESTROYED:
            updated_vm = test_lib.lib_get_vm_by_uuid(self.vm.uuid)
            if updated_vm:
                self.vm = updated_vm
                #vm state need to chenage to stopped, if host is deleted
                host = test_lib.lib_find_host_by_vm(updated_vm)
                if not host and self.vm.state == vm_header.STOPPED:
                    self.set_state(vm_header.STOPPED)
            else:
                self.set_state(vm_header.DESTROYED)
            return self.vm
