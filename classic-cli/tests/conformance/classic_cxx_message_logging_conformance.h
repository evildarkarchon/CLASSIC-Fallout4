// Observe real bridge log records from the Windows native stderr stream.

/// Own and restore both CRT and Win32 stderr destinations during one serial fixture.
class NativeLogCapture {
    FILE* file_ = nullptr;
    int saved_ = -1;
    bool restored_ = false;

    /// Restore the original destination before diagnostics or exceptions escape.
    void restore() noexcept {
        if (restored_ || saved_ < 0) return;
        fflush(stderr);
        _dup2(saved_, _fileno(stderr));
        SetStdHandle(STD_ERROR_HANDLE, reinterpret_cast<HANDLE>(_get_osfhandle(_fileno(stderr))));
        restored_ = true;
    }

public:
    /// Start an anonymous capture file; no user path or persistent log is modified.
    NativeLogCapture() {
        file_ = tmpfile();
        if (!file_) throw RunnerError("cannot create native log capture");
        saved_ = _dup(_fileno(stderr));
        if (saved_ < 0 || _dup2(_fileno(file_), _fileno(stderr)) != 0) {
            if (saved_ >= 0) _close(saved_);
            fclose(file_);
            throw RunnerError("cannot redirect native stderr");
        }
        SetStdHandle(STD_ERROR_HANDLE, reinterpret_cast<HANDLE>(_get_osfhandle(_fileno(stderr))));
    }
    NativeLogCapture(const NativeLogCapture&) = delete;
    NativeLogCapture& operator=(const NativeLogCapture&) = delete;
    /// Restore external process diagnostics on every exit, including fixture failures.
    ~NativeLogCapture() { restore(); if (saved_ >= 0) _close(saved_); if (file_) fclose(file_); }

    /// Read exact records, removing only env_logger's timestamp and target prefix.
    json records() {
        restore();
        fflush(file_);
        rewind(file_);
        std::string output;
        std::array<char, 4096> bytes{};
        while (const auto count = fread(bytes.data(), 1, bytes.size(), file_)) output.append(bytes.data(), count);
        if (ferror(file_)) throw RunnerError("cannot read native log capture");
        const std::regex pattern(R"(^\[[^\]]+\s(TRACE|DEBUG|INFO|WARN|ERROR)\s+[^\]]+\] (.*)$)");
        std::istringstream lines(output);
        std::string line;
        auto records = json::array();
        while (std::getline(lines, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            std::smatch match;
            if (!std::regex_match(line, match, pattern)) throw RunnerError("unrecognized native log record: " + line);
            records.push_back(json{{"level", match[1].str()}, {"message", match[2].str()}});
        }
        return records;
    }
};

/// Execute public bridge logging APIs and capture their emitted level/message stream.
json execute_message_logging_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    std::ifstream input(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto fixture = json::parse(input);
    NativeLogCapture capture;
    const auto old_filter = read_environment("RUST_LOG");
    const auto old_style = read_environment("RUST_LOG_STYLE");
    _putenv_s("RUST_LOG", "trace");
    _putenv_s("RUST_LOG_STYLE", "never");
    classic::message::init_logging();
    classic::message::init_logging();
    _putenv_s("RUST_LOG", old_filter.value_or("").c_str());
    _putenv_s("RUST_LOG_STYLE", old_style.value_or("").c_str());
    const auto operation = fixture.at("operation").get<std::string>();
    if (operation == "basic") {
        const auto& messages = fixture.at("messages");
        classic::message::log_info(messages.at("info").get<std::string>());
        classic::message::log_warning(messages.at("warning").get<std::string>());
        classic::message::log_error(messages.at("error").get<std::string>());
        classic::message::log_debug(messages.at("debug").get<std::string>());
    } else if (operation == "startup") {
        classic::message::log_trace(fixture.at("trace").get<std::string>());
        classic::message::log_startup_binding_contract_validated(fixture.at("contract").get<std::string>(), fixture.at("checked").get<uint32_t>(), fixture.at("correlation").get<std::string>());
        classic::message::log_startup_binding_contract_failed(fixture.at("contract").get<std::string>(), fixture.at("missing").get<std::string>(), fixture.at("failureType").get<std::string>(), fixture.at("hint").get<std::string>(), fixture.at("error").get<std::string>(), fixture.at("correlation").get<std::string>());
        classic::message::log_startup_acceleration_status(fixture.at("active").get<uint32_t>(), fixture.at("total").get<uint32_t>(), fixture.at("acceleration").get<std::string>(), fixture.at("correlation").get<std::string>());
    } else {
        throw RunnerError("unsupported CXX logging operation");
    }
    return json{{"records", capture.records()}};
}
