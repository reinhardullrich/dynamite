module orblib_c_api
    use iso_c_binding
    use numeric_kinds
    implicit none
    private

    public :: orblib_api_abi_version
    public :: orblib_api_run_orbitstart_memory
    public :: orblib_api_run_orblib_direct

contains

    integer(c_int) function orblib_api_abi_version() bind(C, name="orblib_api_abi_version")
        orblib_api_abi_version = 2_c_int
    end function orblib_api_abi_version

    subroutine orblib_api_run_orbitstart_memory(random_seed, ngauss, &
                                                surf_pc, sigobs_arcsec, &
                                                qobs_input, psi_obs_input, &
                                                distance, theta_view, &
                                                phi_view, psi_view, upsilon, &
                                                xmbh, softl_arcsec, nener, &
                                                rlogmin, rlogmax, ni2, ni3, &
                                                orbit_dithering, quad_nr, &
                                                quad_nth, quad_nph, &
                                                dm_profile_type, n_dmparam, &
                                                dmparam_input, max_rows, &
                                                begin_values, begin_noreg, &
                                                beginbox_values, &
                                                beginbox_noreg, rows_written, &
                                                box_rows_written, status) &
                                                bind(C, name="orblib_api_run_orbitstart_memory")
        use initial_parameters, only: iniparam_from_arrays
        use interpolpot, only: ip_setup, ip_stop
        use orbitstart, only: runorbitstart_memory
        integer(c_int), value, intent(in) :: random_seed, ngauss
        integer(c_int), value, intent(in) :: nener, ni2, ni3, orbit_dithering
        integer(c_int), value, intent(in) :: quad_nr, quad_nth, quad_nph
        integer(c_int), value, intent(in) :: dm_profile_type, n_dmparam
        integer(c_int), value, intent(in) :: max_rows
        real(c_double), intent(in) :: surf_pc(*), sigobs_arcsec(*)
        real(c_double), intent(in) :: qobs_input(*), psi_obs_input(*)
        real(c_double), value, intent(in) :: distance, theta_view, phi_view
        real(c_double), value, intent(in) :: psi_view, upsilon, xmbh
        real(c_double), value, intent(in) :: softl_arcsec, rlogmin, rlogmax
        real(c_double), intent(in) :: dmparam_input(*)
        real(c_double), intent(out), target :: begin_values(*)
        real(c_double), intent(out), target :: beginbox_values(*)
        integer(c_int), intent(out), target :: begin_noreg(*)
        integer(c_int), intent(out), target :: beginbox_noreg(*)
        integer(c_int), intent(out) :: rows_written, box_rows_written, status
        integer :: r_seed
        integer(kind=i4b) :: rows_i, box_rows_i, status_i

        status = 0_c_int
        rows_written = 0_c_int
        box_rows_written = 0_c_int
        r_seed = int(random_seed)
        call seed_ran1(r_seed)

        call iniparam_from_arrays(int(ngauss, kind=i4b), surf_pc, &
                                  sigobs_arcsec, qobs_input, psi_obs_input, &
                                  distance, theta_view, phi_view, psi_view, &
                                  upsilon, xmbh, softl_arcsec, &
                                  int(nener, kind=i4b), rlogmin, rlogmax, &
                                  int(ni2, kind=i4b), int(ni3, kind=i4b), &
                                  int(orbit_dithering, kind=i4b), &
                                  int(quad_nr, kind=i4b), &
                                  int(quad_nth, kind=i4b), &
                                  int(quad_nph, kind=i4b), &
                                  int(dm_profile_type, kind=i4b), &
                                  int(n_dmparam, kind=i4b), dmparam_input)

        call ip_setup()
        call runorbitstart_memory(int(max_rows, kind=i4b), begin_values, &
                                  begin_noreg, beginbox_values, &
                                  beginbox_noreg, rows_i, box_rows_i, &
                                  status_i)
        call ip_stop()

        rows_written = int(rows_i, kind=c_int)
        box_rows_written = int(box_rows_i, kind=c_int)
        status = int(status_i, kind=c_int)
    end subroutine orblib_api_run_orbitstart_memory

    subroutine orblib_api_run_orblib_direct(random_seed, ngauss, surf_pc, &
                                            sigobs_arcsec, qobs_input, &
                                            psi_obs_input, distance, &
                                            theta_view, phi_view, psi_view, &
                                            upsilon, xmbh, softl_arcsec, &
                                            nener, rlogmin, rlogmax, ni2, &
                                            ni3, orbit_dithering, quad_nr, &
                                            quad_nth, quad_nph, &
                                            dm_profile_type, n_dmparam, &
                                            dmparam_input, begin_rows, &
                                            begin_values, begin_noreg, &
                                            orbital_periods, sampling, &
                                            starting_orbit, number_orbits, &
                                            accuracy, psf_count, &
                                            max_psf_gauss, psf_kind, &
                                            psf_weight, psf_sigma, &
                                            aperture_count, ap_begin, &
                                            ap_size, ap_rot, ap_binx, &
                                            ap_biny, ap_psf, ap_hist_dim, &
                                            hist_width, hist_center, &
                                            hist_bins, max_bin_size, &
                                            bin_type, bin_size, bin_order, &
                                            out_qgrid_path, out_pops_path, &
                                            out_losvd_path, &
                                            out_orbclass_path, status) &
                                            bind(C, name="orblib_api_run_orblib_direct")
        use initial_parameters, only: iniparam_from_arrays
        use interpolpot, only: ip_setup, ip_stop
        use high_level, only: setup_direct, run, stob
        integer(c_int), value, intent(in) :: random_seed, ngauss
        integer(c_int), value, intent(in) :: nener, ni2, ni3, orbit_dithering
        integer(c_int), value, intent(in) :: quad_nr, quad_nth, quad_nph
        integer(c_int), value, intent(in) :: dm_profile_type, n_dmparam
        integer(c_int), value, intent(in) :: begin_rows
        integer(c_int), value, intent(in) :: sampling
        integer(c_int), value, intent(in) :: starting_orbit, number_orbits
        integer(c_int), value, intent(in) :: psf_count, max_psf_gauss
        integer(c_int), value, intent(in) :: aperture_count, max_bin_size
        real(c_double), value, intent(in) :: distance, theta_view, phi_view
        real(c_double), value, intent(in) :: psi_view, upsilon, xmbh
        real(c_double), value, intent(in) :: softl_arcsec, rlogmin, rlogmax
        real(c_double), value, intent(in) :: orbital_periods, accuracy
        real(c_double), intent(in) :: surf_pc(*), sigobs_arcsec(*)
        real(c_double), intent(in) :: qobs_input(*), psi_obs_input(*)
        real(c_double), intent(in) :: dmparam_input(*)
        real(c_double), intent(in) :: begin_values(begin_rows, 9)
        integer(c_int), intent(in) :: begin_noreg(begin_rows)
        integer(c_int), intent(in) :: psf_kind(psf_count)
        real(c_double), intent(in) :: psf_weight(max_psf_gauss, psf_count)
        real(c_double), intent(in) :: psf_sigma(max_psf_gauss, psf_count)
        real(c_double), intent(in) :: ap_begin(aperture_count, 2)
        real(c_double), intent(in) :: ap_size(aperture_count, 2)
        real(c_double), intent(in) :: ap_rot(aperture_count)
        integer(c_int), intent(in) :: ap_binx(aperture_count)
        integer(c_int), intent(in) :: ap_biny(aperture_count)
        integer(c_int), intent(in) :: ap_psf(aperture_count)
        integer(c_int), intent(in) :: ap_hist_dim(aperture_count)
        real(c_double), intent(in) :: hist_width(psf_count)
        real(c_double), intent(in) :: hist_center(psf_count)
        integer(c_int), intent(in) :: hist_bins(psf_count)
        integer(c_int), intent(in) :: bin_type(aperture_count)
        integer(c_int), intent(in) :: bin_size(aperture_count)
        integer(c_int), intent(in) :: bin_order(max_bin_size, aperture_count)
        character(kind=c_char), intent(in) :: out_qgrid_path(*)
        character(kind=c_char), intent(in) :: out_pops_path(*)
        character(kind=c_char), intent(in) :: out_losvd_path(*)
        character(kind=c_char), intent(in) :: out_orbclass_path(*)
        integer(c_int), intent(out) :: status
        integer :: r_seed
        character(len=80) :: out_qgrid, out_pops, out_losvd, out_orbclass

        status = 0_c_int
        call c_string_to_fortran(out_qgrid_path, out_qgrid, status)
        if (status /= 0_c_int) return
        call c_string_to_fortran(out_pops_path, out_pops, status)
        if (status /= 0_c_int) return
        call c_string_to_fortran(out_losvd_path, out_losvd, status)
        if (status /= 0_c_int) return
        call c_string_to_fortran(out_orbclass_path, out_orbclass, status)
        if (status /= 0_c_int) return

        r_seed = int(random_seed)
        call seed_ran1(r_seed)

        call iniparam_from_arrays(int(ngauss, kind=i4b), surf_pc, &
                                  sigobs_arcsec, qobs_input, psi_obs_input, &
                                  distance, theta_view, phi_view, psi_view, &
                                  upsilon, xmbh, softl_arcsec, &
                                  int(nener, kind=i4b), rlogmin, rlogmax, &
                                  int(ni2, kind=i4b), int(ni3, kind=i4b), &
                                  int(orbit_dithering, kind=i4b), &
                                  int(quad_nr, kind=i4b), &
                                  int(quad_nth, kind=i4b), &
                                  int(quad_nph, kind=i4b), &
                                  int(dm_profile_type, kind=i4b), &
                                  int(n_dmparam, kind=i4b), dmparam_input)

        call ip_setup()
        call setup_direct(begin_values, begin_noreg, int(begin_rows, kind=i4b), &
                          orbital_periods, int(sampling, kind=i4b), &
                          int(starting_orbit, kind=i4b), &
                          int(number_orbits, kind=i4b), accuracy, &
                          int(psf_count, kind=i4b), &
                          int(max_psf_gauss, kind=i4b), psf_kind, &
                          psf_weight, psf_sigma, &
                          int(aperture_count, kind=i4b), ap_begin, ap_size, &
                          ap_rot, ap_binx, ap_biny, ap_psf, ap_hist_dim, &
                          hist_width, hist_center, hist_bins, bin_type, &
                          bin_size, int(max_bin_size, kind=i4b), bin_order, &
                          trim(out_qgrid), trim(out_pops), trim(out_losvd), &
                          trim(out_orbclass))
        call run()
        call stob()
        call ip_stop()
    end subroutine orblib_api_run_orblib_direct

    subroutine c_string_to_fortran(c_string, fortran_string, status)
        character(kind=c_char), intent(in) :: c_string(*)
        character(len=*), intent(out) :: fortran_string
        integer(c_int), intent(out) :: status
        integer :: i

        status = 0_c_int
        fortran_string = " "
        do i = 1, len(fortran_string)
            if (c_string(i) == c_null_char) return
            fortran_string(i:i) = c_string(i)
        end do
        status = 1_c_int
    end subroutine c_string_to_fortran

    subroutine seed_ran1(r_seed)
        integer, intent(inout) :: r_seed
        real(kind=dp) :: ran1, r_num

        if (r_seed <= 0) then
            call random_seed()
            call random_number(r_num)
            r_seed = int(2147483647.0_dp*r_num)
            r_num = ran1(-r_seed)
            write (*, *) "Using ran1 with random seed ", r_seed
        else
            r_num = ran1(-r_seed)
            write (*, *) "Using ran1 with given seed ", r_seed
        end if
    end subroutine seed_ran1

end module orblib_c_api
