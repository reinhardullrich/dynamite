! Split from orblib_f_new_mirror.f90 without changing module names.

module output
! Module doing all the output of the program
    use numeric_kinds
    implicit none
    private

    integer(kind=i4b), private :: out_handle = 0_i4b
    character(len=80), public  :: out_file_qgrid, out_file_pops &
                                  , out_file_losvd, out_file_orbclass
    character(len=84), private :: out_tmp_file

    public :: output_setup_direct
    ! Inactive legacy output setup is kept below as comments.
    ! The active Python path passes output paths directly.

    public :: output_close

    public :: output_write

contains

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive legacy output setup: active Python path passes output paths to output_setup_direct.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine output_setup()
!         use integrator, only: integrator_setup_write, integrator_set_current,&
!              &                   integrator_current
!         use aperture, only: ap_hist0d_n
!         use histograms, only: histogram_setup_write
!         use histograms, only: histogram_setup_write_mass
!         use quadrantgrid, only: qgrid_setup_write
!         !----------------------------------------------------------------------
!         character(len=8)  :: d
!         character(len=10)  :: t
!         character(len=5)  :: g
!         integer(kind=i4b)  :: error, tmp
! 
!         print *, "  ** Setting up output module"
!         print *, "  * Give the name of the qgrid outputfile:"
!         ! read (unit=*, fmt="(a80)"), out_file
!         read *, out_file_qgrid
!         print *, out_file_qgrid
! 
!         if (ap_hist0d_n > 0) then
!             print *, "  * Give the name of the pops '0d histogram' outputfile:"
!             read *, out_file_pops
!             print *, out_file_pops
!         end if
! 
!         print *, "  * Give the name of the 1d losvd histogram outputfile:"
!         read *, out_file_losvd
!         print *, out_file_losvd
! 
!         print *, "  * Give the name of the orbit classification outputfile:"
!         read *, out_file_orbclass
!         print *, out_file_orbclass
! 
!         ! out_file = adjustl(out_file)
!         ! print *, out_file
! 
!         out_tmp_file = out_file_qgrid
!         out_tmp_file(len_trim(out_file_qgrid) + 1:len_trim(out_file_qgrid) + 4) = ".tmp"
!         print *, out_tmp_file
! 
!         call date_and_time(date=d, time=t, zone=g)
!         print *, "  * Date : ", d, " ", t, " ", g
! 
!         out_handle = 50
!         error = 0
!         ! Check status and setup files
!         open (unit=out_handle + 1, iostat=error, file=out_tmp_file, action="write", &
!              & status="new", position="rewind")
!         if (error == 0) then
! 
!             if (error /= 0) stop "  Error opening file."
!             ! Write orbit library header in *binary* (typically orblib.dat)
!             open (unit=out_handle, iostat=error, file=out_file_qgrid, action="write", &
!                   status="new", form="unformatted")
!             call integrator_setup_write(out_handle)
!             call qgrid_setup_write(out_handle)
!             close (unit=out_handle, iostat=error)
!             if (error /= 0) stop "  Error closing qgrid file."
!             if (ap_hist0d_n > 0) then
!                 open (unit=out_handle, iostat=error, file=out_file_pops, action="write", &
!                     status="new", form="unformatted")
!                 close (unit=out_handle, iostat=error)  ! no setup, just create file
!                 if (error /= 0) stop "  Error closing pops file."
!             end if
!             open (unit=out_handle, iostat=error, file=out_file_losvd, action="write", &
!                   status="new", form="unformatted")
!             call histogram_setup_write(out_handle)
!             close (unit=out_handle, iostat=error)
!             if (error /= 0) stop "  Error closing losvd file."
! 
!             ! Write status file
!             write (unit=out_handle + 1, fmt=*, iostat=error) integrator_current
!             if (error /= 0) stop "  Error writing to status file."
!             close (unit=out_handle + 1, iostat=error)
!             if (error /= 0) stop "  Error closing status file."
!         else
!             print *, "  * Trying to resume previous calculations"
!             ! Try to read the status file
!             open (unit=out_handle + 1, iostat=error, file=out_tmp_file, action="read", &
!                  & status="old", position="rewind")
!             if (error /= 0) stop "  Error: Inconsistent status file."
!             read (unit=out_handle + 1, fmt=*) tmp
!             if (tmp == -1) stop " Error: Orbit library already finished or orbit &
!                  & library in inconsistent state"
!             call integrator_set_current(tmp)
!             close (unit=out_handle + 1, iostat=error)
!             if (error /= 0) stop "  Error closing status file."
! 
!             ! Checking if orbit library file exists
!             open (unit=out_handle, iostat=error, file=out_file_qgrid, action="write", &
!                  & status="old", position="append", form="unformatted")
!             if (error /= 0) stop "  Error opening library file. Does it exist?"
!             close (unit=out_handle, iostat=error)
!             if (error /= 0) stop "  Error closing library file."
!             print *, "  * Resuming with orbit :", tmp + 1
!         end if
! 
!         open (unit=30, file=out_file_orbclass, status="replace", action="write")
! 
!         print *, "  ** Output file setup finished."
! 
!     end subroutine output_setup

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine output_setup_direct(out_qgrid, out_pops, out_losvd, out_orbclass)
        use integrator, only: integrator_setup_write, integrator_set_current,&
             &                   integrator_current
        use aperture, only: ap_hist0d_n
        use histograms, only: histogram_setup_write
        use quadrantgrid, only: qgrid_setup_write
        character(len=*), intent(in) :: out_qgrid, out_pops, out_losvd, out_orbclass
        character(len=8)  :: d
        character(len=10) :: t
        character(len=5)  :: g
        integer(kind=i4b) :: error, tmp

        print *, "  ** Setting up output module from direct Python input"
        out_file_qgrid = out_qgrid
        out_file_pops = out_pops
        out_file_losvd = out_losvd
        out_file_orbclass = out_orbclass

        out_tmp_file = out_file_qgrid
        out_tmp_file(len_trim(out_file_qgrid) + 1:len_trim(out_file_qgrid) + 4) = ".tmp"

        call date_and_time(date=d, time=t, zone=g)
        print *, "  * Date : ", d, " ", t, " ", g

        out_handle = 50
        error = 0
        open (unit=out_handle + 1, iostat=error, file=out_tmp_file, action="write", &
             & status="new", position="rewind")
        if (error == 0) then
            open (unit=out_handle, iostat=error, file=out_file_qgrid, action="write", &
                  status="new", form="unformatted")
            call integrator_setup_write(out_handle)
            call qgrid_setup_write(out_handle)
            close (unit=out_handle, iostat=error)
            if (error /= 0) stop "  Error closing qgrid file."
            if (ap_hist0d_n > 0) then
                open (unit=out_handle, iostat=error, file=out_file_pops, action="write", &
                    status="new", form="unformatted")
                close (unit=out_handle, iostat=error)
                if (error /= 0) stop "  Error closing pops file."
            end if
            open (unit=out_handle, iostat=error, file=out_file_losvd, action="write", &
                  status="new", form="unformatted")
            call histogram_setup_write(out_handle)
            close (unit=out_handle, iostat=error)
            if (error /= 0) stop "  Error closing losvd file."

            write (unit=out_handle + 1, fmt=*, iostat=error) integrator_current
            if (error /= 0) stop "  Error writing to status file."
            close (unit=out_handle + 1, iostat=error)
            if (error /= 0) stop "  Error closing status file."
        else
            print *, "  * Trying to resume previous calculations"
            open (unit=out_handle + 1, iostat=error, file=out_tmp_file, action="read", &
                 & status="old", position="rewind")
            if (error /= 0) stop "  Error: Inconsistent status file."
            read (unit=out_handle + 1, fmt=*) tmp
            if (tmp == -1) stop " Error: Orbit library already finished or orbit &
                 & library in inconsistent state"
            call integrator_set_current(tmp)
            close (unit=out_handle + 1, iostat=error)
            if (error /= 0) stop "  Error closing status file."

            open (unit=out_handle, iostat=error, file=out_file_qgrid, action="write", &
                 & status="old", position="append", form="unformatted")
            if (error /= 0) stop "  Error opening library file. Does it exist?"
            close (unit=out_handle, iostat=error)
            if (error /= 0) stop "  Error closing library file."
            print *, "  * Resuming with orbit :", tmp + 1
        end if

        open (unit=30, file=out_file_orbclass, status="replace", action="write")

        print *, "  ** direct Output file setup finished."
    end subroutine output_setup_direct

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine output_close()
        use integrator, only: integrator_current
        use aperture, only: ap_hist0d_n
        !----------------------------------------------------------------------
        integer :: error
        print *, "  * Closing files and stopping output module"
        if (out_handle /= 0) then
            open (unit=out_handle, iostat=error, file=out_file_qgrid, action="write", &
                 & status="old", position="append", form="unformatted")
            if (error /= 0) stop "  Error opening qgrid file."
            write (unit=out_handle, iostat=error) " "
            if (error /= 0) stop "  Error writing to qgrid file. Disk full?"
            close (unit=out_handle, iostat=error)
            if (error /= 0) stop "  Error closing qgrid file."
            if (ap_hist0d_n > 0) then
                open (unit=out_handle, iostat=error, file=out_file_pops, action="write", &
                    & status="old", position="append", form="unformatted")
                if (error /= 0) stop "  Error opening pops file."
                write (unit=out_handle, iostat=error) " "
                if (error /= 0) stop "  Error writing to pops file. Disk full?"
                close (unit=out_handle, iostat=error)
                if (error /= 0) stop "  Error closing pops file."
            end if
            open (unit=out_handle, iostat=error, file=out_file_losvd, action="write", &
                 & status="old", position="append", form="unformatted")
            if (error /= 0) stop "  Error opening losvd file."
            write (unit=out_handle, iostat=error) " "
            if (error /= 0) stop "  Error writing to losvd file. Disk full?"
            close (unit=out_handle, iostat=error)
            if (error /= 0) stop "  Error closing losvd file."
        end if

        ! Update the temp file to finished status
        open (unit=out_handle + 1, iostat=error, file=out_tmp_file, action="write", &
             & status="old", position="rewind")
        if (error /= 0) stop "  Error opening status file."
        write (unit=out_handle + 1, fmt=*, iostat=error) - 1_i4b, "orbit library &
             & finished ", integrator_current
        if (error /= 0) stop "  Error writing to status file."
        close (unit=out_handle + 1, iostat=error)
        if (error /= 0) stop "  Error closing status file."

        close(unit=32,iostat=error)                           ! for orbit info (BT)
        if (error/=0) stop "  Error closing status file."

        print *, " * Finished closing files"

    end subroutine output_close

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine output_write()
        use histograms, only: histogram_write
        use aperture, only: ap_hist0d_n
        use quadrantgrid, only: qgrid_write
        use integrator, only: integrator_write, integrator_current
        !----------------------------------------------------------------------
        integer :: error, out_handle_pops
        ! Update the temp file to writing status
        open (unit=out_handle + 1, iostat=error, file=out_tmp_file, action="write", &
             & status="old", position="rewind")
        if (error /= 0) stop "  Error opening status file."
        write (unit=out_handle + 1, fmt=*, iostat=error) - 1_i4b, "Writing orbit: ", &
             & integrator_current - 1
        if (error /= 0) stop "  Error writing to status file."
        close (unit=out_handle + 1, iostat=error)
        if (error /= 0) stop "  Error closing status file."

        ! Write the orbit to the *binary* output file (typically orblib.dat).
        open (unit=out_handle, iostat=error, file=out_file_qgrid, action="write", &
             & status="old", position="append", form="unformatted")
        if (error /= 0) stop "  Error opening qgrid file."
        call integrator_write(out_handle)
        call qgrid_write(out_handle)
        close (unit=out_handle, iostat=error)
        if (error /= 0) stop "  Error closing qgrid file."
        if (ap_hist0d_n > 0) then
            out_handle_pops = out_handle + 10
            open (unit=out_handle_pops, iostat=error, file=out_file_pops, action="write", &
                & status="old", position="append", form="unformatted")
            if (error /= 0) stop "  Error opening pops file."
        else
            out_handle_pops = 0
        end if
        open (unit=out_handle, iostat=error, file=out_file_losvd, action="write", &
        & status="old", position="append", form="unformatted")
        if (error /= 0) stop "  Error opening losvd file."
        call histogram_write(out_handle, out_handle_pops)
        if (ap_hist0d_n > 0) then
            close (unit=out_handle_pops, iostat=error)
            if (error /= 0) stop "  Error closing pops file."
        end if
        close (unit=out_handle, iostat=error)
        if (error /= 0) stop "  Error closing losvd file."

        ! Update the temp file to intermediate status
        open (unit=out_handle + 1, iostat=error, file=out_tmp_file, action="write", &
             & status="old", position="rewind")
        if (error /= 0) stop "  Error opening status file."
        write (unit=out_handle + 1, fmt=*, iostat=error) integrator_current
        if (error /= 0) stop "  Error writing to status file."
        close (unit=out_handle + 1, iostat=error)
        if (error /= 0) stop "  Error closing status file."

    end subroutine output_write

end module output
