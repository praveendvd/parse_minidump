#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Get a recorded PCAP file, assume that payload is 16 bits RGB565, save the payload to the PNG image file
# Data can come from OV7691
'''
The script parses the Windows BSOD dumpfiles. It handles only files which start with 
'PAGEDU64' or 'PAGEDUMP'
Usage:
    parse_minidump.py parse --filein=FILENAME 


Options:
    --filein=FILENAME file to convert

Example:
    ./parse_minidump.py parse --filein=100916-24960-01.dmp 
'''

import logging
import re
import struct
import time
from datetime import datetime
import subprocess


try:
    from docopt import docopt
except Exception as e:
    print "Try 'pip install -U docopt'"
    print e


def convert_to_int(str_in, base):
    value = None
    try:
        value = int(str_in, base)
        result = True
    except Exception as e:
        logger.error("Bad formed number '{0}'".format(str_in))
        logger.error(e)
        result = False
    return (result, value)

def open_file(filename, flag):
    '''
    Open a file for reading or writing
    Returns handle to the open file and result code False/True
    '''
    try:
        file_handle = open(filename, flag) # read text file
    except Exception as e:
        logger.error('Failed to open file {0}'.format(filename))
        logger.error(e)
        return (False, None)
    else:
        return (True, file_handle)

def get_mask(bits):
    return (1 << bits) - 1

def data_to_hex(data, max_length=32):
    s = ""
    for b in data:
        s = format(ord(b), 'x') + s
        max_length = max_length - 1
        if (max_length == 0):
            break
        
    return s

def data_to_ascii(data, max_length=32):
    s = ""
    contains_ascii = False
    for b in data:
        b_ascii = ord(b)
        if (b_ascii >= 0x20) and (b_ascii <= 0x7e):
            s =  s + b
            contains_ascii = True
        else:
            s = s + "."
        max_length = max_length - 1
        if (max_length == 0):
            break
    return (contains_ascii, s)
        
def get_bits(value, start, bits):
    mask = get_mask(bits)
    value = value >> start
    value = value & mask
    return value

def get_int(data):
    if (len(data) == 4):
        return struct.unpack("<I", data)[0]
    if (len(data) == 8):
        return struct.unpack("<Q", data)[0]
    else:
        logger.error("Failed to convert data {0} bytes".format(len(data)))
        return -1;

class DataField:
    def __init__(self, name, size, data_struct = None):
        self.name = name
        self.size = size
        self.data_struct = data_struct
        self.is_struct = (data_struct != None)

PHYSICAL_MEMORY_RUN32_STRUCT = (
    DataField("BasePage", 4),
    DataField("PageCount", 4),
);


PHYSICAL_MEMORY_DESCRIPTOR32_STRUCT = (
    DataField("NumberOfRuns", 4),
    DataField("NumberOfPages", 4),
    DataField("Run", 256, PHYSICAL_MEMORY_RUN32_STRUCT)
);

     
HEADER32_STRUCT = (
    DataField("Signature", 4),
    DataField("ValidDump", 4),
    DataField("MajorVersion", 4),
    DataField("MinorVersion", 4),
    DataField("DirectoryTableBase", 4),
    DataField("PfnDataBase", 4), 
    DataField("PsLoadedModuleList", 4),
    DataField("PsActiveProcessHead", 4),
    DataField("MachineImageType", 4),
    DataField("NumberProcessors", 4),
    DataField("BugCheckCode", 4),
    DataField("BugCheckParameter", 16),
    DataField("VersionUser", 32),
    DataField("PaeEnabled", 1),
    DataField("KdSecondaryVersion", 1),
    DataField("Spare", 32),
    DataField("KdDebuggerDataBlock", 32),
    DataField("PhysicalMemoryBlock", 256, PHYSICAL_MEMORY_DESCRIPTOR32_STRUCT)
    # size is 0x1000 bytes
);

PHYSICAL_MEMORY_RUN64_STRUCT = (
    DataField("BasePage", 8),
    DataField("PageCount", 8),
);

PHYSICAL_MEMORY_DESCRIPTOR64_STRUCT = (
    DataField("NumberOfRuns", 8),
    DataField("NumberOfPages", 8),
    DataField("Run", 256, PHYSICAL_MEMORY_RUN64_STRUCT)
);

