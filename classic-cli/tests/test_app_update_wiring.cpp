#include <catch2/catch_test_macros.hpp>

#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

namespace {

std::string read_source(const char* relative_path) {
    const auto path = std::filesystem::path(__FILE__).parent_path().parent_path() / relative_path;
    std::ifstream file(path);
    REQUIRE(file.is_open());

    std::ostringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

} // namespace

TEST_CASE("App update not_published classification is benign", "[app_update]") {
    const std::string source = read_source("src/app_update.cpp");
    REQUIRE(source.find("kClassificationNotPublished") != std::string::npos);

    const auto branch_start = source.find(
        "is_classification(status.classification, kClassificationNotPublished)");
    REQUIRE(branch_start != std::string::npos);

    const auto branch_end = source.find(
        "is_classification(status.classification, kClassificationError)", branch_start);
    REQUIRE(branch_end != std::string::npos);

    const std::string branch = source.substr(branch_start, branch_end - branch_start);
    REQUIRE(branch.find("No update information is currently published.") != std::string::npos);
    REQUIRE(branch.find("return 0") != std::string::npos);
    REQUIRE(branch.find("stderr") == std::string::npos);
    REQUIRE(branch.find("return 1") == std::string::npos);
}
