
##############################################################
#
# This file builds the Python-facing shared library using a standard Fortran
# compiler. Executable driver sources are retained under unused/ for reference
# only. Never use unused/ code in the supported runtime build.
# This makefile was written by Remco van den Bosch, using the
# Leiden, 2009
#
##############################################################
FAST=TRUE
#PROFILE=TRUE
compiler=gfortran

#PROFILEDIR=~/profile/

BUILDDIR ?= build
SRCDIR ?= source
NUMERICSDIR := $(SRCDIR)/numerics
UNUSEDDIR := unused
POTENTIALDIR := $(SRCDIR)/potential
ORBITLIBDIR := $(SRCDIR)/orbit_library
OBJDIR := $(BUILDDIR)/obj
MODDIR := $(BUILDDIR)/mod
LIBDIR := $(BUILDDIR)/lib
BUILD_DIRS := $(OBJDIR) $(MODDIR) $(LIBDIR)

ifeq ($(compiler),ifort)
ifdef FAST
  #flags = -fast
  flags += -O3 -IPO -xT -prefetch -pad
  flags += -fno-fnalias
else
  flags += -C -g -inline-debug-info
endif



ifdef PROFILEDIR
ifdef PROFILE
flags  += -prof-dir $(PROFILEDIR)
flags  +=  -prof-gen
else
  ifdef FAST
    flags  += -prof-dir $(PROFILEDIR)
    flags  += -prof-use
  endif
endif
endif


fortran90 = $(compiler) $(flags)     -c
fortran77 = $(compiler) $(flags) -W0 -c
link      = $(compiler) $(flags)     -o
endif

ifeq ($(compiler),F)
  fortran90 = F -ieee=stop -C -O4   -c
  fortran77 = g77.old -O2   -c
  link = F -ieee=stop -C -O4   -o
endif

ifeq ($(compiler),g95)
  fortran90 = ~/local/bin/g95 -c -O3 -m64  -c
  fortran77 = ~/local/bin/g95 -c -O3 -m64  -c
  link = ~/local/bin/g95 -o -O3 -m64 -o
endif

ifeq ($(compiler),gfortran)
  ifdef FAST
   flags =    -ffast-math -O3 -march=native -fomit-frame-pointer -m64
   flags +=    -funroll-loops -ftree-loop-linear
#   flags += -fno-protect-parens
#   flags +=  -fwhole-file #-fwhole-program # -flto
   flags += -std=legacy
  else
   flags =  -m64 -g  -ggdb -fbounds-check -fcheck-array-temporaries
   #flags = -m64   -g -ffast-math -O3 -march=native -fomit-frame-pointer -m64
  endif

  ifdef PROFILEDIR
  ifdef PROFILE
    flags  += -fprofile-generate=$(PROFILEDIR)
  else
    ifdef FAST
        flags  += -fprofile-use=$(PROFILEDIR)
    endif
  endif
  endif

   # on MAC OS X we can use the built-in BLAS/LAPACK
  #flags += -fexternal-blas -framework Accelerate
  flags += -fexternal-blas

  modflags = -J$(MODDIR) -I$(MODDIR)
  fortran90 = gfortran $(flags) $(modflags) -c
  fortran77 = gfortran $(flags) $(modflags) -c
  link = gfortran $(flags) $(modflags) -o
  shared_link = gfortran $(flags) $(modflags) -fPIC -shared -o
endif

##########################################################

all : shared
nogal : all
shared : $(LIBDIR)/liborblib_fortran.so

$(BUILD_DIRS):
	mkdir -p $@

#########################################################
#
# Store a copy of all compiled version in RCS as backup
#
#########################################################

RCS : makefile $(SRCDIR)/initial_parameters.f90 $(ORBITLIB_SOURCES) $(POTENTIALDIR)/triaxial_stellar_potential.f90 $(POTENTIALDIR)/interpolated_potential.f90 $(SRCDIR)/orbit_start_library.f90 $(SRCDIR)/orblib_c_api.f90 $(POTENTIALDIR)/dark_halo_potential.f90
	ci -q -l -mcompile makefile $(SRCDIR)/initial_parameters.f90 $(ORBITLIB_SOURCES) $(POTENTIALDIR)/triaxial_stellar_potential.f90 $(POTENTIALDIR)/interpolated_potential.f90 $(SRCDIR)/orbit_start_library.f90 $(SRCDIR)/orblib_c_api.f90 $(POTENTIALDIR)/dark_halo_potential.f90