MINIDUMP_HEADER_STRUCT = (
    DataField("Signature", 4),
    DataField("ValidDump", 4),
    DataField("NumberOfStreams", 4),                  # The number of streams in the minidump directory.
    DataField("StreamDirectoryRva", 4),   # The directory is an array of MINIDUMP_DIRECTORY structures. 
    DataField("CheckSum", 4),
    DataField("TimeDateStamp", 4), 
    DataField("Flags", 8)               # MINIDUMP_TYPE
);


# from file wdm.h
EXCEPTION_MAXIMUM_PARAMETERS = 15 # maximum number of exception parameters

EXCEPTION_RECORD32_STRUCT = (
    DataField("ExceptionCode", 4),
    DataField("ExceptionFlags", 4),
    DataField("ExceptionRecord", 4),
    DataField("ExceptionAddress", 4),
    DataField("NumberParameters", 4),
    DataField("ExceptionInformation", 4*EXCEPTION_MAXIMUM_PARAMETERS)
);

EXCEPTION_RECORD64_STRUCT = (
    DataField("ExceptionCode", 4),
    DataField("ExceptionFlags", 4),
    DataField("ExceptionRecord", 8),
    DataField("ExceptionAddress", 8),
    DataField("NumberParameters", 4),
    DataField("__unusedAlignment", 4),
    DataField("ExceptionInformation", 8*EXCEPTION_MAXIMUM_PARAMETERS)
);

DUMP_0x2000_STRUCT = (
    DataField("Uknwn", 4),  # 2000
    DataField("Uknwn", 4),  
    DataField("Uknwn", 8),
    
    DataField("Uknwn", 4), # 2010
    DataField("Uknwn", 4),
    DataField("Uknwn", 4),
    DataField("Uknwn", 4),

    DataField("Uknwn", 4), # 2020
    DataField("Uknwn", 4),
    DataField("Uknwn", 4),
    DataField("Uknwn", 4),

    DataField("Uknwn", 4), # 2030
    DataField("Uknwn", 4),
    DataField("Strings", 4),
    DataField("Uknwn", 4),
);

                                    
HEADER64_STRUCT = (
    DataField("Signature", 4),
    DataField("ValidDump", 4),
    DataField("MajorVersion", 4),
    DataField("MinorVersion", 4),
    DataField("DirectoryTableBase", 8),
    DataField("PfnDataBase", 8), 
    DataField("PsLoadedModuleList", 8),
    DataField("PsActiveProcessHead", 8),
    DataField("MachineImageType", 4),
    DataField("NumberProcessors", 4),
    DataField("BugCheckCode", 4),
    DataField("Unknown", 4),
    DataField("BugCheckParameter", 4*8),
    DataField("Skip", 0x20),
    DataField("KdDebuggerDataBlock", 8),
    DataField("PhysicalMemoryBlockBuffer", 0x2C0, PHYSICAL_MEMORY_DESCRIPTOR64_STRUCT),
    DataField("ContextRecord", 3000),
    DataField("Exception", 0x98, EXCEPTION_RECORD64_STRUCT),
    DataField("DumpType", 8),
    DataField("RequiredDumpSpace", 8),
    DataField("SystemTime", 8),
    DataField("Comment", 128),
    DataField("SystemUpTime", 8),
    DataField("MiniDumpFields", 4),
    DataField("SecondaryDataState", 4),
    DataField("ProductType", 4),
    DataField("WriterStatus", 4),
    DataField("Unused1", 1),
    DataField("KdSecondaryVersion", 1),
    DataField("Unused2", 2),
    DataField("Reserved", 0xfb4),
    # Offset  0x2000  
    DataField("DUMP_0x2000_STRUCT", 4, DUMP_0x2000_STRUCT),
);

VS_FIXEDFILEINFO_STRUCT = (
    DataField("dwSignature", 4),
    DataField("dwStrucVersion", 4),
    DataField("dwFileVersionMS", 4),
    DataField("dwFileVersionLS", 4),
    DataField("dwProductVersionMS", 4),
    DataField("dwProductVersionLS", 4),
    DataField("dwFileFlagsMask", 4),
    DataField("dwFileFlags", 4),
    DataField("dwFileOS", 4),
    DataField("dwFileType", 4),
    DataField("dwFileSubtype", 4),
    DataField("dwFileDateMS", 4),
    DataField("dwFileDateLS", 4)
);

