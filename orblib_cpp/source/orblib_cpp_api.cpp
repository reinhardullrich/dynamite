namespace {

constexpr int kAbiVersion = 1;
constexpr int kStatusNotImplemented = -100;

void set_status(int* status, int value) noexcept {
    if (status != nullptr) {
        *status = value;
    }
}

}  // namespace

extern "C" int orblib_cpp_api_abi_version() noexcept {
    return kAbiVersion;
}

extern "C" void orblib_cpp_api_run_orbitstart_memory(
    int,
    int,
    const double*,
    const double*,
    const double*,
    const double*,
    double,
    double,
    double,
    double,
    double,
    double,
    double,
    int,
    double,
    double,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    const double*,
    int,
    double*,
    int*,
    double*,
    int*,
    int* rows_written,
    int* box_rows_written,
    int* status
) noexcept {
    set_status(rows_written, 0);
    set_status(box_rows_written, 0);
    set_status(status, kStatusNotImplemented);
}

extern "C" void orblib_cpp_api_run_orblib_direct(
    int,
    int,
    const double*,
    const double*,
    const double*,
    const double*,
    double,
    double,
    double,
    double,
    double,
    double,
    double,
    int,
    double,
    double,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    const double*,
    int,
    const double*,
    const int*,
    double,
    int,
    int,
    int,
    double,
    int,
    int,
    const int*,
    const double*,
    const double*,
    int,
    const double*,
    const double*,
    const double*,
    const int*,
    const int*,
    const int*,
    const int*,
    const double*,
    const double*,
    const int*,
    int,
    const int*,
    const int*,
    const int*,
    const char*,
    const char*,
    const char*,
    const char*,
    int* status
) noexcept {
    set_status(status, kStatusNotImplemented);
}
