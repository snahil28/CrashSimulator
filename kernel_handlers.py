from tracereplay_python import *
import logging


# This handler assumes that uname cannot fail. The only documented way it can
# fail is if the buffer it is handed is somehow invalid. This code assumes that
# well written programs don't do this.
def uname_entry_handler(syscall_id, syscall_object, pid):
    logging.debug('Entering uname handler')
    args = {x.value.split('=')[0]: x.value.split('=')[1]
            for x in syscall_object.args}
    args = {x.strip('{}'): y.strip('"{}') for x, y in args.iteritems()}
    logging.debug(args)
    address = tracereplay.peek_register(pid, tracereplay.EBX)
    noop_current_syscall(pid)
    tracereplay.populate_uname_structure(pid,
                                         address,
                                         args['sysname'],
                                         args['nodename'],
                                         args['release'],
                                         args['version'],
                                         args['machine'],
                                         args['domainname'])
    apply_return_conditions(pid, syscall_object)


def getrlimit_entry_handler(syscall_id, syscall_object, pid):
    logging.debug('Entering getrlimit handler')
    cmd = syscall_object.args[0].value[0]
    if cmd != 'RLIMIT_STACK':
        raise Exception('Unimplemented getrlimit command {}'.format(cmd))
    addr = tracereplay.peek_register(pid, tracereplay.ECX)
    rlim_cur = syscall_object.args[1].value.strip('{')
    rlim_cur = rlim_cur.split('=')[1]
    if rlim_cur.find('*') == -1:
        raise Exception('Unimplemented rlim_cur format {}'.format(rlim_cur))
    rlim_cur = int(rlim_cur.split('*')[0]) * int(rlim_cur.split('*')[1])
    rlim_max = syscall_object.args[2].value.strip('}')
    rlim_max = rlim_max.split('=')[1]
    if rlim_max != 'RLIM_INFINITY':
        raise Exception('Unlimited rlim_max format {}'.format(rlim_max))
    rlim_max = 0x7fffffffffffffff
    logging.debug('rlim_cur: %s', rlim_cur)
    logging.debug('rlim_max: %x', rlim_max)
    logging.debug('Address: %s', addr)
    noop_current_syscall(pid)
    tracereplay.populate_rlimit_structure(pid, addr, rlim_cur, rlim_max)
    apply_return_conditions(pid, syscall_object)


def ioctl_entry_handler(syscall_id, syscall_object, pid):
    logging.debug('Entering ioctl handler')
    ebx = tracereplay.peek_register(pid, tracereplay.EBX)
    ecx = tracereplay.peek_register(pid, tracereplay.ECX)
    edx = tracereplay.peek_register(pid, tracereplay.EDX)
    edi = tracereplay.peek_register(pid, tracereplay.EDI)
    esi = tracereplay.peek_register(pid, tracereplay.ESI)
    logging.debug('ebx: %x', ebx)
    logging.debug('ecx: %x', ecx)
    logging.debug('edx: %x', edx)
    logging.debug('edi: %x', edi)
    logging.debug('esi: %x', esi)
    addr = edx
    noop_current_syscall(pid)
    if syscall_object.ret[0] != -1:
        cmd = syscall_object.args[1].value
        if not ('TCGETS' in cmd or 'FIONREAD' in cmd or 'TCSETSW' in cmd or
                'FIONBIO' in cmd):
            raise NotImplementedError('Unsupported ioctl command')
        if 'FIONREAD' in cmd:
            num_bytes = int(syscall_object.args[2].value.strip('[]'))
            logging.debug('Number of bytes: %d', num_bytes)
            tracereplay.poke_address(pid, addr, num_bytes)
        elif 'TCSETSW' in cmd:
            logging.debug('Got a TCSETSW ioctl() call')
            logging.debug('WARNING: NO SIDE EFFECTS REPLICATED')
        elif 'FIONBIO' in cmd:
            logging.debug('Got a FIONBIO ioctl() call')
            logging.debug('WARNING: NO SIDE EFFECTS REPLICATED')
        else:
            c_iflags = syscall_object.args[2].value
            c_iflags = int(c_iflags[c_iflags.rfind('=')+1:], 16)
            c_oflags = syscall_object.args[3].value
            c_oflags = int(c_oflags[c_oflags.rfind('=')+1:], 16)
            c_cflags = syscall_object.args[4].value
            c_cflags = int(c_cflags[c_cflags.rfind('=')+1:], 16)
            c_lflags = syscall_object.args[5].value
            c_lflags = int(c_lflags[c_lflags.rfind('=')+1:], 16)
            c_line = syscall_object.args[6].value
            c_line = int(c_line[c_line.rfind('=')+1:])
            cc = syscall_object.args[7].value
            cc = cc[cc.rfind('=')+1:].strip('"}')
            cc = cc.replace('\\x', ' ').strip()
            cc = bytearray.fromhex(cc)
            cc_as_string = ''.join('{:02x}'.format(x) for x in cc)
            cc = cc_as_string.decode('hex')
            logging.debug('pid: %s', pid)
            logging.debug('Addr: %s', addr)
            logging.debug('cmd: %s', cmd)
            logging.debug('c_iflags: %x', c_iflags)
            logging.debug('c_oflags: %x', c_oflags)
            logging.debug('c_cflags: %x', c_cflags)
            logging.debug('c_lflags: %x', c_lflags)
            logging.debug('c_line: %s', c_line)
            logging.debug('cc: %s', cc_as_string)
            logging.debug('len(cc): %s', len(cc))
            tracereplay.populate_tcgets_response(pid, addr, c_iflags, c_oflags,
                                                 c_cflags,
                                                 c_lflags,
                                                 c_line,
                                                 cc)
    apply_return_conditions(pid, syscall_object)


def brk_entry_debug_printer(pid, orig_eax, syscall_object):
    logging.debug('This call tried to use address: %x',
                  tracereplay.peek_register(pid, tracereplay.EBX))