MINIDUMP_LOCATION_DESCRIPTOR = (
    DataField("DataSize", 4),
    DataField("Rva", 4)
);

MINIDUMP_MODULE64_STRUCT = (
    DataField("BaseOfImage", 8),
    DataField("SizeOfImage", 4),
    DataField("CheckSum", 4),
    DataField("TimeDateStamp", 4),
    DataField("ModuleNameRva", 4),
    DataField("VersionInfo", 4, VS_FIXEDFILEINFO_STRUCT),
    DataField("CvRecord", 4, MINIDUMP_LOCATION_DESCRIPTOR),
    DataField("MiscRecord", 4, MINIDUMP_LOCATION_DESCRIPTOR),
    DataField("Reserved0", 8),
    DataField("Reserved1", 8),
);

MINIDUMP_MODULE_LIST_STRUCT = (
    DataField("NumberOfModules", 4),
    DataField("Modules", 4, MINIDUMP_MODULE64_STRUCT)
);

DUMP_0x2000_STRINGS_STRUCT = (
    DataField("Length", 4),
    DataField("String", 4),
); 

def read_field(file, size):
    data = file.read(size)
    return data

def parse_field(file, data_field):
    file_offset = file.tell()
    data = read_field(file, data_field.size)
    value = data_to_hex(data)
    (contains_ascii, value_ascii) = data_to_ascii(data)
    if (data_field.name != "Skip"):
        if (contains_ascii):
            logger.debug("{3}:{0} = {1} ({2})".format(data_field.name, value, value_ascii, hex(file_offset)))
        else:
            logger.debug("{2}:{0} = {1}".format(data_field.name, value, hex(file_offset)))
    else:
        logger.debug("Skip {0} bytes".format(data_field.size))
        
        
    return (value, contains_ascii, value_ascii)

def parse_dump_header_generic_struct(arguments, file_dump, struct):
    for data_field in struct:
        if (not data_field.is_struct):
            parse_field(file_dump, data_field)
        else:
            parse_dump_header_generic_struct(arguments, file_dump, struct)
        
    

def parse_dump_header_physical_memory_block_buffer_64(arguments, file_dump, data_field):
    (value, contains_ascii, value_ascii) = parse_field(file_dump, PHYSICAL_MEMORY_DESCRIPTOR64_STRUCT[0])
    if (value == '4547415045474150'):
        bytes_to_skip = data_field.size
        logger.warn("Skip physical memory descriptors {0} bytes".format(bytes_to_skip))
        read_field(file_dump, bytes_to_skip-PHYSICAL_MEMORY_DESCRIPTOR64_STRUCT[0].size)
        return False
    number_of_pages = parse_field(file_dump, PHYSICAL_MEMORY_DESCRIPTOR64_STRUCT[1])
    return False

def parse_dump_header_exception_64(arguments, file_dump):
    (exception_code, exception_flags, exception_address) = (None, None, None)
    for data_field in EXCEPTION_RECORD64_STRUCT:
        (value, contains_ascii, value_ascii) = parse_field(file_dump, data_field)
        if (data_field.name == "ExceptionCode"):
            exception_code = int(value, 16)
        if (data_field.name == "ExceptionFlags"):
            exception_flags = int(value, 16)
        if (data_field.name == "ExceptionAddress"):
            exception_address = int(value, 16)
            
    return (exception_code, exception_flags, exception_address)
        

def parse_dump_header_physical_blocks_32(arguments, file_dump):
    number_of_runs = parse_field(file_dump, PHYSICAL_MEMORY_DESCRIPTOR32_STRUCT[0])
    number_of_pages = parse_field(file_dump, PHYSICAL_MEMORY_DESCRIPTOR32_STRUCT[1])

def parse_dump_header_0x2000(arguments, file_dump):
    strings_offset = None
    for data_field in DUMP_0x2000_STRUCT:
        (value, contains_ascii, value_ascii) = parse_field(file_dump, data_field)
        if (data_field.name == "Strings"):
            strings_offset = int(value, 16)
            logger.debug("Loaded modules names at offset {0}".format(hex(strings_offset)))
    return (strings_offset)

