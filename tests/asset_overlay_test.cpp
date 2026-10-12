// Exercise the real file resolver and mutation entry points on temporary trees.
#include "hle/fs.cpp"
#include <filesystem>
#include <fstream>
#include <stdexcept>
#define CHECK(c) do { if (!(c)) throw std::runtime_error("failed: " #c); } while (0)

MainThreadWait::MainThreadWait(int kind) : kind_(kind) {}
MainThreadWait::~MainThreadWait() {}
GameFolders config_game_folders(const std::string& app0) { return {app0, app0 + "-UPDATE"}; }
int main() {
    namespace fs = std::filesystem;
    char temp[] = "/tmp/bbhost-assets-XXXXXX";
    CHECK(mkdtemp(temp));
    fs::path root(temp), base=root/"game", merged=root/"merged"/"dvdroot_ps4", legacy=root/"patch-mods";
    auto put=[](const fs::path& p, const char* text) { fs::create_directories(p.parent_path()); std::ofstream(p)<<text; };
    put(base/"dvdroot_ps4/chr/replace.bin", "base");
    put(base/"dvdroot_ps4/chr/missing.bin", "fallback");
    put(base/"dvdroot_ps4/chr/base-only.bin", "original listing");
    put(base.string()+"-UPDATE/dvdroot_ps4/chr/update.bin", "update");
    put(merged/"chr/replace.bin", "merged");
    put(merged/"chr/Mixed.bin", "mixed case");
    put(legacy/"dvdroot_ps4/chr/replace.bin", "legacy");
    put(legacy/"dvdroot_ps4/chr/legacy.bin", "legacy");
    put(root/"source.bin", "linked");
    fs::create_symlink(root/"source.bin", merged/"chr/link.bin");
    put(root/"merged/eboot.bin", "never replaces executable");
    fs::create_directories(root/"data"); fs::create_directories(root/"tmp");
    auto setup=[&](const char* assets) { hle_fs_set_roots(base.c_str(), (root/"data").c_str(), (root/"tmp").c_str(), "eboot.bin", legacy.c_str(), assets); };
    setup(merged.c_str());
    CHECK(hle_fs_map_path("/app0/dvdroot_ps4/chr/replace.bin") == (merged/"chr/replace.bin").string());
    CHECK(hle_fs_map_path("/app0/dvdroot_ps4/chr/missing.bin") == (base/"dvdroot_ps4/chr/missing.bin").string());
    CHECK(hle_fs_map_path("/app0/dvdroot_ps4/chr/update.bin") == base.string()+"-UPDATE/dvdroot_ps4/chr/update.bin");
    CHECK(hle_fs_map_path("/app0/dvdroot_ps4/chr/legacy.bin") == (legacy/"dvdroot_ps4/chr/legacy.bin").string());
    CHECK(hle_fs_map_path("/app0/dvdroot_ps4/chr/mixed.bin") == (merged/"chr/Mixed.bin").string());
    CHECK(hle_fs_map_path("/app0/dvdroot_ps4/chr/link.bin") == (merged/"chr/link.bin").string());
    CHECK(hle_fs_overlay_file("/dvdroot_ps4/chr/link.bin") == (merged/"chr/link.bin").string());
    CHECK(hle_fs_map_path("/app0/eboot.bin") == (base/"eboot.bin").string());
    CHECK(hle_fs_map_path("/data/save.bin") == (root/"data/save.bin").string());
    CHECK(hle_fs_map_path("/app0/../../source.bin").empty());
    // Partial overlay directories must not hide the lower-layer directory listing.
    CHECK(hle_fs_map_path("/app0/dvdroot_ps4/chr") == (legacy/"dvdroot_ps4/chr").string());
    CHECK(hle_kernel_open("/app0/dvdroot_ps4/chr/replace.bin", 1|kOrbisOTrunc, 0) == sce_err(EROFS));
    CHECK(hle_kernel_open("/app0/dvdroot_ps4/chr/missing.bin", 2, 0) == sce_err(EROFS));
    CHECK(hle_kernel_unlink("/app0/dvdroot_ps4/chr/link.bin") == sce_err(EROFS));
    CHECK(hle_kernel_truncate("/app0/dvdroot_ps4/chr/replace.bin", 0) == sce_err(EROFS));
    CHECK(hle_kernel_rename("/app0/dvdroot_ps4/chr/replace.bin", "/data/moved.bin") == sce_err(EROFS));
    CHECK(fs::file_size(merged/"chr/replace.bin") == 6);
    CHECK(fs::file_size(base/"dvdroot_ps4/chr/replace.bin") == 4);
    int fd=hle_kernel_open("/app0/dvdroot_ps4/chr/link.bin", 0, 0); CHECK(fd>=0); hle_kernel_close(fd);
    fd=hle_kernel_open("/data/save.bin", 1|kOrbisOCreat, 0666); CHECK(fd>=0); hle_kernel_close(fd);
    setup(nullptr);
    CHECK(hle_fs_map_path("/app0/dvdroot_ps4/chr/replace.bin") == (legacy/"dvdroot_ps4/chr/replace.bin").string());
    fs::remove_all(root);
}
