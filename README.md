# parse_minidump

The script parses the Windows BSOD 64 bit Kernel Mini Dump files (minidumps). It handles only files which start with 
'PAGEDU64' or 'PAGEDUMP'
Example of output
~~~~
INFO:parser:Parse file '../winvm/minidump.dmp'
INFO:parser:64bits dump
INFO:parser:Exception: code=0x80000003, address=0xfffff800026d4f00L, flags=0x1
.......................  
INFO:parser:Stack: 0xfffff88001127c0bL, \.S.y.s.t.e.m.R.o.o.t.\.s.y.s.t.e.m.3.2.\.d.r.i.v.e.r.s.\.f.l.t.m.g.r...s.y.s.......
.......................
INFO:parser:Stack: 0xfffff800026d4f00L, \.S.y.s.t.e.m.R.o.o.t.\.s.y.s.t.e.m.3.2.\.n.t.o.s.k.r.n.l...e.x.e...
.......................
~~~~

Usage:
~~~~
  parse_minidump.py parse --filein=FILENAME [--debuglevel=LEVEL] 
  parse_minidump.py parse -h
~~~~     