def parse_strings(arguments, file_dump, strings_offset):
    file_dump_cursor = file_dump.tell()
    
    file_dump.seek(strings_offset)
    # End of the strings section is 16 bits zero
    while (True):
        file_offset = file_dump.tell()
        cursor_tmp = file_dump.tell()
        data = read_field(file_dump, 4)
        length_hex = data_to_hex(data)
        length = int(length_hex, 16)
        if (length == 0):
            logger.debug("{0}: Length is zero".format(hex(strings_offset)))
            break
        if (length > 256):
            logger.debug("{0}:Length is {1} bytes".format(hex(cursor_tmp), length))
            break
        string = read_field(file_dump, 2*length)
        (contains_ascii, string_ascii) = data_to_ascii(string, 256)
        logger.debug("{0}: length={1},'{2}'".format(hex(file_offset), length, string_ascii))
        
        cursor_tmp = file_dump.tell()
        data = read_field(file_dump, 2) # I expect zero terminaiton here
        zero_hex = data_to_hex(data)
        zero = int(zero_hex, 16)  
        if (zero != 0):
            logger.debug("{0}:Missing zero termination - got {1} instead".format(hex(cursor_tmp), zero_hex))
            break
        
    file_dump.seek(file_dump_cursor)
        

def parse_dump_header_64(arguments, file_dump):
    logger.info("64bits dump")
    skip = True
    physical_memory_presents = False
        
    for data_field in HEADER64_STRUCT:
        if (data_field.name == "MajorVersion"):
            skip = False
        if skip:
            continue
        if (not data_field.is_struct):
            (value, contains_ascii, value_ascii) = parse_field(file_dump, data_field)
        else:
            if (data_field.name == "PhysicalMemoryBlockBuffer"):
                physical_memory_presents = parse_dump_header_physical_memory_block_buffer_64(arguments, file_dump, data_field)
            elif (data_field.name == "Exception"):
                (exception_code, exception_flags, exception_address) = parse_dump_header_exception_64(arguments, file_dump)
                logger.info("Exception: code={0}, address={1}, flags={2}".format(hex(exception_code), hex(exception_address), hex(exception_flags)))
            elif (data_field.name == "DUMP_0x2000_STRUCT"):
                strings_offset = parse_dump_header_0x2000(arguments, file_dump)
                parse_strings(arguments, file_dump, strings_offset)
            else:
                parse_dump_header_generic_struct(arguments, file_dump, data_field.data_struct)
    return physical_memory_presents;
                
    
def parse_dump_header_32(arguments, file_dump):
    logger.info("32bits dump")
    skip = True
    for data_field in HEADER64_STRUCT:
        if (data_field.name == "MajorVersion"):
            skip = False
        if skip:
            continue
        if (not data_field.is_struct):
            (value, contains_ascii, value_ascii) = parse_field(file_dump, data_field)
        else:
            if (data_field.name == "PhysicalMemoryBlock"):
                parse_dump_header_physical_blocks_32(arguments, file_dump)


def parse_dump_header(arguments, file_dump):
    dump_type_64 = None
    for data_field in HEADER32_STRUCT:
        if (not data_field.is_struct):
            (value, contains_ascii, value_ascii) = parse_field(file_dump, data_field)
            if (data_field.name == "Signature"):
                if (value_ascii != "PAGE"):
                    logger.error("Failed to parse header in the file '{0}' - no signature. {1} instead of expected {2}".format(filename_in, value_ascii, "PAGE"))
                    break
            if (data_field.name == "ValidDump"):
                dump_type_64 = (value_ascii == "DU64") 
                if (dump_type_64):
                    physical_memory_presents = parse_dump_header_64(arguments, file_dump)
                else:
                    physical_memory_presents = parse_dump_header_32(arguments, file_dump)
            
                break
            
    if (not physical_memory_presents):
        logger.info("No physical memory presents in the dump file")

            
    return dump_type_64
                 
                    
                

def parse_dump(arguments):
    filename_in = arguments["--filein"]
    logger.info("Parse file '{0}'".format(filename_in))
    while True:
        (result, file_dump) = open_file(filename_in, 'rb')
        if not result:
            logger.error("Failed to open file '{0}' for reading".format(filename_in))
            break
        parse_dump_header(arguments, file_dump)
        
        file_dump.close()
        break


if __name__ == '__main__':
    arguments = docopt(__doc__, version="parser")

    logging.basicConfig()
    logger = logging.getLogger('parser')
    logger.setLevel(logging.DEBUG)

    is_parse = arguments["parse"]

    if is_parse:
        parse_dump(arguments)