##########################################################
#
# Choice between two integrators
#
# DOP853 is the more accurate and is less prone to fail
# integrating the orbit trajectory, but it is slower too.
#
##########################################################

# DOPRI5 is kept in unused/ as archived reference code only.
# Never switch active builds to unused/ without explicit user approval.
#DOPCDE = $(UNUSEDDIR)/dopri5.f
#DOPOBJ = $(OBJDIR)/dopri5.o

DOPCDE = $(NUMERICSDIR)/dop853.f
DOPOBJ = $(OBJDIR)/dop853.o


######################################################
#
# MGE Code.
#
######################################################

MGECDE = $(NUMERICSDIR)/ran1_nr.f90 $(NUMERICSDIR)/numeric_kinds_f.f90 $(NUMERICSDIR)/dqxgs.f $(NUMERICSDIR)/ellipint.f90 $(SRCDIR)/initial_parameters.f90 $(POTENTIALDIR)/triaxial_stellar_potential.f90 $(POTENTIALDIR)/dark_halo_potential.f90 $(POTENTIALDIR)/interpolated_potential.f90 $(NUMERICSDIR)/specfunc_beta.f90
MGEOBJ = $(OBJDIR)/ran1_nr.o $(OBJDIR)/numeric_kinds_f.o $(OBJDIR)/dqxgs.o $(OBJDIR)/initial_parameters.o $(OBJDIR)/triaxial_stellar_potential.o $(OBJDIR)/dark_halo_potential.o $(OBJDIR)/interpolated_potential.o $(OBJDIR)/ellipint.o $(OBJDIR)/specfunc_beta.o

$(OBJDIR)/initial_parameters.o: $(SRCDIR)/initial_parameters.f90 $(OBJDIR)/numeric_kinds_f.o | $(BUILD_DIRS)
	$(fortran90) -o $@ $(SRCDIR)/initial_parameters.f90

$(OBJDIR)/triaxial_stellar_potential.o : $(POTENTIALDIR)/triaxial_stellar_potential.f90 $(OBJDIR)/ellipint.o $(OBJDIR)/numeric_kinds_f.o $(OBJDIR)/initial_parameters.o | $(BUILD_DIRS)
	$(fortran90) -o $@ $(POTENTIALDIR)/triaxial_stellar_potential.f90

$(OBJDIR)/dark_halo_potential.o : $(POTENTIALDIR)/dark_halo_potential.f90 $(OBJDIR)/triaxial_stellar_potential.o $(OBJDIR)/numeric_kinds_f.o $(OBJDIR)/initial_parameters.o | $(BUILD_DIRS)
	$(fortran90) -o $@ $(POTENTIALDIR)/dark_halo_potential.f90

$(OBJDIR)/interpolated_potential.o : $(POTENTIALDIR)/interpolated_potential.f90 $(OBJDIR)/triaxial_stellar_potential.o $(OBJDIR)/numeric_kinds_f.o $(OBJDIR)/initial_parameters.o | $(BUILD_DIRS)
	$(fortran90) -o $@ $(POTENTIALDIR)/interpolated_potential.f90

#####################################################
#
# AUX routines
#
###################################################

$(OBJDIR)/ran1_nr.o : $(NUMERICSDIR)/ran1_nr.f90 | $(BUILD_DIRS)
	$(fortran90) -o $@ $(NUMERICSDIR)/ran1_nr.f90

$(OBJDIR)/numeric_kinds_f.o : $(NUMERICSDIR)/numeric_kinds_f.f90 | $(BUILD_DIRS)
	$(fortran90) -o $@ $(NUMERICSDIR)/numeric_kinds_f.f90

