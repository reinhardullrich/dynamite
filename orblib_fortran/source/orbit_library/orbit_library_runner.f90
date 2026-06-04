! Split from orblib_f_new_mirror.f90 without changing module names.

module high_level
    use numeric_kinds
    implicit none
    private

    ! setup/run/stop the program.
    public :: setup_direct, run, stob
    ! Inactive legacy file-input setup routines are kept below as comments.
    ! The active Python path enters through setup_direct.

contains

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive legacy file-input runner setup: active Python path enters through setup_direct.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine setup()
!         use integrator, only: integrator_setup
!         use projection, only: projection_setup
!         use quadrantgrid, only: qgrid_setup
!         use aperture_routines, only: aperture_setup
!         use histograms, only: histogram_setup
!         use psf, only: psf_setup
!         use output, only: output_setup
!         !----------------------------------------------------------------------
!         print *, "  ** Start Setup"
!         call integrator_setup()
!         call projection_setup()
!         call qgrid_setup()
!         call psf_setup()
!         call aperture_setup()
!         call histogram_setup()
!         call output_setup()
!         print *, "  ** Setup Finished"
! 
!     end subroutine setup

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive legacy bar runner setup: active direct shared-library path is non-bar triaxial.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine setup_bar()
!         use integrator, only: integrator_setup_bar
!         use projection, only: projection_setup
!         use quadrantgrid, only: qgrid_setup
!         use aperture_routines, only: aperture_setup
!         use histograms, only: histogram_setup
!         use psf, only: psf_setup
!         use output, only: output_setup
!         !----------------------------------------------------------------------
!         print *, "  ** Start Setup"
!         call integrator_setup_bar()
!         call projection_setup()
!         call qgrid_setup()
!         call psf_setup()
!         call aperture_setup()
!         call histogram_setup()
!         call output_setup()
!         print *, "  ** Setup Finished"
! 
!     end subroutine setup_bar

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine setup_direct(begin_values, begin_noreg, begin_rows, &
                            n_orbits_input, points_input, start_input, &
                            number_input, accuracy_input, psf_count, &
                            max_psf_gauss, psf_kind_input, psf_iten_input, &
                            psf_sigma_input, aperture_count, ap_begin_input, &
                            ap_size_input, ap_rot_input, ap_binx_input, &
                            ap_biny_input, aperture_psf_input, &
                            ap_hist_dim_input, hist_width_input, &
                            hist_center_input, hist_bins_input, &
                            bin_type_input, bin_size_input, max_bin_size, &
                            bin_order_input, out_qgrid, out_pops, out_losvd, &
                            out_orbclass)
        use integrator, only: integrator_setup_direct
        use projection, only: projection_setup
        use quadrantgrid, only: qgrid_setup
        use aperture_routines, only: aperture_setup_direct
        use histograms, only: histogram_setup_direct
        use psf, only: psf_setup_direct
        use output, only: output_setup_direct
        integer(kind=i4b), intent(in) :: begin_rows
        real(kind=dp), intent(in) :: n_orbits_input
        integer(kind=i4b), intent(in) :: points_input, start_input, number_input
        integer(kind=i4b), intent(in) :: psf_count, max_psf_gauss
        integer(kind=i4b), intent(in) :: aperture_count, max_bin_size
        real(kind=dp), intent(in) :: accuracy_input
        real(kind=dp), intent(in), dimension(begin_rows, 9) :: begin_values
        integer(kind=i4b), intent(in), dimension(begin_rows) :: begin_noreg
        integer(kind=i4b), intent(in), dimension(psf_count) :: psf_kind_input
        real(kind=dp), intent(in), dimension(max_psf_gauss, psf_count) :: psf_iten_input
        real(kind=dp), intent(in), dimension(max_psf_gauss, psf_count) :: psf_sigma_input
        real(kind=dp), intent(in), dimension(aperture_count, 2) :: ap_begin_input
        real(kind=dp), intent(in), dimension(aperture_count, 2) :: ap_size_input
        real(kind=dp), intent(in), dimension(aperture_count) :: ap_rot_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: ap_binx_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: ap_biny_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: aperture_psf_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: ap_hist_dim_input
        real(kind=dp), intent(in), dimension(psf_count) :: hist_width_input
        real(kind=dp), intent(in), dimension(psf_count) :: hist_center_input
        integer(kind=i4b), intent(in), dimension(psf_count) :: hist_bins_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: bin_type_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: bin_size_input
        integer(kind=i4b), intent(in), dimension(max_bin_size, aperture_count) :: bin_order_input
        character(len=*), intent(in) :: out_qgrid, out_pops, out_losvd, out_orbclass

        print *, "  ** Start direct Python-input setup"
        call integrator_setup_direct(begin_values, begin_noreg, begin_rows, &
                                     n_orbits_input, points_input, &
                                     start_input, number_input, &
                                     accuracy_input)
        call projection_setup()
        call qgrid_setup()
        call psf_setup_direct(psf_count, max_psf_gauss, psf_kind_input, &
                              psf_iten_input, psf_sigma_input)
        call aperture_setup_direct(aperture_count, ap_begin_input, &
                                   ap_size_input, ap_rot_input, &
                                   ap_binx_input, ap_biny_input, &
                                   aperture_psf_input, ap_hist_dim_input)
        call histogram_setup_direct(hist_width_input, hist_center_input, &
                                    hist_bins_input, aperture_count, &
                                    bin_type_input, bin_size_input, &
                                    max_bin_size, bin_order_input)
        call output_setup_direct(out_qgrid, out_pops, out_losvd, out_orbclass)
        print *, "  ** Direct setup Finished"
    end subroutine setup_direct

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine run()
      use initial_parameters, only: Omega
        use histograms, only: histogram_reset, hist_thesame, &
                              histogram_velbin, histogram_store
        use projection, only: project, projection_symmetry
        use integrator, only: integrator_integrate, integrator_points
        use output, only: output_write
        use quadrantgrid, only: qgrid_reset, qgrid_store
        use psf, only: psf_n, psf_gaussian
        use aperture, only: aperture_n, aperture_psf
        use aperture_boxed, only: aperture_boxed_find

        !----------------------------------------------------------------------
        logical :: done, first, alldone
        real(kind=dp), dimension(integrator_points, 3) :: pos
        real(kind=dp), dimension(integrator_points, 3) :: vel
        real(kind=dp), dimension(integrator_points*projection_symmetry, 2):: proj, vec_gauss
        real(kind=dp), dimension(integrator_points*projection_symmetry):: losvel
        integer(kind=i4b), dimension(integrator_points*projection_symmetry):: velb, poly
        integer(kind=i4b)                                          :: ap, i

        integer(kind=i4b) :: type
        real(kind=dp) :: t1, t2
        alldone = .false.
        print *, "  ** Starting Orbit Calculations"
        if (Omega /= 0.0_dp) print*,"Pattern speed ==================== ", Omega ! (BT)
        do  ! for each orbit

            call cpu_time(t1)

            call histogram_reset()
            call qgrid_reset()
            first = .true.
            do ! for all dithers
                call integrator_integrate(pos, vel, type, done, first, alldone)
                first = .false.
                if (done .or. alldone) exit

                call qgrid_store(pos(:, :), vel(:, :), type)
                first = .true.
                do ! for all projections
                    call project(type, pos, vel, proj, losvel, done, first)
                    if (done) exit
                    first = .false.

                    if (hist_thesame) call histogram_velbin(1, losvel, velb)
                    do i = 1, psf_n
                        if (.not. hist_thesame) call histogram_velbin(i, losvel, velb)
                        call psf_gaussian(i, proj, vec_gauss)
                        do ap = 1, aperture_n
                            if (i == aperture_psf(ap)) then
                                call aperture_boxed_find(ap, vec_gauss, poly)
                                call histogram_store(ap, poly, velb, size(proj, 1))
                            end if
                        end do
                    end do
                end do
            end do
            if (alldone) exit
            call output_write()
            call cpu_time(t2)
            print *, "  * Time spent one orbit:", t2 - t1, " seconds"
        end do
        print *, "  ** Finished Orbit Calculations"

    end subroutine run

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine stob()
        use integrator, only: integrator_stop
        use projection, only: projection_stop
        use histograms, only: histogram_stop
        use psf, only: psf_stop
        use aperture_routines, only: aperture_stop
        use output, only: output_close
        !----------------------------------------------------------------------
        call output_close()
        call integrator_stop()
        call projection_stop()
        call aperture_stop()
        call psf_stop()
        call histogram_stop()

    end subroutine stob

end module high_level
