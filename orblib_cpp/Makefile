CXX ?= g++
BUILDDIR ?= build
SRCDIR ?= source
OBJDIR := $(BUILDDIR)/obj
LIBDIR := $(BUILDDIR)/lib
BUILD_DIRS := $(OBJDIR) $(LIBDIR)

CXXFLAGS ?= -O3 -march=native -fPIC -std=c++20 -Wall -Wextra -Wpedantic -Iinclude
LDFLAGS ?= -shared
SOURCES := $(SRCDIR)/orblib_cpp_api.cpp $(SRCDIR)/dop853.cpp $(SRCDIR)/ran1.cpp
OBJECTS := $(patsubst $(SRCDIR)/%.cpp,$(OBJDIR)/%.o,$(SOURCES))

all: shared
shared: $(LIBDIR)/liborblib_cpp.so

$(BUILD_DIRS):
	mkdir -p $@

$(OBJDIR)/%.o: $(SRCDIR)/%.cpp | $(BUILD_DIRS)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

$(LIBDIR)/liborblib_cpp.so: $(OBJECTS) | $(BUILD_DIRS)
	$(CXX) $(LDFLAGS) -o $@ $^

distclean:
	rm -rf $(BUILDDIR)
