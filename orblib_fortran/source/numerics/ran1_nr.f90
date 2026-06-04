double precision function ran1(init)
    implicit none

    integer :: init
    integer, parameter :: IA = 16807
    integer, parameter :: IM = 2147483647
    integer, parameter :: IQ = 127773
    integer, parameter :: IR = 2836
    integer, parameter :: NTAB = 32
    integer, parameter :: NDIV = 1 + (IM - 1) / NTAB
    double precision, parameter :: AM = 1d0 / IM
    double precision, parameter :: RNMX = 1d0 - 2.23d-16
    integer :: j, k
    integer, save :: idum
    integer, save :: iv(NTAB) = 0
    integer, save :: iy = 0

    ! DYNAMITE random number generator. First call with init <= 0 initializes
    ! the sequence; later calls with init > 0 return the next value.
    if (init <= 0 .or. iy == 0) then
        init = max(-init, 1)
        do j = NTAB + 8, 1, -1
            k = init / IQ
            init = IA * (init - k * IQ) - IR * k
            if (init < 0) init = init + IM
            if (j <= NTAB) iv(j) = init
        end do
        iy = iv(1)
        idum = init
    end if

    k = idum / IQ
    idum = IA * (idum - k * IQ) - IR * k
    if (idum < 0) idum = idum + IM
    j = 1 + iy / NDIV
    iy = iv(j)
    iv(j) = idum
    ran1 = min(AM * iy, RNMX)
end function ran1
