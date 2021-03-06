import zstackwoodpecker.operations.resource_operations as res_ops
import zstackwoodpecker.header.checker as checker_header
import zstackwoodpecker.header.vm as vm_header
import zstackwoodpecker.header.security_group as sg_header
import zstackwoodpecker.test_util as test_util
import apibinding.inventory as inventory

import sys
import traceback

class zstack_vm_db_checker(checker_header.TestChecker):
    def check(self):
        super(zstack_vm_db_checker, self).check()
        vm = self.test_obj.vm
        conditions = res_ops.gen_query_conditions('uuid', '=', vm.uuid)
        vm_in_db = res_ops.query_resource(res_ops.VM_INSTANCE, conditions)
        if not vm_in_db:
            test_util.test_logger('Check result: can NOT find [vm:] %s in Database.' % vm.uuid)
            return self.judge(False)
        if (vm_in_db[0].state == inventory.RUNNING and self.test_obj.state == vm_header.RUNNING) or (vm_in_db[0].state == inventory.STOPPED and self.test_obj.state == vm_header.STOPPED) or (vm_in_db[0].state == inventory.DESTROYED and self.test_obj.state == vm_header.DESTROYED):
            #vm state sync is default pass. so didn't print the infomation by default
            #test_util.test_logger('Check result: [vm:] %s status is synced with Database.' % vm.uuid)
            return self.judge(True)
        else:
            test_util.test_logger('Check result: [vm:] %s [status:] %s is NOT synced with [Database:] %s.' % (vm.uuid, self.test_obj.state, vm_in_db[0].state))
            return self.judge(False)

class zstack_image_db_checker(checker_header.TestChecker):
    '''check image existence in database. If it is in db, 
        return self.judge(True). If not, return self.judge(False)'''
    def check(self):
        super(zstack_image_db_checker, self).check()
        try:
            conditions = res_ops.gen_query_conditions('uuid', '=', self.test_obj.image.uuid)
            image = res_ops.query_resource(res_ops.IMAGE, conditions)[0]
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            test_util.test_logger('Check result: [imageInventory uuid:] %s does not exist in database.' % self.test_obj.image.uuid)
            return self.judge(False)

        test_util.test_logger('Check result: [imageInventory uuid:] %s exist in database.' % image.uuid)
        return self.judge(True)

class zstack_volume_db_checker(checker_header.TestChecker):
    '''check volume existence in database. If it is in db, 
        return self.judge(True). If not, return self.judge(False)'''
    def check(self):
        super(zstack_volume_db_checker, self).check()
        try:
            conditions = res_ops.gen_query_conditions('uuid', '=', self.test_obj.volume.uuid)
            volume = res_ops.query_resource(res_ops.VOLUME, conditions)[0]
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            test_util.test_logger('Check result: [volumeInventory uuid:] %s does not exist in database.' % self.test_obj.volume.uuid)
            return self.judge(False)

        test_util.test_logger('Check result: [volumeInventory uuid:] %s exist in database.' % volume.uuid)
        return self.judge(True)


class zstack_volume_attach_db_checker(checker_header.TestChecker):
    '''
        Check if volume attached relationship with vm is correct in DB.
    '''
    def check(self):
        super(zstack_volume_attach_db_checker, self).check()
        volume = self.test_obj.volume
        if not volume.vmInstanceUuid:
            test_util.test_logger('Check result: test [volume:] %s does NOT record any vmInstanceUuid. It is not attached to any vm yet.' % volume.uuid)
            return self.judge(False)

        try:
            conditions = res_ops.gen_query_conditions('uuid', '=', self.test_obj.volume.uuid)
            db_volume = res_ops.query_resource(res_ops.VOLUME, conditions)[0]
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            test_util.test_logger('Check result: [volumeInventory uuid:] %s does not exist in database.' % self.test_obj.volume.uuid)
            return self.judge(False)

        if not db_volume.vmInstanceUuid:
            #update self.test_obj, due to vm destroyed. 
            if self.test_obj.target_vm.state == vm_header.DESTROYED:
                test_util.test_warn('Update test [volume:] %s state, since attached VM was destroyed.' % volume.uuid)
                self.test_obj.update()
            else:
                test_util.test_warn('Check warn: [volume:] %s state is not aligned with DB. DB did not record any attached VM, but test volume has attached vm record: %s.' % (volume.uuid, volume.vmInstanceUuid))
            test_util.test_logger('Check result: [volume:] %s does NOT have vmInstanceUuid in Database. It is not attached to any vm.' % volume.uuid)
            return self.judge(False)

        if not self.test_obj.target_vm:
            test_util.test_logger('Check result: test [volume:] %s does NOT have vmInstance record in test structure. Can not do furture checking.' % volume.uuid)
            return self.judge(False)

        vm = self.test_obj.target_vm.vm

        if db_volume.vmInstanceUuid == vm.uuid:
            test_util.test_logger('Check result: [volume:] %s is attached to [vm:] %s in zstack database.' % (volume.uuid, vm.uuid))
            return self.judge(True)
        else:
            test_util.test_logger('Check result: [volume:] %s is NOT attached to [vm:] %s in zstack database.' % (volume.uuid, vm.uuid))
            return self.judge(False)

class zstack_sg_db_checker(checker_header.TestChecker):
    '''check sg state in database. If its state is aligned with db record,
        return self.judge(True). If not, return self.judge(False)'''
    def _check_sg_exist(self, test_sg):
        try:
            conditions = res_ops.gen_query_conditions('uuid', '=', test_sg.security_group.uuid)
            sg = res_ops.query_resource(res_ops.SECURITY_GROUP, conditions)[0]
        except Exception as e:
            test_util.test_logger('Check result: [SG uuid:] %s does not exist in database.' % test_sg.security_group.uuid)
            if test_sg.state == sg_header.DELETED:
                return self.judge(True)
            else:    
                traceback.print_exc(file=sys.stdout)
                return self.judge(False)

        test_util.test_logger('Check result: [SG uuid:] %s is found in database.' % test_sg.security_group.uuid)
        if test_sg.state == sg_header.DELETED:
            test_util.test_warn('[SG uuid:] %s should not be found in database, since it is deleted.' % test_sg.security_group.uuid)
            return self.judge(False)

        rules = sg.rules
        test_rules = test_sg.get_all_rules()
        rule_id_list = []
        for rule in rules:
            rule_id_list.append(rule.uuid)

        if len(rules) != len(test_rules):
            test_util.test_warn('[SG uuid:] %s rules number: %s  is not aligned with the record: %s in DB.' % (test_sg.security_group.uuid, len(test_rules), len(rules)))
            return self.judge(False)

        for rule in test_rules:
            if not rule.uuid in rule_id_list:
                test_util.test_warn('[SG uuid:] %s rule: %s  is not found in DB.' % (test_sg.security_group.uuid, rule.uuid))
                return self.judge(False)

        test_util.test_logger('Check result: [SG uuid:] %s rules are all found in database.' % test_sg.security_group.uuid)
        return self.judge(True)

    def check(self):
        super(zstack_sg_db_checker, self).check()
        for test_sg in self.test_obj.get_all_sgs():
            self._check_sg_exist(test_sg)

