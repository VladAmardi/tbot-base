PYTHON?=python
TESTFLAGS=-p -v
TESTOPTS=
SETUPFLAGS=
GCC=gcc
VER=3.9
DESTDIR=/usr/local/lib/python3.10/site-packages

all: build

build:
	$(GCC) -c -fpic procnamemodule.c -DHAVE_CONFIG_H -I/usr/include/python$(VER) -I/usr/lib/python$(VER)/config
	$(GCC) -shared procnamemodule.o  -o $(DESTDIR)/procname.so
