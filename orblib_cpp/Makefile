CXX ?= g++
BUILDDIR ?= build
SRCDIR ?= source
OBJDIR := $(BUILDDIR)/obj
LIBDIR := $(BUILDDIR)/lib
BUILD_DIRS := $(OBJDIR) $(LIBDIR)

CXXFLAGS ?= -O3 -march=native -fPIC -std=c++20 -Wall -Wextra -Wpedantic
LDFLAGS ?= -shared

all: shared
shared: $(LIBDIR)/liborblib_cpp.so

$(BUILD_DIRS):
	mkdir -p $@

$(OBJDIR)/orblib_cpp_api.o: $(SRCDIR)/orblib_cpp_api.cpp | $(BUILD_DIRS)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

$(LIBDIR)/liborblib_cpp.so: $(OBJDIR)/orblib_cpp_api.o | $(BUILD_DIRS)
	$(CXX) $(LDFLAGS) -o $@ $^

distclean:
	rm -rf $(BUILDDIR)
