
##############################################################
#
# This file builds the Python-facing shared library using a standard Fortran
# compiler. Executable driver sources are retained under source/unused for
# reference, but they are not part of the supported runtime build.
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
UNUSEDDIR := $(SRCDIR)/unused
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

RCS : Makefile $(SRCDIR)/iniparam_f.f90 $(SRCDIR)/orblib_f_new_mirror.f90 $(SRCDIR)/triaxpotent.f90 $(SRCDIR)/interpolpotent.f90 $(SRCDIR)/orbitstart_f.f90 $(SRCDIR)/orblib_api.f90 $(SRCDIR)/dmpotent.f90
	ci -q -l -mcompile Makefile $(SRCDIR)/iniparam_f.f90 $(SRCDIR)/orblib_f_new_mirror.f90 $(SRCDIR)/triaxpotent.f90 $(SRCDIR)/interpolpotent.f90 $(SRCDIR)/orbitstart_f.f90 $(SRCDIR)/orblib_api.f90 $(SRCDIR)/dmpotent.f90

##########################################################
#
# Choice between two integrators
#
# DOP853 is the more accurate and is less prone to fail
# integrating the orbit trajectory, but it is slower too.
#
##########################################################

# DOPRI5 is kept in source/unused as an inactive alternate integrator.
#DOPCDE = $(UNUSEDDIR)/dopri5.f
#DOPOBJ = $(OBJDIR)/dopri5.o

DOPCDE = $(NUMERICSDIR)/dop853.f
DOPOBJ = $(OBJDIR)/dop853.o


######################################################
#
# MGE Code.
#
######################################################

MGECDE = $(SRCDIR)/ran1_nr.f $(NUMERICSDIR)/numeric_kinds_f.f90 $(NUMERICSDIR)/dqxgs.f $(NUMERICSDIR)/ellipint.f90 $(SRCDIR)/iniparam_f.f90 $(SRCDIR)/triaxpotent.f90 $(SRCDIR)/dmpotent.f90 $(SRCDIR)/interpolpotent.f90 $(NUMERICSDIR)/specfunc_beta.f90
MGEOBJ = $(OBJDIR)/ran1_nr.o $(OBJDIR)/numeric_kinds_f.o $(OBJDIR)/dqxgs.o $(OBJDIR)/iniparam_f.o $(OBJDIR)/triaxpotent.o $(OBJDIR)/dmpotent.o $(OBJDIR)/interpolpotent.o $(OBJDIR)/ellipint.o $(OBJDIR)/specfunc_beta.o

$(OBJDIR)/iniparam_f.o: $(SRCDIR)/iniparam_f.f90 $(OBJDIR)/numeric_kinds_f.o | $(BUILD_DIRS)
	$(fortran90) -o $@ $(SRCDIR)/iniparam_f.f90

$(OBJDIR)/triaxpotent.o : $(SRCDIR)/triaxpotent.f90 $(OBJDIR)/ellipint.o $(OBJDIR)/numeric_kinds_f.o $(OBJDIR)/iniparam_f.o | $(BUILD_DIRS)
	$(fortran90) -o $@ $(SRCDIR)/triaxpotent.f90

$(OBJDIR)/dmpotent.o : $(SRCDIR)/dmpotent.f90 $(OBJDIR)/triaxpotent.o $(OBJDIR)/numeric_kinds_f.o $(OBJDIR)/iniparam_f.o | $(BUILD_DIRS)
	$(fortran90) -o $@ $(SRCDIR)/dmpotent.f90

$(OBJDIR)/interpolpotent.o : $(SRCDIR)/interpolpotent.f90 $(OBJDIR)/triaxpotent.o $(OBJDIR)/numeric_kinds_f.o $(OBJDIR)/iniparam_f.o | $(BUILD_DIRS)
	$(fortran90) -o $@ $(SRCDIR)/interpolpotent.f90

#####################################################
#
# AUX routines
#
###################################################

$(OBJDIR)/ran1_nr.o : $(SRCDIR)/ran1_nr.f | $(BUILD_DIRS)
	$(fortran77) -o $@ $(SRCDIR)/ran1_nr.f

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

ORBLIBNMCDE= $(MGECDE) $(NUMERICSDIR)/numrec_arloc.f $(DOPCDE) $(SRCDIR)/orblib_f_new_mirror.f90
ORBLIBNMOBJ= $(MGEOBJ) $(OBJDIR)/numrec_arloc.o $(DOPOBJ) $(OBJDIR)/orblib_f_new_mirror.o
ORBLIBAPICDE= $(ORBLIBNMCDE) $(SRCDIR)/orbitstart_f.f90 $(SRCDIR)/orblib_api.f90

ifeq ($(FAST),TRUE)
  ORBLIBNMOBJ=$(ORBLIBNMCDE)
endif

$(OBJDIR)/orblib_f_new_mirror.o : $(SRCDIR)/orblib_f_new_mirror.f90 $(MGEOBJ) $(OBJDIR)/numrec_arloc.o $(DOPOBJ) | $(BUILD_DIRS)
	$(fortran90) -o $@ $(SRCDIR)/orblib_f_new_mirror.f90

$(LIBDIR)/liborblib_fortran.so : $(ORBLIBAPICDE)
	mkdir -p $(MODDIR) $(LIBDIR)
	$(shared_link) $@ $(ORBLIBAPICDE)

$(OBJDIR)/orbitstart_f.o : $(ORBLIBNMOBJ) $(MGEOBJ) $(SRCDIR)/orbitstart_f.f90 | $(BUILD_DIRS)
	$(fortran90) -o $@ $(SRCDIR)/orbitstart_f.f90

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
