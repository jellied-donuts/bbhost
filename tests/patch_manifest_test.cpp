// Exercise the real manifest loader with config/filesystem/memory stand-ins.
#include "engine/patch_manifest.cpp"
#include <iostream>

namespace {
std::map<std::string, std::string> settings;
std::map<std::string, std::string> parsed;
bool have_file = true;
HostConfig cfg;
int protections = 0;
void require(bool ok, const char* message) {
    if (!ok) { std::cerr << message << '\n'; std::exit(1); }
}
}
const HostConfig& config() { return cfg; }
std::string config_value(const std::string& k) { return settings[k]; }
std::string config_exe_dir() { return "/test"; }
bool config_parse_toml(const std::string&, std::map<std::string, std::string>* out, std::string*) {
    *out = parsed;
    return true;
}
HostSettings host_settings() { return {}; }
const char* hle_fs_mods_root() { return ""; }
std::string hle_fs_map_path(const char* p) { return p; }
bool host_list_dir(const char*, std::vector<std::string>* names) {
    if (have_file) names->push_back("test.toml");
    return true;
}
namespace gcn {
std::vector<std::uint8_t> dcx_decompress(const std::vector<std::uint8_t>&, std::string*) { return {}; }
}
bool guest_protect_rwx(GuestMemory*, std::uint64_t, std::size_t) { ++protections; return true; }
bool guest_protect_rw(GuestMemory*, std::uint64_t, std::size_t) { ++protections; return true; }
bool guest_protect_rx(GuestMemory*, std::uint64_t, std::size_t) { ++protections; return true; }

int main() {
    parsed = {{"patch.name", "test"}, {"patch.eboot", "hash"},
              {"site.one.address", "0x400000"}, {"site.one.expect", "55"}, {"site.one.bytes", "90"},
              {"site.two.address", "0x400001"}, {"site.two.expect", "56"}, {"site.two.bytes", "91"}};
    auto listed = patch_manifests_list("");
    require(listed.size() == 1 && listed[0].default_on, "legacy manifests default on");
    require(!patch_manifest_off("test"), "legacy switch defaults on");
    parsed["patch.default_on"] = "false";
    listed = patch_manifests_list("");
    require(!listed[0].default_on && patch_manifest_off("test", false), "import defaults off");
    std::uint8_t bytes[] = {0x55, 0x56};
    ElfImage image;
    image.sha256 = "hash";
    image.mem = {bytes, sizeof bytes, 0x900000}; // relocation must not change site selection
    patch_manifests_apply(&image);
    require(bytes[0] == 0x55 && protections == 0, "default-off makes no writes");
    settings["patches.test"] = "true";
    require(!patch_manifest_off("test", false), "explicit enable overrides default");
    image.sha256 = "wrong";
    patch_manifests_apply(&image);
    require(bytes[0] == 0x55 && protections == 0, "wrong hash makes no writes");
    image.sha256 = "hash";
    bytes[1] = 0x57;
    patch_manifests_apply(&image);
    require(bytes[0] == 0x55 && protections == 0, "mismatched second site refuses entire patch");
    bytes[1] = 0x56;
    patch_manifests_apply(&image);
    require(bytes[0] == 0x90 && bytes[1] == 0x91, "enabled patch applied at relocated base");
    const int after = protections;
    patch_manifests_apply(&image);
    require(protections == after, "already-applied patch makes no writes");
    settings["patches.test"] = "false";
    require(patch_manifest_off("test", true), "explicit disable overrides default");
    parsed["patch.default_on"] = "typo";
    require(!patch_manifests_list("")[0].error.empty(), "invalid default rejected");
    settings.clear();
    settings["world.old_hunters"] = "false";
    require(patch_manifest_off("old-hunters"), "legacy Old Hunters config preserved");
    settings["patches.old-hunters"] = "true";
    require(!patch_manifest_off("old-hunters"), "new Old Hunters config wins");
    std::cout << "patch manifest checks passed\n";
}
