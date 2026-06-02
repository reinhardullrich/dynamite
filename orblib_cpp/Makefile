CXX ?= g++
BUILDDIR ?= build
SRCDIR ?= source
OBJDIR := $(BUILDDIR)/obj
LIBDIR := $(BUILDDIR)/lib
BUILD_DIRS := $(OBJDIR) $(LIBDIR)

CXXFLAGS ?= -O3 -march=native -fPIC -std=c++20 -Wall -Wextra -Wpedantic -Iinclude
LDFLAGS ?= -shared
SOURCES := $(SRCDIR)/orblib_cpp_api.cpp $(SRCDIR)/dop853.cpp $(SRCDIR)/elliptic_integrals.cpp $(SRCDIR)/interpolated_potential.cpp $(SRCDIR)/orbit_aperture.cpp $(SRCDIR)/orbit_classification.cpp $(SRCDIR)/orbit_histogram.cpp $(SRCDIR)/orbit_integrator.cpp $(SRCDIR)/orbit_projection.cpp $(SRCDIR)/orbit_psf.cpp $(SRCDIR)/orbit_rhs.cpp $(SRCDIR)/potential.cpp $(SRCDIR)/ran1.cpp $(SRCDIR)/triaxial_mge.cpp
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