$(OBJDIR)/ellipint.o : $(NUMERICSDIR)/ellipint.f90 $(OBJDIR)/numeric_kinds_f.o | $(BUILD_DIRS)
	$(fortran90) -o $@ $(NUMERICSDIR)/ellipint.f90

$(OBJDIR)/numrep.o: $(NUMERICSDIR)/numrep.f90 $(OBJDIR)/numeric_kinds_f.o | $(BUILD_DIRS)
	$(fortran77) -o $@ $(NUMERICSDIR)/numrep.f90

$(OBJDIR)/numrec_arloc.o : $(NUMERICSDIR)/numrec_arloc.f | $(BUILD_DIRS)
	$(fortran77) -o $@ $(NUMERICSDIR)/numrec_arloc.f

$(OBJDIR)/dop853.o: $(NUMERICSDIR)/dop853.f | $(BUILD_DIRS)
	$(fortran77) -o $@ $(NUMERICSDIR)/dop853.f

$(OBJDIR)/dopri5.o: $(UNUSEDDIR)/dopri5.f | $(BUILD_DIRS)
	$(fortran77) -o $@ $(UNUSEDDIR)/dopri5.f

$(OBJDIR)/dqxgs.o : $(NUMERICSDIR)/dqxgs.f | $(BUILD_DIRS)
	$(fortran77) -o $@ $(NUMERICSDIR)/dqxgs.f

$(OBJDIR)/specfunc_beta.o : $(NUMERICSDIR)/specfunc_beta.f90 $(OBJDIR)/numeric_kinds_f.o | $(BUILD_DIRS)
	$(fortran90) -o $@ $(NUMERICSDIR)/specfunc_beta.f90

######################################################
#
# orblib_f, The orbit library program.
#
#######################################################

ORBITLIB_SOURCES = $(ORBITLIBDIR)/random_gauss_generator.f90 \
	$(ORBITLIBDIR)/orbit_integrator.f90 \
	$(ORBITLIBDIR)/projection.f90 \
	$(ORBITLIBDIR)/psf.f90 \
	$(ORBITLIBDIR)/aperture_base.f90 \
	$(ORBITLIBDIR)/aperture_boxed.f90 \
	$(ORBITLIBDIR)/aperture_dispatch.f90 \
	$(ORBITLIBDIR)/spatial_binning.f90 \
	$(ORBITLIBDIR)/losvd_histograms.f90 \
	$(ORBITLIBDIR)/intrinsic_qgrid.f90 \
	$(ORBITLIBDIR)/orbit_output.f90 \
	$(ORBITLIBDIR)/orbit_library_runner.f90

ORBLIBNMCDE= $(MGECDE) $(NUMERICSDIR)/numrec_arloc.f $(DOPCDE) $(ORBITLIB_SOURCES)
ORBLIBNMOBJ= $(MGEOBJ) $(OBJDIR)/numrec_arloc.o $(DOPOBJ)
ORBLIBAPICDE= $(ORBLIBNMCDE) $(SRCDIR)/orbit_start_library.f90 $(SRCDIR)/orblib_c_api.f90

ifeq ($(FAST),TRUE)
  ORBLIBNMOBJ=$(ORBLIBNMCDE)
endif

$(LIBDIR)/liborblib_fortran.so : $(ORBLIBAPICDE)
	mkdir -p $(MODDIR) $(LIBDIR)
	$(shared_link) $@ $(ORBLIBAPICDE)

$(OBJDIR)/orbit_start_library.o : $(ORBLIBNMOBJ) $(MGEOBJ) $(SRCDIR)/orbit_start_library.f90 | $(BUILD_DIRS)
	$(fortran90) -o $@ $(SRCDIR)/orbit_start_library.f90

##########################################
#
#  Utilities
#
##########################################

distclean:
	rm -rf $(BUILDDIR)
	rm -f *.o *.il *.mod *.dyn work.* *.d *.exe ifc* *.dpi *.spi gmon.out orbitstart orbitstart_bar orblib_new_mirror orblib_bar

clean:
	rm -rf $(BUILDDIR)
	rm -f *.o *.il *.mod work.* *.d ifc*

profclean:
	rm -rf $(OBJDIR)
	rm -f *.o
